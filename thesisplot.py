import json
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import sys
import numpy as np
import copy

#import helper

import mea_11_jitter.analyze
import mea_12_xor_dpsk_10s.analyze
import mea_13_xor_dpsk_20ms.analyze
import mea_14_xor_dpsk_30ms.analyze
import mea_15_xor_dpsk_40ms.analyze
import mea_16_xor_dpsk_50ms.analyze
import mea_17_xor_dpsk_60ms.analyze
import mea_18_xor_dpsk_70ms.analyze
import mea_19_xor_dpsk_100ms.analyze
import mea_20_xor_dpsk_nojumpback_100ms.analyze
import mea_21_xor_dpsk_nojumpback_50ms.analyze
import mea_22_xor_8bit.analyze
import mea_24_xor_2bit.analyze
import mea_25_xor_4bit.analyze
import analyze

# Ignore NONE in list
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

def plot():
    mea_11 = mea_11_jitter.analyze.analyze(mea_11_jitter.analyze.readMeasurements("mea_11_jitter/out.json"))
    mea_12 = mea_12_xor_dpsk_10s.analyze.analyze(mea_12_xor_dpsk_10s.analyze.readMeasurements("mea_12_xor_dpsk_10s/out.json"))
    mea_13 = mea_13_xor_dpsk_20ms.analyze.analyze(mea_13_xor_dpsk_20ms.analyze.readMeasurements("mea_13_xor_dpsk_20ms/out.json"))
    mea_14 = mea_14_xor_dpsk_30ms.analyze.analyze(mea_14_xor_dpsk_30ms.analyze.readMeasurements("mea_14_xor_dpsk_30ms/out.json"))
    mea_15 = mea_15_xor_dpsk_40ms.analyze.analyze(mea_15_xor_dpsk_40ms.analyze.readMeasurements("mea_15_xor_dpsk_40ms/out.json"))
    mea_16 = mea_16_xor_dpsk_50ms.analyze.analyze(mea_16_xor_dpsk_50ms.analyze.readMeasurements("mea_16_xor_dpsk_50ms/out.json"))
    mea_17 = mea_17_xor_dpsk_60ms.analyze.analyze(mea_17_xor_dpsk_60ms.analyze.readMeasurements("mea_17_xor_dpsk_60ms/out.json"))
    mea_18 = mea_18_xor_dpsk_70ms.analyze.analyze(mea_18_xor_dpsk_70ms.analyze.readMeasurements("mea_18_xor_dpsk_70ms/out.json"))
    mea_19 = mea_19_xor_dpsk_100ms.analyze.analyze(mea_19_xor_dpsk_100ms.analyze.readMeasurements("mea_19_xor_dpsk_100ms/out.json"))
    mea_20 = mea_20_xor_dpsk_nojumpback_100ms.analyze.analyze(mea_20_xor_dpsk_nojumpback_100ms.analyze.readMeasurements("mea_20_xor_dpsk_nojumpback_100ms/nojump_100ms.json"))
    mea_21 = mea_21_xor_dpsk_nojumpback_50ms.analyze.analyze(mea_21_xor_dpsk_nojumpback_50ms.analyze.readMeasurements("mea_21_xor_dpsk_nojumpback_50ms/nojump_50ms.json"))
    mea_22 = mea_22_xor_8bit.analyze.analyze(mea_22_xor_8bit.analyze.readMeasurements("mea_22_xor_8bit/8bit.json"))
    mea_24 = mea_24_xor_2bit.analyze.analyze(mea_24_xor_2bit.analyze.readMeasurements("mea_24_xor_2bit/2bit.json"))
    mea_25 = mea_25_xor_4bit.analyze.analyze(mea_25_xor_4bit.analyze.readMeasurements("mea_25_xor_4bit/4bit.json"))

    packetloss = analyze.getPacketLosses()
    ber = analyze.getBER()

    # Print barchart of BER
    plt.bar(range(len(ber[1])), ber[1])
    plt.xticks(range(len(ber[1])), ber[0])
#    plt.axes.Axes.set_xticklabels(ber[0])
#    plt.title("Phases wrongly decoded")
    plt.ylabel("[%]")
    plt.grid(linestyle='--', axis='y')
    plt.savefig("phase_errors.svg")
    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # Print barchart of packetloss
#    plt.bar(range(len(packetloss[1])), packetloss[1])
#    plt.xticks(range(len(packetloss[1])),packetloss[0])
#  plt.axes.Axes.set_xticklabels(packetloss[0])
#    plt.title("Packetloss")
#    plt.ylabel("[%]")
#    plt.grid(linestyle='--', axis='y')
#    plt.savefig("packetloss.svg")
#    plt.show()
#    plt.clf()
#    plt.cla()
#    plt.close()

    # Print hist of jitter
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_11["msgs"]), float)
    y2 = ((y2) - mea_11_jitter.analyze.NOMINAL_S) * 1000
    y2 = y2[2:] # Delete first, this is an outlier

    plt.hist(y2, bins=mea_11_jitter.analyze.HIST_BINS, color='b')
#    plt.title("Jitter: Histogram of gateway timestamps")
    plt.xlabel("ms")
#    plt.grid(True)
    plt.savefig("hist_jitter.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # Print delta of 10s
    plt.plot(list(ele["gw_timestamp_delta"] for ele in mea_12["msgs"]), list(ele["lora_msg_id"] for ele in mea_12["msgs"]), "b.-")
    plt.xlabel('gateway delta timestamp [s]')
    plt.ylabel('msg')
    plt.tick_params('y')
    plt.grid(True)
    plt.savefig("delta_10s.svg")
    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # Print hist of 10s
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_12["msgs"]), float)
    y2 = ((y2) - mea_12_xor_dpsk_10s.analyze.NOMINAL_S) * 1000
    y2 = y2[y2 > -1000]

    plt.hist(y2, bins=mea_12_xor_dpsk_10s.analyze.HIST_BINS, color='b')
    plt.xlabel("ms")
#    plt.grid(True)
    plt.savefig("hist_10s.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # Print delta of 100ms
    plt.plot(list(ele["lora_msg_id"] for ele in mea_19["msgs"]), list(ele["gw_timestamp_delta"] for ele in mea_19["msgs"]), "b.-")
#    plt.title("100ms: Delta timestamps")
    plt.xlabel('msg')
    plt.ylabel('gateway delta timestamp [s]')
    plt.tick_params('y')
    plt.grid(True)
    plt.savefig("delta_100ms.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # Print hist of 100ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_19["msgs"]), float)
    y2 = ((y2) - mea_19_xor_dpsk_100ms.analyze.NOMINAL_S) * 1000
    y2 = y2[y2 > -200]

    plt.hist(y2, bins=mea_19_xor_dpsk_100ms.analyze.HIST_BINS, color='b')
    plt.xlabel("ms")
#    plt.grid(True)
    plt.savefig("hist_100ms.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # Print hist of all
#    fig, axs = plt.subplots(2, 4, figsize=(10,5))
    fig, axs = plt.subplots(4, 2, figsize=(10,7))
    fig.tight_layout(h_pad=2)

    # 20ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_13["msgs"]), float)
    y2 = ((y2) - mea_13_xor_dpsk_20ms.analyze.NOMINAL_S) * 1000
    axs[0][0].hist(y2, bins=mea_13_xor_dpsk_20ms.analyze.HIST_BINS, color='b')
    axs[0][0].set_title("a) 20 ms")
#    axs[0][0].set_xlabel("ms", fontsize=8)

    # 30ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_14["msgs"]), float)
    y2 = ((y2) - mea_14_xor_dpsk_30ms.analyze.NOMINAL_S) * 1000
    axs[0][1].hist(y2, bins=mea_14_xor_dpsk_30ms.analyze.HIST_BINS, color='b')
    axs[0][1].set_title("b) 30 ms")
#    axs[0][1].set_xlabel("ms", fontsize=8)

    # 40ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_15["msgs"]), float)
    y2 = ((y2) - mea_15_xor_dpsk_40ms.analyze.NOMINAL_S) * 1000
    axs[1][0].hist(y2, bins=mea_15_xor_dpsk_40ms.analyze.HIST_BINS, color='b')
    axs[1][0].set_title("c) 40 ms")
#    axs[1][0].set_xlabel("ms", fontsize=8)

    # 50ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_16["msgs"]), float)
    y2 = ((y2) - mea_16_xor_dpsk_50ms.analyze.NOMINAL_S) * 1000
    axs[1][1].hist(y2, bins=mea_16_xor_dpsk_50ms.analyze.HIST_BINS, color='b')
    axs[1][1].set_title("d) 50 ms")
#    axs[1][2].set_xlabel("ms", fontsize=8)

    # 60ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_17["msgs"]), float)
    y2 = ((y2) - mea_17_xor_dpsk_60ms.analyze.NOMINAL_S) * 1000
    axs[2][0].hist(y2, bins=mea_17_xor_dpsk_60ms.analyze.HIST_BINS, color='b')
    axs[2][0].set_title("e) 60 ms")
#    axs[2][0].set_xlabel("ms", fontsize=8)

    # 70ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_18["msgs"]), float)
    y2 = ((y2) - mea_18_xor_dpsk_70ms.analyze.NOMINAL_S) * 1000
    axs[2][1].hist(y2, bins=mea_18_xor_dpsk_70ms.analyze.HIST_BINS, color='b')
    axs[2][1].set_title("f) 70 ms")
#    axs[2][1].set_xlabel("ms", fontsize=8)

    # 100ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_19["msgs"]), float)
    y2 = ((y2) - mea_19_xor_dpsk_100ms.analyze.NOMINAL_S) * 1000
    axs[3][0].hist(y2, bins=mea_19_xor_dpsk_100ms.analyze.HIST_BINS, color='b')
    axs[3][0].set_title("g) 100 ms")
    axs[3][0].set_xlabel("ms", fontsize=8)

    # 10 s
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_12["msgs"]), float)
    y2 = ((y2) - mea_12_xor_dpsk_10s.analyze.NOMINAL_S) * 1000
    axs[3][1].hist(y2, bins=mea_12_xor_dpsk_10s.analyze.HIST_BINS, color='b')
    axs[3][1].set_title("h) 10 s")
    axs[3][1].set_xlabel("ms", fontsize=8)
    plt.savefig("hist.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # nojumpback measurements plots
    # 100ms delta
    plt.plot(list(ele["lora_msg_id"] for ele in mea_20["msgs"]), list(ele["gw_timestamp_delta"] for ele in mea_20["msgs"]), "b.-")
    plt.xlabel('msg')
    plt.ylabel('gateway delta timestamp [s]')
    plt.tick_params('y')
    plt.grid(True)
    plt.savefig("delta_100ms_nojumpback.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # 50ms + 100ms hist
    fig, axs = plt.subplots(1, 2, figsize=(7,3))
    fig.tight_layout(h_pad=2)

    # 50ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_21["msgs"]), float)
    y2 = ((y2) - mea_21_xor_dpsk_nojumpback_50ms.analyze.NOMINAL_S) * 1000
    axs[0].hist(y2, bins=mea_21_xor_dpsk_nojumpback_50ms.analyze.HIST_BINS, color='b')
    axs[0].set_title("a) 50 ms")
    axs[0].set_xlabel("ms", fontsize=8)

    # 100ms
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_20["msgs"]), float)
    y2 = ((y2) - mea_20_xor_dpsk_nojumpback_100ms.analyze.NOMINAL_S) * 1000
    axs[1].hist(y2, bins=mea_20_xor_dpsk_nojumpback_100ms.analyze.HIST_BINS, color='b')
    axs[1].set_title("b) 100 ms")
    axs[1].set_xlabel("ms", fontsize=8)
    plt.savefig("hist_nojumpback.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # nbit plots
    # plot deltas of 2 bit encoding
    plt.plot(list(ele["lora_msg_id"] for ele in mea_24["msgs"])[900:1100], list(ele["gw_timestamp_delta"] for ele in mea_24["msgs"])[900:1100], "b.-")
    plt.xlabel('msg')
    plt.ylabel('gateway delta timestamp [s]')
    plt.tick_params('y')
    plt.grid(True)
    plt.savefig("delta_2bit.svg")
    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # plot hist of all nbits
#    fig, axs = plt.subplots(2, 2, figsize=(7,3))
    fig = plt.figure()
    fig.tight_layout(h_pad=2)
    gs = GridSpec(2,2, figure=fig)
    ax1 = fig.add_subplot(gs[0,0])
    ax2 = fig.add_subplot(gs[0,1])
    ax3 = fig.add_subplot(gs[1,:])

    # 2bit
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_24["msgs"]), float)
    y2 = ((y2) - mea_24_xor_2bit.analyze.NOMINAL_S) * 1000
    ax1.hist(y2, bins=mea_24_xor_2bit.analyze.HIST_BINS, color='b')
    ax1.set_title("a) 2 bit")

    # 4bit
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_25["msgs"]), float)
    y2 = ((y2) - mea_25_xor_4bit.analyze.NOMINAL_S) * 1000
    ax2.hist(y2, bins=mea_25_xor_4bit.analyze.HIST_BINS, color='b')
    ax2.set_title("b) 4 bit")

    # 4bit
    y2 = np.array(list(ele["gw_timestamp_delta"] for ele in mea_22["msgs"]), float)
    y2 = ((y2) - mea_22_xor_8bit.analyze.NOMINAL_S) * 1000
    ax3.hist(y2, bins=mea_22_xor_8bit.analyze.HIST_BINS, color='b')
    ax3.set_title("c) 8 bit")
    ax3.set_xlabel("ms", fontsize=8)

    plt.savefig("hist_nbit.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()



if __name__ == "__main__":
    plot()
