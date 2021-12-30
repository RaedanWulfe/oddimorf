#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""
Runs all example scripts.
"""

import os
import subprocess

from flask import Flask, request
from flask_restful import Resource, Api
from subprocess import PIPE

python_command = "python"
processes = []
supervisor = None
supervisor_url = 'http://localhost:8070'
dirs = [
    "control",
    "data_feeder",
    "emulator",
    "processor",
    "recorder",
    "spoofer",
    "tracker_matlab"
]

class Shutdown(Resource):
    def get(self):
        try:
            for process in processes:
                process.terminate()
            print(f"supervisor halted, terminating all associated processes...")
        finally:
            shutdown_hook = request.environ.get(supervisor_url)
            if shutdown_hook is not None:
                shutdown_hook()
            return "terminate received"

# -----------------------------------------------------------------------------
# Execute requisite logic
if __name__ == '__main__':
    supervisor = Flask(__name__)
    api = Api(supervisor)
    api.add_resource(Shutdown, '/shutdown')

    print(f"initializing associated processes...")

    for dir in dirs:
        processes.append(subprocess.Popen([python_command, os.path.join(
            os.path.dirname(__file__), dir + "/main.py")], stdout=PIPE, stderr=PIPE))

    print(f"initialized {len(processes)} processes to supervisor (terminate by accessing {supervisor_url})...")
    supervisor.run(port=8070)

    print(f"supervisor launched")
