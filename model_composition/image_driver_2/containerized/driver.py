import sys
import os
import argparse
import numpy as np
import time
import base64
import logging

from clipper_admin import ClipperConnection, DockerContainerManager
from datetime import datetime
from PIL import Image
from containerized_utils.zmq_client import Client
from containerized_utils import driver_utils
from multiprocessing import Process, Queue

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%y-%m-%d:%H:%M:%S',
    level=logging.INFO)

logger = logging.getLogger(__name__)

# Models and applications for each heavy node
# will share the same name
INCEPTION_MODEL_APP_NAME = "inception"
OPENCV_FEATS_MODEL_APP_NAME = "opencv-feats"
OPENCV_SVM_MODEL_APP_NAME = "opencv-svm"

INCEPTION_IMAGE_NAME = "model-comp/inception"
OPENCV_FEATS_IMAGE_NAME = "model-comp/opencv-feats"
OPENCV_SVM_IMAGE_NAME = "model-comp/opencv-svm"

VALID_MODEL_NAMES = [
    INCEPTION_MODEL_APP_NAME,
    OPENCV_FEATS_MODEL_APP_NAME,
    OPENCV_SVM_MODEL_APP_NAME
]

CLIPPER_ADDRESS = "localhost"
CLIPPER_SEND_PORT = 4456
CLIPPER_RECV_PORT = 4455

DEFAULT_OUTPUT = "TIMEOUT"

# Configuration parameters for input generation
NUM_SIFT_FEATURES = 20
SIFT_FEATURE_VEC_SIZE = 128

########## Setup ##########

def setup_clipper(config):
    cl = ClipperConnection(DockerContainerManager(redis_port=6380))
    cl.stop_all()
    cl.start_clipper(
        query_frontend_image="clipper/zmq_frontend:develop",
        redis_cpu_str="0",
        mgmt_cpu_str="0",
        query_cpu_str="1-4")
    time.sleep(10)
    driver_utils.setup_heavy_node(cl, config, DEFAULT_OUTPUT)
    time.sleep(10)
    logger.info("Clipper is set up!")
    return config

def get_heavy_node_config(model_name, batch_size, num_replicas, cpus_per_replica=None, allocated_cpus=None, allocated_gpus=None):
    if model_name == INCEPTION_MODEL_APP_NAME:
        if not cpus_per_replica:
            cpus_per_replica = 2
        if not allocated_cpus:
            allocated_cpus = [6,7,14,15]
        if not allocated_gpus:
            allocated_gpus = [0]

        return driver_utils.HeavyNodeConfig(name=INCEPTION_MODEL_APP_NAME,
                                            input_type="floats",
                                            model_image=INCEPTION_IMAGE_NAME,
                                            allocated_cpus=allocated_cpus,
                                            cpus_per_replica=cpus_per_replica,
                                            gpus=allocated_gpus,
                                            batch_size=batch_size,
                                            num_replicas=num_replicas,
                                            use_nvidia_docker=True)

    if model_name == OPENCV_FEATS_MODEL_APP_NAME:
        if not cpus_per_replica:
            cpus_per_replica = 1
        if not allocated_cpus:
            allocated_cpus = range(16,19)
        if not allocated_gpus:
            allocated_gpus = []

        return driver_utils.HeavyNodeConfig(name=OPENCV_FEATS_MODEL_APP_NAME,
                                            input_type="floats",
                                            model_image=OPENCV_FEATS_IMAGE_NAME,
                                            allocated_cpus=allocated_cpus,
                                            cpus_per_replica=cpus_per_replica,
                                            gpus=allocated_gpus,
                                            batch_size=batch_size,
                                            num_replicas=num_replicas,
                                            use_nvidia_docker=True)

    if model_name == OPENCV_SVM_MODEL_APP_NAME:
        if not cpus_per_replica:
            cpus_per_replica = 1
        if not allocated_cpus:
            allocated_cpus = range(20,27)
        if not allocated_gpus:
            allocated_gpus = []

        return driver_utils.HeavyNodeConfig(name=OPENCV_SVM_MODEL_APP_NAME,
                                            input_type="ints",
                                            model_image=OPENCV_SVM_IMAGE_NAME,
                                            allocated_cpus=allocated_cpus,
                                            cpus_per_replica=cpus_per_replica,
                                            gpus=allocated_gpus,
                                            batch_size=batch_size,
                                            num_replicas=num_replicas,
                                            use_nvidia_docker=True)


########## Benchmarking ##########

class Predictor(object):

    def __init__(self):
        self.outstanding_reqs = {}
        self.client = Client(CLIPPER_ADDRESS, CLIPPER_SEND_PORT, CLIPPER_RECV_PORT)
        self.client.start()
        self.init_stats()
        self.stats = {
            "thrus": [],
            "p99_lats": [],
            "mean_lats": []}
        self.total_num_complete = 0

    def init_stats(self):
        self.latencies = []
        self.batch_num_complete = 0
        self.cur_req_id = 0
        self.start_time = datetime.now()

    def print_stats(self):
        lats = np.array(self.latencies)
        p99 = np.percentile(lats, 99)
        mean = np.mean(lats)
        end_time = datetime.now()
        thru = float(self.batch_num_complete) / (end_time - self.start_time).total_seconds()
        self.stats["thrus"].append(thru)
        self.stats["p99_lats"].append(p99)
        self.stats["mean_lats"].append(mean)
        logger.info("p99: {p99}, mean: {mean}, thruput: {thru}".format(p99=p99,
                                                                       mean=mean,
                                                                       thru=thru))

    def predict(self, model_app_name, input_item):
        begin_time = datetime.now()
        def continuation(output):
            if output == DEFAULT_OUTPUT:
                return
            end_time = datetime.now()
            latency = (end_time - begin_time).total_seconds()
            self.latencies.append(latency)
            self.total_num_complete += 1
            self.batch_num_complete += 1
            if self.batch_num_complete % 50 == 0:
                self.print_stats()
                self.init_stats()

        return self.client.send_request(model_app_name, input_item).then(continuation)

class ModelBenchmarker(object):
    def __init__(self, config, queue):
        self.config = config
        self.queue = queue
        self.input_generator_fn = self._get_input_generator_fn(model_app_name=self.config.name)

    def run(self, duration_seconds=120):
        logger.info("Generating random inputs")
        inputs = [self.input_generator_fn() for _ in range(10000)]
        logger.info("Starting predictions")
        start_time = datetime.now()
        predictor = Predictor()
        for input_item in inputs:
            predictor.predict(model_app_name=self.config.name, input_item=input_item)
            # time.sleep(0.005)
            time.sleep(0)
        while True:
            curr_time = datetime.now()
            if ((curr_time - start_time).total_seconds() > duration_seconds) or (predictor.total_num_complete == 10000):
                break
            time.sleep(1)

        self.queue.put(predictor.stats)

    def _get_inception_input(self):
        input_img = np.array(np.random.rand(299, 299, 3) * 255, dtype=np.float32)
        return input_img.flatten()

    def _get_opencv_feats_input(self):
        input_img = np.array(np.random.rand(299, 299, 3) * 255, dtype=np.float32)
        return input_img.flatten()

    def _get_opencv_svm_input(self):
        return np.array(np.random.rand(NUM_SIFT_FEATURES * SIFT_FEATURE_VEC_SIZE) * 20, dtype=np.int32)

    def _get_input_generator_fn(self, model_app_name):
        if model_app_name == INCEPTION_MODEL_APP_NAME:
            return self._get_inception_input
        elif model_app_name == OPENCV_FEATS_MODEL_APP_NAME:
            return self._get_opencv_feats_input
        elif model_app_name == OPENCV_SVM_MODEL_APP_NAME:
            return self._get_opencv_svm_input

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Set up and benchmark models for Clipper image driver 1')
    parser.add_argument('-d', '--duration', type=int, default=120, help='The maximum duration of the benchmarking process in seconds, per iteration')
    parser.add_argument('-m', '--model_name', type=str, help="The name of the model to benchmark. One of: 'inception', 'opencv-feats', 'opencv-svm'")
    parser.add_argument('-b', '--batch_sizes', type=int, nargs='+', help="The batch size configurations to benchmark for the model. Each configuration will be benchmarked separately.")
    parser.add_argument('-r', '--num_replicas', type=int, nargs='+', help="The replica number configurations to benchmark for the model. Each configuration will be benchmarked separately.")
    parser.add_argument('-c', '--model_cpus', type=int, nargs='+', help="The set of cpu cores on which to run replicas of the provided model")
    parser.add_argument('-p', '--cpus_per_replica_nums', type=int, nargs='+', help="Configurations for the number of cpu cores allocated to each replica of the model")
    parser.add_argument('-g', '--model_gpus', type=int, nargs='+', help="The set of gpus on which to run replicas of the provided model. Each replica of a gpu model must have its own gpu!")
    parser.add_argument('-n', '--num_clients', type=int, default=1, help="The number of concurrent client processes. This can help increase the request rate in order to saturate high throughput models.")
    
    args = parser.parse_args()

    if args.model_name not in VALID_MODEL_NAMES:
        raise Exception("Model name must be one of: {}".format(VALID_MODEL_NAMES))

    default_batch_size_confs = [2]
    default_replica_num_confs = [1]
    default_cpus_per_replica_confs = [None]

    batch_size_confs = args.batch_sizes if args.batch_sizes else default_batch_size_confs
    replica_num_confs = args.num_replicas if args.num_replicas else default_replica_num_confs
    cpus_per_replica_confs = args.cpus_per_replica_nums if args.cpus_per_replica_nums else default_cpus_per_replica_confs


    for num_replicas in replica_num_confs:
        for cpus_per_replica in cpus_per_replica_confs:
            for batch_size in batch_size_confs:
                model_config = get_heavy_node_config(model_name=args.model_name, 
                                                     batch_size=batch_size, 
                                                     num_replicas=num_replicas,
                                                     cpus_per_replica=cpus_per_replica,
                                                     allocated_cpus=args.model_cpus,                               
                                                     allocated_gpus=args.model_gpus)
                setup_clipper(model_config)
                queue = Queue()
                benchmarker = ModelBenchmarker(model_config, queue)

                processes = []
                all_stats = []
                for _ in range(args.num_clients):
                    p = Process(target=benchmarker.run, args=(args.duration,))
                    p.start()
                    processes.append(p)
                for p in processes:
                    all_stats.append(queue.get())
                    p.join()

                cl = ClipperConnection(DockerContainerManager(redis_port=6380))
                cl.connect()
                driver_utils.save_results([model_config], cl, all_stats, "gpu_and_batch_size_experiments")