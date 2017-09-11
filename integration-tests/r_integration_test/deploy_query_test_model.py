import sys
import os
import time
import requests
import json

cur_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath("%s/../../clipper_admin" % cur_dir))

from clipper_admin import ClipperConnection, DockerContainerManager

APP_NAME = "rtest_app"
APP_DEFAULT_VALUE = "default"
APP_SLO = 10000000

INPUT_TYPE = "doubles"

MODEL_NAME = "rtest-model"
MODEL_VERSION = 1
MODEL_IMAGE_NAME = "rtest-model:1"


def create_application(conn):
    conn.register_application(APP_NAME, INPUT_TYPE, APP_DEFAULT_VALUE, APP_SLO)


def deploy_and_link_model(conn):
    conn.deploy_model(MODEL_NAME, MODEL_VERSION, INPUT_TYPE, MODEL_IMAGE_NAME)
    conn.link_model_to_app(APP_NAME, MODEL_NAME)


def send_requests():
    for i in range(0, 5):
        url = "http://localhost:1337/%s/predict" % APP_NAME
        input_item = [float(j) for j in range(0, i + 1)]
        req_json = json.dumps({'input': input_item})
        headers = {'Content-type': 'application/json'}
        r = requests.post(url, headers=headers, data=req_json)
        print(r.text)
        response_json = json.loads(r.text)
        assert (not response_json["default"])
        assert (int(response_json["output"]) == len(input_item))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage is 'python deploy_query_test_model.py <redis_port>")

    redis_port = int(sys.argv[1])

    mgr = DockerContainerManager(redis_port=redis_port)
    conn = ClipperConnection(mgr)
    conn.stop_all()
    conn.start_clipper()

    create_application(conn)
    deploy_and_link_model(conn)

    time.sleep(5)

    send_requests()
    conn.stop_all()
    print("Success!")