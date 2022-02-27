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
NOMINAL_S = 600
TOLERANCE_S = 1
HIST_BINS = 200
SUBPLOT_SIZE = [4,3]
SUPTITLE = "Jitter"

def readMeasurements(f=FILE):
    in_file = open(f, "r")
    data = json.loads(in_file.read())
    in_file.close()
    return data

def analyze(measurements):
    #numMsgsLost, msgs = helper.readMessages(measurements, NOMINAL_S, TOLERANCE_S, PRINT_MATCHES)
    return helper.readMessages(measurements, NOMINAL_S, TOLERANCE_S, PRINT_MATCHES)

def plot():

    res = analyze(readMeasurements())

    msgs = res["msgs"]
    numMsgsLost = res["numMsgsLost"]
    numPhasesDecoded = res["numPhasesDecoded"]
    numPhasesErrors = res["numPhasesErrors"]

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

    # Show calculations
    y1 = []
    for ele in msgs:
        if not (ele["gw_timestamp_delta"] == None):
            y1.append(ele["gw_timestamp_delta"]*1000)

    y1 = np.array(y1)

    print("Packetloss: \n\t{0} (of {1} = {2:.2f}%)".format(numMsgsLost, len(msgs), (numMsgsLost/len(msgs))*100))

    print("Jitter:")
    print("\tmin:  {0:.2f} ms".format(np.min(y1)))
    print("\tmax:  {0:.2f} ms".format(np.max(y1)))
    print("\tavg:  {0:.2f} ms".format(np.average(y1)))
    print("\tmean: {0:.2f} ms".format(np.mean(y1)))

    duration_gw = msgs[-1]["gw_timestamp"] - msgs[0]["gw_timestamp"]
    duration_mcu = msgs[-1]["mcu_timestamp_s"] - msgs[0]["mcu_timestamp_s"]
    deviation = abs(duration_gw-duration_mcu)
    print("Clock deviation:")
    print("\tDuration GW:  {0:.2f} s".format(duration_gw))
    print("\tDuration MCU: {0:.2f} s".format(duration_mcu))
    print("\tDeviation:    {0:.2f} ms ({1:.2f} ppm)".format(deviation*1000, (deviation/duration_gw)*1000000))

    plt.show()

if __name__ == "__main__":
    plot()
