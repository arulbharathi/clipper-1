from __future__ import print_function

import random
import time
import numpy as np
import requests
import json

import grpc
import logging
import time

import clipper_frontend_pb2
import clipper_frontend_pb2_grpc

from clipper_admin import Clipper

DATA_TYPE_BYTES = 0
DATA_TYPE_INTS = 1
DATA_TYPE_FLOATS = 2
DATA_TYPE_DOUBLES = 3
DATA_TYPE_STRINGS = 4

logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%y-%m-%d:%H:%M:%S',
    level=logging.INFO)

logger = logging.getLogger(__name__)

input_type = "floats"
app_name = "a1"
model_name = "m1"


# def guide_get_one_feature(stub, point):
#   feature = stub.GetFeature(point)
#   if not feature.location:
#     print("Server returned incomplete feature")
#     return
#
#   if feature.name:
#     print("Feature called %s at %s" % (feature.name, feature.location))
#   else:
#     print("Found no feature at %s" % feature.location)
#
#
# def guide_get_feature(stub):
#   guide_get_one_feature(stub, route_guide_pb2.Point(latitude=409146138, longitude=-746188906))
#   guide_get_one_feature(stub, route_guide_pb2.Point(latitude=0, longitude=0))

def setup():
  clipper = Clipper("localhost", rpc_frontend=True, redis_port=6380)
  clipper.start()
  time.sleep(5)
  clipper.register_application(app_name, input_type, "default_pred", 100000)

  clipper.deploy_model(model_name,
      1,
      "/tmp/123456",
      "clipper/noop-container:develop",
      input_type,
      num_containers=1)
  clipper.link_model_to_app(app_name, model_name)

def setup_external():
  clipper = Clipper("localhost")
  clipper.register_application(app_name, input_type, "default_pred", 100000)

  clipper.register_external_model(model_name,
      1,
      input_type)
  clipper.link_model_to_app(app_name, model_name)

def run_rest():
    url = "http://localhost:1337/%s/predict" % app_name
    headers = {'Content-type': 'application/json'}
    while True:
      req_json = json.dumps({'input': list(np.random.random(299*299*3))})
      # start = datetime.now()
      r = requests.post(url, headers=headers, data=req_json)
    # end = datetime.now()
    # latency = (end - start).total_seconds() * 1000.0
    # print("'%s', %f ms" % (r.text, latency))



def run():
  channel = grpc.insecure_channel('localhost:1337')
  stub = clipper_frontend_pb2_grpc.PredictStub(channel)
  while True:
    for _ in range(100):
      x = clipper_frontend_pb2.FloatData(data=list(np.random.random(299*299*3)))
      req = clipper_frontend_pb2.PredictRequest(application=app_name, data_type=DATA_TYPE_FLOATS, float_data=x)
      response = stub.Predict(req)
      print(response)


if __name__ == '__main__':
  # setup_external()
  #run_rest()
  run()