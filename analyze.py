import json
import matplotlib.pyplot as plt
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

# Ignore NONE in list
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

def getPacketLosses():

    mea_11 = mea_11_jitter.analyze.analyze(mea_11_jitter.analyze.readMeasurements("mea_11_jitter/out.json"))
    mea_12 = mea_12_xor_dpsk_10s.analyze.analyze(mea_12_xor_dpsk_10s.analyze.readMeasurements("mea_12_xor_dpsk_10s/out.json"))
    mea_13 = mea_13_xor_dpsk_20ms.analyze.analyze(mea_13_xor_dpsk_20ms.analyze.readMeasurements("mea_13_xor_dpsk_20ms/out.json"))
    mea_14 = mea_14_xor_dpsk_30ms.analyze.analyze(mea_14_xor_dpsk_30ms.analyze.readMeasurements("mea_14_xor_dpsk_30ms/out.json"))
    mea_15 = mea_15_xor_dpsk_40ms.analyze.analyze(mea_15_xor_dpsk_40ms.analyze.readMeasurements("mea_15_xor_dpsk_40ms/out.json"))
    mea_16 = mea_16_xor_dpsk_50ms.analyze.analyze(mea_16_xor_dpsk_50ms.analyze.readMeasurements("mea_16_xor_dpsk_50ms/out.json"))
    mea_17 = mea_17_xor_dpsk_60ms.analyze.analyze(mea_17_xor_dpsk_60ms.analyze.readMeasurements("mea_17_xor_dpsk_60ms/out.json"))
    mea_18 = mea_18_xor_dpsk_70ms.analyze.analyze(mea_18_xor_dpsk_70ms.analyze.readMeasurements("mea_18_xor_dpsk_70ms/out.json"))
    mea_19 = mea_19_xor_dpsk_100ms.analyze.analyze(mea_19_xor_dpsk_100ms.analyze.readMeasurements("mea_19_xor_dpsk_100ms/out.json"))

    packetlosses = [
        [
            "Jitter",
            "20ms",
            "30ms",
            "40ms",
            "50ms",
            "60ms",
            "70ms",
            "100ms",
            "10s",
        ],
        [
            (mea_11["numMsgsLost"] / len(mea_11["msgs"])) * 100,
            (mea_13["numMsgsLost"] / len(mea_13["msgs"])) * 100,
            (mea_14["numMsgsLost"] / len(mea_14["msgs"])) * 100,
            (mea_15["numMsgsLost"] / len(mea_15["msgs"])) * 100,
            (mea_16["numMsgsLost"] / len(mea_16["msgs"])) * 100,
            (mea_17["numMsgsLost"] / len(mea_17["msgs"])) * 100,
            (mea_18["numMsgsLost"] / len(mea_18["msgs"])) * 100,
            (mea_19["numMsgsLost"] / len(mea_19["msgs"])) * 100,
            (mea_12["numMsgsLost"] / len(mea_12["msgs"])) * 100,
        ]
    ]

    return packetlosses

def getBER():
    mea_11 = mea_11_jitter.analyze.analyze(mea_11_jitter.analyze.readMeasurements("mea_11_jitter/out.json"))
    mea_12 = mea_12_xor_dpsk_10s.analyze.analyze(mea_12_xor_dpsk_10s.analyze.readMeasurements("mea_12_xor_dpsk_10s/out.json"))
    mea_13 = mea_13_xor_dpsk_20ms.analyze.analyze(mea_13_xor_dpsk_20ms.analyze.readMeasurements("mea_13_xor_dpsk_20ms/out.json"))
    mea_14 = mea_14_xor_dpsk_30ms.analyze.analyze(mea_14_xor_dpsk_30ms.analyze.readMeasurements("mea_14_xor_dpsk_30ms/out.json"))
    mea_15 = mea_15_xor_dpsk_40ms.analyze.analyze(mea_15_xor_dpsk_40ms.analyze.readMeasurements("mea_15_xor_dpsk_40ms/out.json"))
    mea_16 = mea_16_xor_dpsk_50ms.analyze.analyze(mea_16_xor_dpsk_50ms.analyze.readMeasurements("mea_16_xor_dpsk_50ms/out.json"))
    mea_17 = mea_17_xor_dpsk_60ms.analyze.analyze(mea_17_xor_dpsk_60ms.analyze.readMeasurements("mea_17_xor_dpsk_60ms/out.json"))
    mea_18 = mea_18_xor_dpsk_70ms.analyze.analyze(mea_18_xor_dpsk_70ms.analyze.readMeasurements("mea_18_xor_dpsk_70ms/out.json"))
    mea_19 = mea_19_xor_dpsk_100ms.analyze.analyze(mea_19_xor_dpsk_100ms.analyze.readMeasurements("mea_19_xor_dpsk_100ms/out.json"))

    ber = [
        [
            "20ms",
            "30ms",
            "40ms",
            "50ms",
            "60ms",
            "70ms",
            "100ms",
            "10s",
        ],
        [
            (mea_13["numPhasesErrors"] / mea_13["numPhasesDecoded"]) * 100,
            (mea_14["numPhasesErrors"] / mea_14["numPhasesDecoded"]) * 100,
            (mea_15["numPhasesErrors"] / mea_15["numPhasesDecoded"]) * 100,
            (mea_16["numPhasesErrors"] / mea_16["numPhasesDecoded"]) * 100,
            (mea_17["numPhasesErrors"] / mea_17["numPhasesDecoded"]) * 100,
            (mea_18["numPhasesErrors"] / mea_18["numPhasesDecoded"]) * 100,
            (mea_19["numPhasesErrors"] / mea_19["numPhasesDecoded"]) * 100,
            (mea_12["numPhasesErrors"] / mea_12["numPhasesDecoded"]) * 100,
        ]
    ]
    return ber

def plot():
    packetloss = getPacketLosses()
    ber = getBER()

    # Arrange plots
    fig, axs = plt.subplots(1,2)
    fig.suptitle("XOR DPSK")

    # Print barchart of BER
    axs[0].bar(range(len(ber[1])), ber[1])
    axs[0].set_xticks(range(len(ber[1])))
    axs[0].set_xticklabels(ber[0])
    axs[0].set_title("BER")
    axs[0].set_ylabel("percent [%]")

    # Print barchart of packetloss
    axs[1].bar(range(len(packetloss[1])), packetloss[1])
    axs[1].set_xticks(range(len(packetloss[1])))
    axs[1].set_xticklabels(packetloss[0])
    axs[1].set_title("Packetloss")
    axs[1].set_ylabel("percent [%]")

    plt.show()

if __name__ == "__main__":
    plot()
