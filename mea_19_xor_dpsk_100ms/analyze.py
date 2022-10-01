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
TOLERANCE_S = 0.05
HIST_BINS = 200
SUBPLOT_SIZE = [4,3]
SUPTITLE = "DPSK 100 ms"

def readMeasurements(f=FILE):
    in_file = open(f, "r")
    data = json.loads(in_file.read())
    in_file.close()
    return data

def analyze(measurements):
    return helper.readMessages(measurements, NOMINAL_S, TOLERANCE_S, PRINT_MATCHES)

def plot():

    res = analyze(readMeasurements())

    msgs = res["msgs"]
    numMsgsLost = res["numMsgsLost"]
    numPhasesDecoded = res["numPhasesDecoded"]
    numPhasesErrors = res["numPhasesErrors"]

    # Check if messages are ordered correctly
    msg_id_head = 0
    for msg in msgs:
        if (msg_id_head+1 < msg["lora_msg_id"]):
            print("{0} Packet(s) missing at {1}".format(msg["lora_msg_id"] - (msg_id_head+1), msg["lora_msg_id"]))
        elif (msg_id_head+1 > msg["lora_msg_id"]):
            print("Something is very wrong here! head: {0} id: {1}".format(msg_id_head, msg["lora_msg_id"]))

        msg_id_head = msg["lora_msg_id"]

    # Arrange plots
    fig, axs = plt.subplots(SUBPLOT_SIZE[0],SUBPLOT_SIZE[1])
    fig.suptitle(SUPTITLE)

    # Print x-y diagram of absolute timestamps
    axs[0][0].plot(list(ele["lora_msg_id"] for ele in msgs), list(ele["gw_timestamp"] for ele in msgs), "r.-")
    axs[0][0].set_title("Absolute timestamps")
    axs[0][0].set_xlabel('msg')
    axs[0][0].set_ylabel('gateway timestamp [s]', color='r')
    axs[0][0].tick_params('y', colors='r')
    axs[0][0].grid(True)

    ax002 = axs[0][0].twinx()

    ax002.plot(list(ele["lora_msg_id"] for ele in msgs), list(ele["mcu_timestamp_s"] for ele in msgs), "b.-")
    ax002.set_ylabel('mcu timestamp [s]', color='b')
    ax002.tick_params('y', colors='b')

    # Print x-y diagram of delta timestamps

    axs[0][1].plot(list(ele["lora_msg_id"] for ele in msgs), list(ele["gw_timestamp_delta"] for ele in msgs), "r.-")
    axs[0][1].set_title("Delta timestamps")
    axs[0][1].set_xlabel('msg')
    axs[0][1].set_ylabel('gateway delta timestamp [s]', color='r')
    axs[0][1].tick_params('y', colors='r')
    axs[0][1].grid(True)

    axs[0][2].plot(list(ele["lora_msg_id"] for ele in msgs), list(ele["mcu_timestamp_delta"] for ele in msgs), "b.-")
    axs[0][2].set_title("Delta timestamps")
    axs[0][2].set_xlabel('msg')
    axs[0][2].set_ylabel('mcu delta timestamp [s]', color='b')
    axs[0][2].tick_params('y', colors='b')
    axs[0][2].grid(True)

    # Print histogram
    # Get rid of packet loss and
    # normalize to first value received and pad to ms
    y1 = np.array(list(ele["mcu_timestamp_delta"] for ele in msgs), float)
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in msgs), float)
    y3 = np.array(list(ele["nw_timestamp_delta"] for ele in msgs), float)

    y1 = ((y1) - NOMINAL_S * 1000)
    y2 = ((y2) - NOMINAL_S) * 1000
    y3 = ((y3) - NOMINAL_S) * 1000

    axs[1][0].hist(y1, bins=HIST_BINS, color='b')
    axs[1][0].set_title("Histogram mcu timestamps")
    axs[1][0].set_xlabel("ms")

    axs[2][0].hist(y2, bins=HIST_BINS, color='r')
    axs[2][0].set_title("Histogram gateway timestamps")
    axs[2][0].set_xlabel("ms")

    axs[3][0].hist(y3, bins=HIST_BINS, color='g')
    axs[3][0].set_title("Histogram network timestamps")
    axs[3][0].set_xlabel("ms")

    # Print detailed histogram
    # THIS NEEDS TO BE ADJUSTED FOR EVERY PLOT

    # Only TS at 0s
    gw_ts = np.array(list(ele["gw_timestamp_delta"] for ele in msgs), float)
    gw_ts = (gw_ts - NOMINAL_S) * 1000
    gw_ts = gw_ts[gw_ts < 5000]
    gw_ts = gw_ts[gw_ts > -100]

    axs[2][1].hist(gw_ts, bins=HIST_BINS, color='r')
    axs[2][1].set_title("Histogram GW timestamps (@ 0ms)")
    axs[2][1].set_xlabel("ms")

    # Print detailed histogram

    # Only TS at 0s
    nw_ts = np.array(list(ele["nw_timestamp_delta"] for ele in msgs), float)
    nw_ts = (nw_ts - NOMINAL_S) * 1000
    nw_ts = nw_ts[nw_ts < 5000]
    nw_ts = nw_ts[nw_ts > -100]

    axs[3][1].hist(nw_ts, bins=HIST_BINS, color='g')
    axs[3][1].set_title("Histogram NW timestamps (@ 0ms)")
    axs[3][1].set_xlabel("ms")

    # Show calculations
    y1 = []
    for ele in msgs:
        if not (ele["gw_timestamp_delta"] == None):
            y1.append(ele["gw_timestamp_delta"]*1000)

    y1 = np.array(y1)

    print("Packetloss: \n\t{0} (of {1} sent) = {2:.2f}%".format(numMsgsLost, msgs[-1]["lora_msg_id"], (numMsgsLost/msgs[-1]["lora_msg_id"])*100))

    print("Jitter:")
    print("\tmin:  {0:.2f} ms".format(np.min(y1)))
    print("\tmax:  {0:.2f} ms".format(np.max(y1)))
    print("\tavg:  {0:.2f} ms".format(np.average(y1)))
    print("\tmean: {0:.2f} ms".format(np.mean(y1)))

    print("Phases:")
    print("\tDecoded: {0}".format(numPhasesDecoded))
    print("\tCorrect: {0}\t({1:.2f}%)".format(numPhasesDecoded-numPhasesErrors, ((numPhasesDecoded-numPhasesErrors) / numPhasesDecoded)*100))
    print("\tErrors:  {0}\t({1:.2f}%)".format(numPhasesErrors, (numPhasesErrors / numPhasesDecoded)*100))

    print("Duration: {0}h".format((msgs[-1]["gw_timestamp"] - msgs[0]["gw_timestamp"])/(60*60)))

    plt.show()

def paperPlot():
    res = analyze(readMeasurements())

    msgs = res["msgs"]
    numMsgsLost = res["numMsgsLost"]
    numPhasesDecoded = res["numPhasesDecoded"]
    numPhasesErrors = res["numPhasesErrors"]

    # Print x-y diagram of delta timestamps

    plt.plot(list(ele["lora_msg_id"] for ele in msgs), list(ele["gw_timestamp_delta"] for ele in msgs), "b.-")
    plt.title("100ms: Delta timestamps")
    plt.xlabel('msg')
    plt.ylabel('gateway delta timestamp [s]')
    plt.tick_params('y')
    plt.grid(True)

    plt.show()

    # Only TS at 0s
    gw_ts = np.array(list(ele["gw_timestamp_delta"] for ele in msgs), float)
    gw_ts = (gw_ts - NOMINAL_S) * 1000

    plt.hist(gw_ts, bins=HIST_BINS, color='b')
    plt.title("100ms: Histogram of gateway timestamps")
    plt.xlabel("ms")
    plt.grid(True)

    plt.show()

if __name__ == "__main__":
    plot()
