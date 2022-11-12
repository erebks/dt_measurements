import json
import matplotlib.pyplot as plt
import sys
import numpy as np
import copy

sys.path.append('../')

# importing
import helper

# Ignore NONE in list
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

FILE = "out.json"
PRINT_MATCHES = False
NOMINAL_S = 300
TOLERANCE_S = 0.020
PHASE_DELTA_S = 0.040
BITS = 1
HIST_BINS = 200
SUBPLOT_SIZE = [4,3]
SUPTITLE = "DPSK 40 ms"

def readMeasurements(f=FILE):
    in_file = open(f, "r")
    data = json.loads(in_file.read())
    in_file.close()
    return data

def analyze(measurements):
    return helper.readMessages(measurements, NOMINAL_S, TOLERANCE_S, PHASE_DELTA_S, BITS, PRINT_MATCHES, gw_ts_name="gwTs")

def plot():
    res = analyze(readMeasurements())

    msgs = res["msgs"]

    # Check if messages are ordered correctly
    msg_id_head = 0
    for msg in msgs:
        if (msg_id_head+1 < msg["loraMsgId"]):
            print("{0} Packet(s) missing at {1}".format(msg["loraMsgId"] - (msg_id_head+1), msg["loraMsgId"]))
        elif (msg_id_head+1 > msg["loraMsgId"]):
            print("Something is very wrong here! head: {0} id: {1}".format(msg_id_head, msg["loraMsgId"]))
        msg_id_head = msg["loraMsgId"]

    # Arrange plots
    fig, axs = plt.subplots(SUBPLOT_SIZE[0],SUBPLOT_SIZE[1])
    fig.suptitle(SUPTITLE)

    # Print x-y diagram of absolute timestamps
    axs[0][0].plot(list(ele["loraMsgId"] for ele in msgs), list(ele["gwTs"]["seconds"] for ele in msgs), "r.-")
    axs[0][0].set_title("Absolute timestamps")
    axs[0][0].set_xlabel('msg')
    axs[0][0].set_ylabel('gateway timestamp [s]', color='r')
    axs[0][0].tick_params('y', colors='r')
    axs[0][0].grid(True)

    ax002 = axs[0][0].twinx()

    ax002.plot(list(ele["loraMsgId"] for ele in msgs), list(ele["payload"]["seconds"] for ele in msgs), "b.-")
    ax002.set_ylabel('mcu timestamp [s]', color='b')
    ax002.tick_params('y', colors='b')

    # Print x-y diagram of delta timestamps

    axs[0][1].plot(list(ele["loraMsgId"] for ele in msgs), list(ele["gwTs"]["delta"] for ele in msgs), "r.-")
    axs[0][1].set_title("Delta timestamps")
    axs[0][1].set_xlabel('msg')
    axs[0][1].set_ylabel('gateway delta timestamp [s]', color='r')
    axs[0][1].tick_params('y', colors='r')
    axs[0][1].grid(True)

    axs[0][2].plot(list(ele["loraMsgId"] for ele in msgs), list(ele["payload"]["delta"] for ele in msgs), "b.-")
    axs[0][2].set_title("Delta timestamps")
    axs[0][2].set_xlabel('msg')
    axs[0][2].set_ylabel('mcu delta timestamp [s]', color='b')
    axs[0][2].tick_params('y', colors='b')
    axs[0][2].grid(True)

    axs[1][1].plot(list(ele["loraMsgId"] for ele in msgs), list(ele["modemTs"]["delta"] for ele in msgs), "r.-")
    axs[1][1].set_title("Delta timestamps")
    axs[1][1].set_xlabel('msg')
    axs[1][1].set_ylabel('gateway delta timestamp [s]', color='r')
    axs[1][1].tick_params('y', colors='r')
    axs[1][1].grid(True)

    axs[1][2].plot(list(ele["loraMsgId"] for ele in msgs), list(ele["modemTs"]["seconds"] for ele in msgs), "r.-")
    axs[1][2].set_title("Delta timestamps")
    axs[1][2].set_xlabel('msg')
    axs[1][2].set_ylabel('gateway delta timestamp [s]', color='r')
    axs[1][2].tick_params('y', colors='r')
    axs[1][2].grid(True)

    # Print histogram
    # Get rid of packet loss and
    # normalize to first value received and pad to ms
    y1 = np.array(list(ele["payload"]["delta"] for ele in msgs), float)
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in msgs), float)
    y3 = np.array(list(ele["nwTs"]["delta"] for ele in msgs), float)
    y4 = np.array(list(ele["modemTs"]["delta"] for ele in msgs), float)

    y1 = ((y1) - NOMINAL_S * 1000)
    y2 = ((y2) - NOMINAL_S) * 1000
    y3 = ((y3) - NOMINAL_S) * 1000
    y4 = ((y4) - NOMINAL_S) * 1000

    axs[1][0].hist(y1, bins=HIST_BINS, color='b')
    axs[1][0].set_title("Histogram mcu timestamps")
    axs[1][0].set_xlabel("ms")

    axs[2][0].hist(y2, bins=HIST_BINS, color='r')
    axs[2][0].set_title("Histogram gateway timestamps")
    axs[2][0].set_xlabel("ms")

    axs[2][1].hist(y4, bins=HIST_BINS, color='r')
    axs[2][1].set_title("Histogram gateway timestamps")
    axs[2][1].set_xlabel("ms")

    axs[3][0].hist(y3, bins=HIST_BINS, color='g')
    axs[3][0].set_title("Histogram network timestamps")
    axs[3][0].set_xlabel("ms")

    helper.printCalculations(res)

    plt.show()

if __name__ == "__main__":
    plot()
