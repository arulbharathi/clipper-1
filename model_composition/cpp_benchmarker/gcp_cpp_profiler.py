import subprocess32 as subprocess
import os
import sys
import numpy as np
import time
import logging
import json
from clipper_admin import ClipperConnection
from clipper_admin.gcp.gcp_container_manager import GCPContainerManager
from datetime import datetime
from containerized_utils import driver_utils

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%y-%m-%d:%H:%M:%S',
    level=logging.INFO)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = "TIMEOUT"

RES50 = "res50"
RES152 = "res152"
ALEXNET = "alexnet"
INCEPTION_FEATS = "inception"
TF_KERNEL_SVM = "tf-kernel-svm"
TF_LOG_REG = "tf-log-reg"
TF_RESNET = "tf-resnet-feats"


def get_heavy_node_config(model_name,
                          batch_size,
                          num_replicas,
                          cpus_per_replica,
                          gpu_type):

    if model_name == ALEXNET:
        image = "gcr.io/clipper-model-comp/pytorch-alexnet:bench"
        return driver_utils.HeavyNodeConfigGCP(name="alexnet",
                                               input_type="floats",
                                               model_image=image,
                                               cpus_per_replica=cpus_per_replica,
                                               gpu_type=gpu_type,
                                               batch_size=batch_size,
                                               num_replicas=num_replicas,
                                               no_diverge=True)

    elif model_name == RES50:
        image = "gcr.io/clipper-model-comp/pytorch-res50:bench"
        return driver_utils.HeavyNodeConfigGCP(name="res50",
                                               input_type="floats",
                                               model_image=image,
                                               cpus_per_replica=cpus_per_replica,
                                               gpu_type=gpu_type,
                                               batch_size=batch_size,
                                               num_replicas=num_replicas,
                                               no_diverge=True)

    elif model_name == RES152:
        image = "gcr.io/clipper-model-comp/pytorch-res152:bench"
        return driver_utils.HeavyNodeConfigGCP(name="res152",
                                               input_type="floats",
                                               model_image=image,
                                               cpus_per_replica=cpus_per_replica,
                                               gpu_type=gpu_type,
                                               batch_size=batch_size,
                                               num_replicas=num_replicas,
                                               no_diverge=True)

    elif model_name == INCEPTION_FEATS:
        image = "gcr.io/clipper-model-comp/inception-feats:bench"
        return driver_utils.HeavyNodeConfigGCP(name=INCEPTION_FEATS,
                                               input_type="floats",
                                               model_image=image,
                                               cpus_per_replica=cpus_per_replica,
                                               gpu_type=gpu_type,
                                               batch_size=batch_size,
                                               num_replicas=num_replicas,
                                               no_diverge=True)

    elif model_name == TF_RESNET:
        image = "gcr.io/clipper-model-comp/tf-resnet-feats:bench"
        return driver_utils.HeavyNodeConfigGCP(name=TF_RESNET,
                                               input_type="floats",
                                               model_image=image,
                                               cpus_per_replica=cpus_per_replica,
                                               gpu_type=gpu_type,
                                               batch_size=batch_size,
                                               num_replicas=num_replicas,
                                               no_diverge=True)

    elif model_name == TF_LOG_REG:
        image = "gcr.io/clipper-model-comp/tf-log-reg:bench"
        return driver_utils.HeavyNodeConfigGCP(name=TF_LOG_REG,
                                               input_type="floats",
                                               model_image=image,
                                               cpus_per_replica=cpus_per_replica,
                                               gpu_type=gpu_type,
                                               batch_size=batch_size,
                                               num_replicas=num_replicas,
                                               no_diverge=True)

    elif model_name == TF_KERNEL_SVM:
        image = "gcr.io/clipper-model-comp/tf-kernel-svm:bench"
        return driver_utils.HeavyNodeConfigGCP(name=TF_KERNEL_SVM,
                                               input_type="floats",
                                               model_image=image,
                                               cpus_per_replica=cpus_per_replica,
                                               gpu_type=gpu_type,
                                               batch_size=batch_size,
                                               num_replicas=num_replicas,
                                               no_diverge=True)


def get_input_size(name):
    if name in [TF_LOG_REG, TF_KERNEL_SVM]:
        return 2048
    elif name in [ALEXNET, RES50, RES152, INCEPTION_FEATS]:
        return 299*299*3
    elif name in [TF_RESNET, ]:
        return 224*224*3


def setup_clipper_gcp(configs):
    cl = ClipperConnection(GCPContainerManager(GCP_CLUSTER_NAME))
    cl.stop_all()
    cl.start_clipper()
    time.sleep(30)
    for c in configs:
        driver_utils.setup_heavy_node_gcp(cl, c, DEFAULT_OUTPUT)
    time.sleep(10)
    clipper_address = cl.cm.query_frontend_internal_ip
    logger.info("Clipper is set up on {}".format(clipper_address))
    return clipper_address


def get_clipper_batch_sizes(metrics_json):
    hists = metrics_json["histograms"]
    mean_batch_sizes = {}
    for h in hists:
        if "batch_size" in h.keys()[0]:
            name = h.keys()[0]
            model = name.split(":")[1]
            mean = float(h[name]["mean"])
            mean_batch_sizes[model] = round(float(mean), 2)
    return mean_batch_sizes


def get_clipper_queue_sizes(metrics_json):
    hists = metrics_json["histograms"]
    mean_queue_sizes = {}
    for h in hists:
        if "queue_size" in h.keys()[0]:
            name = h.keys()[0]
            model = name.split(":")[0]
            mean = float(h[name]["mean"])
            mean_queue_sizes[model] = round(float(mean), 2)
    return mean_queue_sizes


def get_clipper_thruputs(metrics_json):
    meters = metrics_json["meters"]
    thrus = {}
    for m in meters:
        if "prediction_throughput" in m.keys()[0]:
            name = m.keys()[0]
            rate = float(m[name]["rate"])
            thrus[name] = round(float(rate), 5)
    return thrus


def get_clipper_counts(metrics_json):
    counters = metrics_json["counters"]
    counts = {}
    for c in counters:
        if "internal" not in c.keys()[0]:
            name = c.keys()[0]
            count = c[name]["count"]
            counts[name] = int(count)
    return counts


def get_profiler_stats(metrics_json):
    mean_latencies = {}
    p99_latencies = {}
    thrus = {}
    counts = {}

    hists = metrics_json["histograms"]
    for h in hists:
        if "prediction_latency" in h.keys()[0]:
            name = h.keys()[0]
            model = name.split(":")[0]
            mean = float(h[name]["mean"]) / 1000.0
            p99 = float(h[name]["p99"]) / 1000.0
            mean_latencies[model] = round(float(mean), 3)
            p99_latencies[model] = round(float(p99), 3)
    meters = metrics_json["meters"]
    for m in meters:
        if "prediction_throughput" in m.keys()[0]:
            name = m.keys()[0]
            model = name.split(":")[0]
            rate = float(m[name]["rate"])
            thrus[model] = round(float(rate), 5)
    counters = metrics_json["counters"]
    counts = {}
    for c in counters:
        if "num_predictions" in c.keys()[0]:
            name = c.keys()[0]
            model = name.split(":")[0]
            count = c[name]["count"]
            counts[model] = int(count)
    return (mean_latencies, p99_latencies, thrus, counts)


def print_stats(client_metrics, clipper_metrics):
    results_dict = {}
    results_dict["batch_sizes"] = get_clipper_batch_sizes(clipper_metrics)
    results_dict["queue_sizes"] = get_clipper_queue_sizes(clipper_metrics)
    results_dict["clipper_thrus"] = get_clipper_thruputs(clipper_metrics)
    results_dict["clipper_counts"] = get_clipper_counts(clipper_metrics)
    results_dict["client_mean_lats"], results_dict["client_p99_lats"], \
        results_dict["client_thrus"], results_dict["client_counts"] = \
        get_profiler_stats(client_metrics)
    # logger.info(("\nClient thrus: {client_thrus}, clipper thrus: {clipper_thrus} "
    #              "\nclient counts: {client_counts}, clipper counts: {clipper_counts}, "
    #              "\nclient p99 lats: {client_p99_lats}, client mean lats: {client_mean_lats} "
    #              "\nqueue sizes: {queue_sizes}, "
    #              "batch sizes: {batch_sizes}").format(**results_dict))
    logger.info(("\nThroughput: {client_thrus}, p99 lat: {client_p99_lats}, "
                 "mean lat: {client_mean_lats} "
                 "\nqueues: {queue_sizes}, batches: {batch_sizes}, "
                 "counts: {client_counts}\n").format(**results_dict))
    return results_dict


def load_metrics(client_path, clipper_path):
    with open(client_path, "r") as client_file, \
            open(clipper_path, "r") as clipper_file:
        client_metrics_str = client_file.read().strip()
        clipper_metrics_str = clipper_file.read().strip()
        if client_metrics_str[-1] == ",":
            client_metrics_str = client_metrics_str.rstrip(",")
            client_metrics_str += "]"
        if clipper_metrics_str[-1] == ",":
            clipper_metrics_str = clipper_metrics_str.rstrip(",")
            clipper_metrics_str += "]"
        try:
            client_metrics = json.loads(client_metrics_str)
        except ValueError as e:
            # logger.warn("Unable to parse client metrics: {}. Skipping...".format(e))
            return None
        try:
            clipper_metrics = json.loads(clipper_metrics_str)
        except ValueError as e:
            # logger.warn("Unable to parse clipper metrics: {}. Skipping...".format(e))
            return None
    return client_metrics, clipper_metrics


def run_profiler(config, trial_length, driver_path, input_size, init_delay=1000):
    clipper_address = setup_clipper_gcp([config, ])
    cl = ClipperConnection(GCPContainerManager(GCP_CLUSTER_NAME))
    cl.connect()
    time.sleep(100)
    log_dir = "/tmp/{name}_profiler_logs_{ts:%y%m%d_%H%M%S}".format(name=config.name,
                                                                    ts=datetime.now())
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    def run(delay_micros, num_trials, name):
        cl.drain_queues()
        time.sleep(10)
        cl.drain_queues()
        time.sleep(10)
        log_path = os.path.join(log_dir, "{n}-delay-{d}".format(n=name, d=delay_micros))
        cmd = [os.path.abspath(driver_path),
               "--name={}".format(config.name),
               "--input_type={}".format(config.input_type),
               "--input_size={}".format(input_size),
               "--request_delay_micros={}".format(delay_micros),
               "--trial_length={}".format(trial_length),
               "--num_trials={}".format(num_trials),
               "--log_file={}".format(log_path),
               "--clipper_address={}".format(clipper_address)]
        logger.info("Driver command: {}".format(" ".join(cmd)))
        client_path = "{p}-client_metrics.json".format(p=log_path)
        clipper_path = "{p}-clipper_metrics.json".format(p=log_path)
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            recorded_trials = 0
            summary_results = []
            while recorded_trials < num_trials:
                time.sleep(5)
                if proc.poll() is not None:
                    if proc.returncode != 0:
                        logger.warn("Driver process finished with return code {}".format(
                            proc.returncode))
                        break
                    # else:
                    #     logger.warn("Driver process finished without enough trials. "
                    #                 "Expected {num}, recorded {rec}".format(num=num_trials,
                    #                                                         rec=recorded_trials))
                if not (os.path.exists(client_path) and os.path.exists(clipper_path)):
                    logger.info("metrics don't exist yet")
                    continue
                loaded_metrics = load_metrics(client_path, clipper_path)
                if loaded_metrics is not None:
                    client_metrics, clipper_metrics = loaded_metrics
                else:
                    logger.info("Couldn't load metrics")
                    continue
                client_trials = len(client_metrics)
                clipper_trials = len(clipper_metrics)
                if clipper_trials != client_trials:
                    logger.warn(("Clipper trials ({}) and client trials ({}) not the "
                                 "same length").format(clipper_trials, client_trials))
                else:
                    new_recorded_trials = clipper_trials
                    if new_recorded_trials > recorded_trials:
                        recorded_trials = new_recorded_trials
                        summary_results.append(print_stats(client_metrics[-1],
                                                           clipper_metrics[-1]))

            # prof_stdout = proc.stdout.read().strip()
            # if len(prof_stdout) > 0:
            #     logger.info("Profiler stdout: {}".format(prof_stdout))
            prof_stderr = proc.stderr.read().strip()
            if len(prof_stderr) > 0:
                logger.info("stderr: {}".format(prof_stderr))
            try:
                loaded_metrics = load_metrics(client_path, clipper_path)
                if loaded_metrics is not None:
                    client_metrics, clipper_metrics = loaded_metrics
                    return (client_metrics, clipper_metrics, summary_results)
                else:
                    logger.error("Error loading final metrics")
            except ValueError as e:
                logger.error("Unable to parse final metrics")
                raise e

    delay_micros = init_delay
    run(delay_micros, 15, "warmup")
    _, _, init_results = run(delay_micros, 15, "init")
    mean_thruput = np.mean([r["client_thrus"][config.name] for r in init_results][1:])
    steady_state_delay = int(round(1.0 / mean_thruput * 1000.0 * 1000.0))
    logger.info("Setting delay to {delay} (mean throughput was: {thru})".format(
        delay=steady_state_delay, thru=mean_thruput))
    steady_results = run(steady_state_delay, 30, "steady_state")
    cl.stop_all()
    return steady_results


if __name__ == "__main__":

    global GCP_CLUSTER_NAME
    num_cpus = 2
    for gpu in ["p100", "k80"]:
        for model in [TF_RESNET, INCEPTION_FEATS, TF_KERNEL_SVM]:
            GCP_CLUSTER_NAME = "smp-cascade-{}".format(model)
            for batch_size in [1, 2, 4, 8, 16, 24, 32, 48, 64]:
                if gpu == "k80" and batch_size > 32:
                    continue
                if gpu == "p100" and model == TF_RESNET and batch_size <= 32:
                    continue
                config = get_heavy_node_config(
                    model_name=model,
                    batch_size=batch_size,
                    num_replicas=1,
                    cpus_per_replica=num_cpus,
                    gpu_type=gpu)

                input_size = get_input_size(config.name)
                client_mets, clipper_mets, summary_mets = run_profiler(
                    config, 2000, "../../release/src/inferline_client/profiler", input_size,
                    init_delay=1000)
                fname = "cpp-gcp-results-batch-{batch}-{gpu}".format(batch=batch_size, gpu=gpu)
                results_dir = "{model}_smp_gcp_cpp_profiling_round".format(model=model)
                driver_utils.save_results_cpp_client([config, ],
                                                     client_mets,
                                                     clipper_mets,
                                                     summary_mets,
                                                     results_dir,
                                                     prefix=fname)

    # num_cpus = 2
    # model = ALEXNET
    # for gpu in ["p100", "k80"]:
    #     GCP_CLUSTER_NAME = "smp-cascade-{}".format(model)
    #     for batch_size in [1, 2, 4, 8, 16, 24, 32]:
    #         config = get_heavy_node_config(
    #             model_name=model,
    #             batch_size=batch_size,
    #             num_replicas=1,
    #             cpus_per_replica=num_cpus,
    #             gpu_type=gpu)
    #
    #         input_size = get_input_size(config.name)
    #         client_mets, clipper_mets, summary_mets = run_profiler(
    #             config, 2000, "../../release/src/inferline_client/profiler",
    #             input_size, init_delay=500)
    #         fname = "cpp-results-batch-{batch}-{gpu}".format(batch=batch_size, gpu=gpu)
    #         results_dir = "pytorch_{model}_smp_gcp_cpp_profiling".format(model=model)
    #         driver_utils.save_results_cpp_client([config, ],
    #                                              client_mets,
    #                                              clipper_mets,
    #                                              summary_mets,
    #                                              results_dir,
    #                                              prefix=fname)
    sys.exit(0)
