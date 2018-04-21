import json
import sys
import os
import numpy as np
import math

from collections import OrderedDict

from e2e_utils import load_arrival_deltas, calculate_mean_throughput, calculate_peak_throughput

ARRIVAL_PROCS_DIR = "cached_arrival_processes"

def get_mean_throughput(config_path):
    with open(config_path, "r") as f:
        config_json = json.load(f)

    thrus = [float(thru) for thru in config_json["client_metrics"][0]["thrus"]]
    return np.mean(thrus)

def load_relevant_arrival_procs(procs_dir, cv):
    deltas_dict = {}
    if cv == 1:
        fnames = [os.path.join(procs_dir, fname) for fname in os.listdir(procs_dir) if ("deltas" in fname) and "_" not in fname]
    else:
        fnames = [os.path.join(procs_dir, fname) for fname in os.listdir(procs_dir) if ("deltas" in fname) and str(cv) in fname]
    for fname in fnames:
        print(fname)
        deltas_subname = fname.split("/")[1]
        if "_" in deltas_subname:
            delta = int(deltas_subname.split("_")[0])
        else:
            delta = int(deltas_subname.split(".")[0])

        deltas_dict[delta] = load_arrival_deltas(fname)

    return OrderedDict(sorted(deltas_dict.items()))

def probe_throughputs(eval_fn, arrival_process):
    curr_min = 0
    curr_max = len(arrival_process)
    highest_successful_config = None
    while True:
        if curr_max == curr_min:
            break
        middle = curr_min + math.ceil((curr_max - curr_min) / 2)
        print("PROBING. min: {}, max: {}, middle: {}".format(
            curr_min, curr_max, middle))

        result = eval_fn(int(middle))

        if result:
            curr_min = middle
            highest_successful_config = result
        else:
            # Pad middle by a small number to account for the fact
            # that peak throughput does not always monotonically
            # increase with lambda
            curr_max = min(curr_max - 1, (middle + 16) - 1)
    return highest_successful_config
        

def find_peak_arrival_proc(arrival_procs, target_thrus, slo_window_millis=350):
    
    def eval_fn(middle, target_thru):
        key = arrival_procs.keys()[middle]
        peak_thru = calculate_peak_throughput(arrival_procs[key], slo_window_millis=slo_window_millis)
        if peak_thru <= target_thru:
            return (key, peak_thru)
        else:
            return None

    outputs = {}
    for thru in target_thrus: 
        peak_thru = probe_throughputs(lambda middle : eval_fn(middle, thru), arrival_procs)
        outputs[thru] = peak_thru

    return outputs

def find_mean_arrival_proc(arrival_procs, target_thrus):
    
    def eval_fn(middle, target_thru):
        key = arrival_procs.keys()[middle]
        mean_thru = calculate_mean_throughput(arrival_procs[key])
        if mean_thru <= target_thru:
            return (key, mean_thru)
        else:
            return None

    outputs = {}
    for thru in target_thrus: 
        peak_thru = probe_throughputs(lambda middle : eval_fn(middle, thru), arrival_procs)
        outputs[thru] = peak_thru

    return outputs