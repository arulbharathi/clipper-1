import sys
import os
import time
import logging
import tensorflow as tf
import subprocess

from datetime import datetime

from grpc.beta import implementations
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%y-%m-%d:%H:%M:%S',
    level=logging.INFO)

logger = logging.getLogger(__name__)

# Change this if necessary
TFS_BASE_PATH = "~/tfserving"

MODEL_SERVER_RELATIVE_PATH = "bazel-bin/tensorflow_serving/model_servers/tensorflow_model_server"

class TFSHeavyNodeConfig(object):
    def __init__(self,
                 name,
                 model_base_path,
                 ports,
                 input_type,
                 allocated_cpus,
                 cpus_per_replica,
                 num_replicas,
                 gpus,
                 batch_size):
        assert len(ports) >= num_replicas
        assert len(allocated_cpus) >= cpus_per_replica * num_replicas

        self.name = name
        self.model_base_path = model_base_path
        self.ports = ports
        self.input_type = input_type
        self.allocated_cpus = allocated_cpus
        self.cpus_per_replica = cpus_per_replica
        self.slo = slo
        self.num_replicas = num_replicas
        self.gpus = gpus
        self.batch_size = batch_size
        self.instance_type = requests.get(
            "http://169.254.169.254/latest/meta-data/instance-type").text
        if len(gpus) == 0:
            self.gpus_per_replica = 0
        else:
            self.gpus_per_replica = 1

    def to_json(self):
        return json.dumps(self.__dict__)

def save_results(configs, client_metrics, results_dir, prefix="results"):
    """
    Parameters
    ----------
    configs : list(HeavyNodeConfig)
        The configs for any models deployed
    """

    results_dir = os.path.abspath(os.path.expanduser(results_dir))
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        logger.info("Created experiments directory: %s" % results_dir)

    results_obj = {
        "node_configs": [c.__dict__ for c in configs],
        "client_metrics": client_metrics,
    }
    results_file = os.path.join(results_dir, "{prefix}-{ts:%y%m%d_%H%M%S}.json".format(
        prefix=prefix, ts=datetime.datetime.now()))
    with open(results_file, "w") as f:
        json.dump(results_obj, f, indent=4)
        logger.info("Saved results to {}".format(results_file))

def create_predict_request(model_name, data, signature_name="predict_images"):
    request = predict_pb2.PredictRequest()
    request.model_spec.name = model_name
    request.model_spec.signature_name = signature_name
    request.inputs['inputs'].CopyFrom(tf.contrib.util.make_tensor_proto(data, shape=data.shape))

def setup_heavy_node(config):
    for _ in range(config.num_replicas):
        if len(config.gpus) > 0:
            node_gpu = config.gpus.pop()

        node_cpus = []
        for _ in range(config.cpus_per_replica):
            node_cpus.append(config.allocated_cpus.pop())

        port_number = config.ports.pop()

        _start_serving(config, port_number, node_gpu, node_cpus)

def _start_serving(config, port_number, gpu_number, cpus):
    model_server_path = os.path.join(TFS_BASE_PATH, MODEL_SERVER_RELATIVE_PATH)

    batching_params = _get_batching_params(config.batch_size)
    batching_params_path = os.path.join("/tmp", "batching_params-{%y%m%d_%H%M%S}.json".format(prefix=prefix, ts=datetime.datetime.now()))

    batching_params_file = open(batching_params_path, "w")
    batching_params_file.write(batching_params)
    batching_params_file.close()

    cpus_str = ", ".join(["%d"] * len(cpus)) % tuple(cpus)
    cmd_filter_cpus = "numactl -C {cpus}".format(cpus=cpus_str)

    cmd_filter_gpus = "export CUDA_VISIBLE_DEVICES={gpu}".format(gpu=gpu_number)

    cmd_serve = ("{cf} {msp} --enable_batching \\",
                "--port {pn} \\",
                "--model_name {mn} \\",
                "--model_base_path {mbp} \\",
                "--batching_parameters_file {bpf}").format(cf=cmd_filter_cpus,
                                                           msp=model_server_path,
                                                           pn=port_number,
                                                           mn=config.model_name,
                                                           mbp=config.model_base_path,
                                                           bpf=batching_params_path)

    subprocess.call(cmd_filter_gpus, shell=True)
    subprocess.call(cmd_serve, shell=True)

    print("Started node! model name: {mn} port: {pn} gpu_num: {gpu} cpu_num: {cpu}".format(mn=config.model_name, 
                                                                                           pn=port_number,
                                                                                           gpu_number=gpu_number,
                                                                                           cpu_number=cpu_number))


def _get_batching_params(max_batch_size, batch_timeout_micros=5000, max_enqueued_batches=4):
    batching_params_text = ("max_batch_size \{ value : {mbs} \}",
                            "batch_timeout_micros \{ value : {btm} \}",
                            "max_enqueued_batches \{ value : {meb} \}"
                            "num_batch_threads { value : {nbt} \}")

    num_batch_threads = max_batch_size * 2

    formatted_params = batching_params_text.format(mbs=max_batch_size,
                                                   btm=batch_timeout_micros,
                                                   meb=max_enqueued_batches,
                                                   nbt=num_batch_threads)

    return formatted_params