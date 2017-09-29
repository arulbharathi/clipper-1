import sys
import os
import argparse
import numpy as np
import time
import base64
import logging

from clipper_admin import ClipperConnection, DockerContainerManager
from datetime import datetime
from io import BytesIO
from PIL import Image
from containerized_utils.zmq_client import Client
from containerized_utils import driver_utils
from multiprocessing import Process

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%y-%m-%d:%H:%M:%S',
    level=logging.INFO)

logger = logging.getLogger(__name__)

# Models and applications for each heavy node
# will share the same name
VGG_FEATS_MODEL_APP_NAME = "vgg"
VGG_SVM_MODEL_APP_NAME = "svm"
INCEPTION_FEATS_MODEL_APP_NAME = "inception"
LGBM_MODEL_APP_NAME = "lgbm"

VGG_FEATS_IMAGE_NAME = "model-comp/vgg-feats"
VGG_SVM_IMAGE_NAME = "model-comp/vgg-svm"
INCEPTION_FEATS_IMAGE_NAME = "model-comp/inception-feats"
LGBM_IMAGE_NAME = "model-comp/lgbm"

VALID_MODEL_NAMES = [
    VGG_FEATS_MODEL_APP_NAME,
    VGG_SVM_MODEL_APP_NAME,
    INCEPTION_FEATS_MODEL_APP_NAME,
    LGBM_MODEL_APP_NAME
]

CLIPPER_ADDRESS = "localhost"
CLIPPER_SEND_PORT = 4456
CLIPPER_RECV_PORT = 4455

########## Setup ##########

def setup_clipper(config):
    cl = ClipperConnection(DockerContainerManager(redis_port=6380))
    cl.stop_all()
    cl.start_clipper(
        query_frontend_image="clipper/zmq_frontend:develop",
        redis_cpu_str="0",
        mgmt_cpu_str="8",
        query_cpu_str="1-5,9-13")
    time.sleep(10)
    driver_utils.setup_heavy_node(cl, config)
    time.sleep(10)
    logger.info("Clipper is set up!")
    return config

def get_heavy_node_config(model_name, batch_size, num_replicas):
    if model_name == VGG_FEATS_MODEL_APP_NAME:
        return driver_utils.HeavyNodeConfig(name=VGG_FEATS_MODEL_APP_NAME,
                                            input_type="floats",
                                            model_image=VGG_FEATS_IMAGE_NAME,
                                            allocated_cpus=[6,7,14,15],
                                            cpus_per_replica=2,
                                            gpus=[0],
                                            batch_size=batch_size,
                                            num_replicas=num_replicas)

    elif model_name == INCEPTION_FEATS_MODEL_APP_NAME:
        return driver_utils.HeavyNodeConfig(name=INCEPTION_FEATS_MODEL_APP_NAME,
                                            input_type="strings",
                                            model_image=INCEPTION_FEATS_IMAGE_NAME,
                                            allocated_cpus=range(16,19),
                                            cpus_per_replica=1,
                                            gpus=[0],
                                            batch_size=batch_size,
                                            num_replicas=num_replicas)

    elif model_name == VGG_SVM_MODEL_APP_NAME:
        return driver_utils.HeavyNodeConfig(name=VGG_SVM_MODEL_APP_NAME,
                                            input_type="floats",
                                            model_image=VGG_SVM_IMAGE_NAME,
                                            allocated_cpus=range(20,27),
                                            cpus_per_replica=2,
                                            gpus=[],
                                            batch_size=batch_size,
                                            num_replicas=num_replicas)

    elif model_name == LGBM_MODEL_APP_NAME:
        return driver_utils.HeavyNodeConfig(name=LGBM_MODEL_APP_NAME,
                                            input_type="floats",
                                            model_image=LGBM_IMAGE_NAME,
                                            allocated_cpus=range(28,29),
                                            cpus_per_replica=1,
                                            gpus=[],
                                            batch_size=batch_size,
                                            num_replicas=num_replicas)


########## Benchmarking ##########

class Predictor(object):

    def __init__(self):
        self.outstanding_reqs = {}
        self.client = Client("localhost", 4456, 4455)
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
    def __init__(self, config):
        self.config = config
        self.input_generator_fn = self._get_input_generator_fn(model_app_name=self.config.name)

    def run(self, duration_seconds=120):
        logger.info("Generating random inputs")
        inputs = [self.input_generator_fn() for _ in range(5000)]
        logger.info("Starting predictions")
        start_time = datetime.now()
        predictor = Predictor()
        last_prediction_task_future = None
        for input_item in inputs:
            last_prediction_task_future = predictor.predict(model_app_name=self.config.name, input_item=input_item)
            time.sleep(0.005)
        while True:
            curr_time = datetime.now()
            if ((curr_time - start_time).total_seconds() > duration_seconds) or (predictor.total_num_complete == 5000):
                break
            time.sleep(1)


        cl = ClipperConnection(DockerContainerManager(redis_port=6380))
        cl.connect()
        driver_utils.save_results([self.config], cl, predictor.stats, "gpu_and_batch_size_experiments")

    def _get_vgg_feats_input(self):
        input_img = np.array(np.random.rand(299, 299, 3) * 255, dtype=np.float32)
        input_img = Image.fromarray(input_img.astype(np.uint8))
        vgg_img = input_img.resize((224, 224)).convert('RGB')
        vgg_input = np.array(vgg_img, dtype=np.float32)
        return vgg_input.flatten()

    def _get_vgg_svm_input(self):
        return np.array(np.random.rand(4096), dtype=np.float32)

    def _get_inception_input(self):
        input_img = np.array(np.random.rand(299, 299, 3) * 255, dtype=np.float32)
        input_img = Image.fromarray(input_img.astype(np.uint8))
        inmem_inception_jpeg = BytesIO()
        resized_inception = input_img.resize((299,299)).convert('RGB')
        resized_inception.save(inmem_inception_jpeg, format="JPEG")
        inmem_inception_jpeg.seek(0)
        inception_input = inmem_inception_jpeg.read()
        return base64.b64encode(inception_input)

    def _get_lgbm_input(self):
        return np.array(np.random.rand(2048), dtype=np.float32)

    def _get_input_generator_fn(self, model_app_name):
        if model_app_name == VGG_FEATS_MODEL_APP_NAME:
            return self._get_vgg_feats_input
        elif model_app_name == VGG_SVM_MODEL_APP_NAME:
            return self._get_vgg_svm_input
        elif model_app_name == INCEPTION_FEATS_MODEL_APP_NAME:
            return self._get_inception_input
        elif model_app_name == LGBM_MODEL_APP_NAME:
            return self._get_lgbm_input

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Set up and benchmark models for Clipper image driver 1')
    parser.add_argument('-n', '--num_procs', type=int, default=1, help='The number of benchmarking processes')
    parser.add_argument('-d', '--duration_seconds', type=int, default=120, help='The maximum duration of the benchmarking process')
    parser.add_argument('-m', '--model_name', type=str, help="The name of the model to benchmark")

    args = parser.parse_args()

    if args.model_name not in VALID_MODEL_NAMES:
        raise Exception("Model name must be one of: {}".format(VALID_MODEL_NAMES))

    batch_size, num_replicas = 4, 1

    # for num_replicas in range(1,5):
    #     for batch_size in [1,2,3,4,8,16,32]:
    model_config = get_heavy_node_config(model_name=args.model_name, batch_size=batch_size, num_replicas=num_replicas) 
    setup_clipper(model_config)
    benchmarker = ModelBenchmarker(model_config)

    processes = []
    for i in range(args.num_procs):
        p = Process(target=benchmarker.run, args=(args.duration_seconds,))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()