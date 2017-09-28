from setuptools import setup
import os

setup(
    name='zmq_client',
    version='1.0.0',
    description='A ZMQ-based client for querying Clipper',
    maintainer='Corey Zumar',
    maintainer_email='czumar@berkeley.edu',
    url='http://clipper.ai',
    packages=[
        "zmq_client"
    ],
    install_requires=[
        'numpy',
        'pyzmq'
    ])