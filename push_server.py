"""
A simple webserver to demonstrate SocketIO workflow. To run install:

  $ pip install flask flask-socketio simple-websocket

and run this file. It uses the signal system to generate random data and stream
via websocket to browser. The sampling rate of the system and the rate at
which data is streamed can be set independently using the constants SAMPLING_RATE
and GUI_UPDATE_RATE.
"""
import argparse

from flask import Flask, render_template
from flask_socketio import SocketIO

from threading import Lock
import sys
from pathlib import Path

from signal_processing.data_sources import (
    ManualTimerDataSource,
    RandomDataSource,
    MouseDataSource,
    WaveDataSource,
)  # noqa: E402
from signal_processing.system import SignalSystem  # noqa: E402
import signal_processing.signals as s  # noqa: E402

app = Flask(__name__)
socketio = SocketIO(app)

thread_lock = Lock()
data_thread = None

SAMPLING_RATE = 100
GUI_UPDATE_RATE = 60
BLE_ADDRESS = "905EC87A-AD3A-3CE7-21AE-9C97B8CA54E1"


def generate_data():
    # source = ManualTimerDataSource(
    #     SAMPLING_RATE, secondary_sources=[RandomDataSource(), MouseDataSource()]
    # )
    print("background ---------------")
    source = WaveDataSource(
        ble_address=BLE_ADDRESS, secondary_sources=[RandomDataSource(), MouseDataSource()]
    )
    system = SignalSystem(source, derived=[s.SamplingRate()])
    with system:
        while True:
            data = system.read(as_dataframe=False)
            if("timestamp_us" in data):
                data = [
                    { k: v[i].tolist() for k, v in data.items() }
                    for i in range(len(data["timestamp_us"])) # NOTE: Error prone since if data is empty this will fail
                ] # dict of lists to list of dicts
                socketio.emit("response", data, broadcast=True, namespace="/data")
            socketio.sleep(1 / GUI_UPDATE_RATE)


@app.route("/")
def index():
    return render_template("plot.html")


@socketio.on("connect", namespace="/data")
def handle_connect():
    print("client connected")

def main(host, port, debug):
    data_thread = socketio.start_background_task(generate_data)
    socketio.run(app, host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--debug", action="store_true", default=False)
    args = parser.parse_args()
    
    main(host=args.host, port=args.port, debug=args.debug)
