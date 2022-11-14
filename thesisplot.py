import json
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib import colors
import sys
import numpy as np
import copy

# Setup standard size
WIDTH_cm = 21 - 5 - 2   # A4 = 21cm, with -5cm margins from tex -2 cm for text
HEIGHT_cm = WIDTH_cm/1.5  # 1:1.5 aspect

# Matplotlib does only know inches...
WIDTH = WIDTH_cm * 1/2.54
HEIGHT = HEIGHT_cm * 1/2.54

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
import mea_27_xor_4bit_lfsr_fix.analyze
import mea_28_xor_4bit_lfsr_ss.analyze
import mea_29_xor_4bit_hamming_50ms.analyze
import mea_30_xor_4bit_feld.analyze
import mea_31_xor_4bit_hochstand.analyze
import analyze

# Ignore NONE in list
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

def plot_single_hist(data, bins, filename, color='b', xlabel='ms', ylabel='frequency', show=False):
    fig, ax = plt.subplots(figsize=(WIDTH, HEIGHT))
    ax.hist(data, bins=bins, color=color)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    plt.savefig(filename, bbox_inches = "tight")
    if show:
        plt.show()

    # Reset plt
    plt.clf()
    plt.cla()
    plt.close()


def plot_single_hist_with_norm(data, mu, sigma, bins, filename, color='b', xlabel='ms', ylabel='density', show=False):
    fig, ax = plt.subplots(figsize=(WIDTH, HEIGHT))
    count, bins, ignored = ax.hist(data, bins=bins, color=color, density=True)

    plt.plot(bins, 1/(sigma * np.sqrt(2 * np.pi)) * np.exp( - (bins - mu)**2 / (2 * sigma**2) ), color='r')

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    plt.savefig(filename, bbox_inches = "tight")
    if show:
        plt.show()

    # Reset plt
    plt.clf()
    plt.cla()
    plt.close()

def plot_single_ipd(data, filename, color='b.-', xlabel='msg', ylabel='IPD at gateway [s]', show=False):
    fig, ax = plt.subplots(figsize=(WIDTH, HEIGHT))
    ax.plot(data[0], data[1], color)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params('y')
    ax.grid(True)

    plt.savefig(filename, bbox_inches = "tight")
    if show:
        plt.show()

    # Reset plt
    plt.clf()
    plt.cla()
    plt.close()

def plot_temp_vdd(msgs, temp, vdd, msgs_received, filename, xlabel='msg', legend_loc='best', show=False):
    fig, (ax0, ax1) = plt.subplots(2, 1, sharex=True, figsize=(WIDTH, HEIGHT), gridspec_kw=dict(height_ratios=[15, 1]))

    # temp
    line_temp = ax0.plot(msgs, temp, color = "b", label='Temperature')
    ax0.set_ylabel("[°C]")
    ax0.tick_params('y', colors='b')

    ax002 = ax0.twinx()

    line_vdd = ax002.plot(msgs, vdd, color = "r", marker = "v", markevery=0.2, label='Vdd')
    ax002.set_ylabel('[V]')
    ax002.tick_params('y', colors='r')

    handles0, labels0 = ax0.get_legend_handles_labels()
    handles002, labels002 = ax002.get_legend_handles_labels()

    ax0.legend(handles=handles0 + handles002, labels=labels0 + labels002, loc=legend_loc)

    plt.setp(ax0.get_xticklabels(), visible=False)
    plt.setp(ax1.get_yticklabels(), visible=False)
    yticks = ax1.yaxis.get_major_ticks()
    yticks[-1].label1.set_visible(False)

    cmap = colors.ListedColormap(['darkgray', 'palegreen'])
    bounds=[0,0.5,1]
    norm = colors.BoundaryNorm(bounds, cmap.N)

    ax1.imshow(msgs_received, aspect='auto', cmap=cmap, norm=norm)
    ax1.set_xlabel(xlabel)

    plt.subplots_adjust(hspace=.0)

    plt.savefig(filename, bbox_inches = "tight")
    if show:
        plt.show()

    # Reset plt
    plt.clf()
    plt.cla()
    plt.close()


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
    mea_27 = mea_27_xor_4bit_lfsr_fix.analyze.analyze(mea_27_xor_4bit_lfsr_fix.analyze.readMeasurements("mea_27_xor_4bit_lfsr_fix/4bit_lfsr.json"))
    mea_28 = mea_28_xor_4bit_lfsr_ss.analyze.analyze(mea_28_xor_4bit_lfsr_ss.analyze.readMeasurements("mea_28_xor_4bit_lfsr_ss/4bit_ss.json"))
    mea_29 = mea_29_xor_4bit_hamming_50ms.analyze.analyze(mea_29_xor_4bit_hamming_50ms.analyze.readMeasurements("mea_29_xor_4bit_hamming_50ms/ecc_50ms.json"))
    mea_30 = mea_30_xor_4bit_feld.analyze.analyze(mea_30_xor_4bit_feld.analyze.readMeasurements("mea_30_xor_4bit_feld/feld.json"))

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
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()

    # Print PDF of jitter
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_11["msgs"]), float)
    y2 = ((y2) - mea_11_jitter.analyze.NOMINAL_S) * 1000
    y2 = y2[2:] # Delete first, this is an outlier

    plot_single_hist_with_norm(
        data=y2,
        mu=-4.4027,
        sigma=8.58411,
        bins=mea_11_jitter.analyze.HIST_BINS,
        filename="hist_jitter_pdf.svg"
    )

    # Print delta of 10s
    ipd = [list(ele["loraMsgId"] for ele in mea_12["msgs"]), list(ele["gwTs"]["delta"] for ele in mea_12["msgs"])]
    plot_single_ipd(
        data = ipd,
        filename = "delta_10s.svg"
    )

    # Print hist of 10s
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_12["msgs"]), float)
    y2 = ((y2) - mea_12_xor_dpsk_10s.analyze.NOMINAL_S) * 1000
    y2 = y2[y2 > -1000]

    plot_single_hist(
        data=y2,
        bins=mea_12_xor_dpsk_10s.analyze.HIST_BINS,
        filename="hist_10s.svg"
    )

    # Print delta of 100ms

    ipd = [list(ele["loraMsgId"] for ele in mea_19["msgs"]), list(ele["gwTs"]["delta"] for ele in mea_19["msgs"])]
    plot_single_ipd(
        data = ipd,
        filename = "delta_100ms.svg"
    )

    # Print hist of 100ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_19["msgs"]), float)
    y2 = ((y2) - mea_19_xor_dpsk_100ms.analyze.NOMINAL_S) * 1000
    y2 = y2[y2 > -200]

    plot_single_hist(
        data=y2,
        bins=mea_19_xor_dpsk_100ms.analyze.HIST_BINS,
        filename="hist_100ms.svg"
    )

    # Print hist of all
#    fig, axs = plt.subplots(2, 4, figsize=(10,5))
    fig, axs = plt.subplots(4, 2, figsize=(10,7))
    fig.tight_layout(h_pad=2)

    # 20ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_13["msgs"]), float)
    y2 = ((y2) - mea_13_xor_dpsk_20ms.analyze.NOMINAL_S) * 1000
    axs[0][0].hist(y2, bins=mea_13_xor_dpsk_20ms.analyze.HIST_BINS, color='b')
    axs[0][0].set_title("a) 20 ms")
    axs[0][0].set_ylabel("frequency")
#    axs[0][0].set_xlabel("ms", fontsize=8)

    # 30ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_14["msgs"]), float)
    y2 = ((y2) - mea_14_xor_dpsk_30ms.analyze.NOMINAL_S) * 1000
    axs[0][1].hist(y2, bins=mea_14_xor_dpsk_30ms.analyze.HIST_BINS, color='b')
    axs[0][1].set_title("b) 30 ms")
#    axs[0][1].set_xlabel("ms", fontsize=8)

    # 40ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_15["msgs"]), float)
    y2 = ((y2) - mea_15_xor_dpsk_40ms.analyze.NOMINAL_S) * 1000
    axs[1][0].hist(y2, bins=mea_15_xor_dpsk_40ms.analyze.HIST_BINS, color='b')
    axs[1][0].set_title("c) 40 ms")
#    axs[1][0].set_xlabel("ms", fontsize=8)

    # 50ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_16["msgs"]), float)
    y2 = ((y2) - mea_16_xor_dpsk_50ms.analyze.NOMINAL_S) * 1000
    axs[1][1].hist(y2, bins=mea_16_xor_dpsk_50ms.analyze.HIST_BINS, color='b')
    axs[1][1].set_title("d) 50 ms")
#    axs[1][2].set_xlabel("ms", fontsize=8)

    # 60ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_17["msgs"]), float)
    y2 = ((y2) - mea_17_xor_dpsk_60ms.analyze.NOMINAL_S) * 1000
    axs[2][0].hist(y2, bins=mea_17_xor_dpsk_60ms.analyze.HIST_BINS, color='b')
    axs[2][0].set_title("e) 60 ms")
#    axs[2][0].set_xlabel("ms", fontsize=8)

    # 70ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_18["msgs"]), float)
    y2 = ((y2) - mea_18_xor_dpsk_70ms.analyze.NOMINAL_S) * 1000
    axs[2][1].hist(y2, bins=mea_18_xor_dpsk_70ms.analyze.HIST_BINS, color='b')
    axs[2][1].set_title("f) 70 ms")
#    axs[2][1].set_xlabel("ms", fontsize=8)

    # 100ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_19["msgs"]), float)
    y2 = ((y2) - mea_19_xor_dpsk_100ms.analyze.NOMINAL_S) * 1000
    axs[3][0].hist(y2, bins=mea_19_xor_dpsk_100ms.analyze.HIST_BINS, color='b')
    axs[3][0].set_title("g) 100 ms")
    axs[3][0].set_xlabel("ms", fontsize=8)

    # 10 s
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_12["msgs"]), float)
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


    ipd = [list(ele["loraMsgId"] for ele in mea_20["msgs"])[:121], list(ele["gwTs"]["delta"] for ele in mea_20["msgs"])[:121]]
    plot_single_ipd(
        data = ipd,
        filename = "delta_100ms_nojumpback.svg",
    )

    # 50ms + 100ms hist
    fig, axs = plt.subplots(1, 2, figsize=(7,3))
    fig.tight_layout(h_pad=2)

    # 50ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_21["msgs"]), float)
    y2 = ((y2) - mea_21_xor_dpsk_nojumpback_50ms.analyze.NOMINAL_S) * 1000
    axs[0].hist(y2, bins=mea_21_xor_dpsk_nojumpback_50ms.analyze.HIST_BINS, color='b')
    axs[0].set_title("a) 50 ms")
    axs[0].set_xlabel("ms", fontsize=8)
    axs[0].set_ylabel("frequency", fontsize=8)


    # 100ms
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_20["msgs"]), float)
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


    ipd = [list(ele["loraMsgId"] for ele in mea_24["msgs"])[900:1100], list(ele["gwTs"]["delta"] for ele in mea_24["msgs"])[900:1100]]
    plot_single_ipd(
        data = ipd,
        filename = "delta_2bit.svg",
    )

    # plot hist of all nbits
#    fig, axs = plt.subplots(2, 2, figsize=(7,3))
    fig = plt.figure()
    fig.tight_layout(h_pad=2)
    gs = GridSpec(2,2, figure=fig)
    ax1 = fig.add_subplot(gs[0,0])
    ax2 = fig.add_subplot(gs[0,1])
    ax3 = fig.add_subplot(gs[1,:])

    # 2bit
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_24["msgs"]), float)
    y2 = ((y2) - mea_24_xor_2bit.analyze.NOMINAL_S) * 1000
    ax1.hist(y2, bins=mea_24_xor_2bit.analyze.HIST_BINS, color='b')
    ax1.set_title("a) 2 bit")
    ax1.set_ylabel("frequency")

    # 4bit
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_25["msgs"]), float)
    y2 = ((y2) - mea_25_xor_4bit.analyze.NOMINAL_S) * 1000
    ax2.hist(y2, bins=mea_25_xor_4bit.analyze.HIST_BINS, color='b')
    ax2.set_title("b) 4 bit")

    # 8bit
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_22["msgs"]), float)
    y2 = ((y2) - mea_22_xor_8bit.analyze.NOMINAL_S) * 1000
    ax3.hist(y2, bins=mea_22_xor_8bit.analyze.HIST_BINS, color='b')
    ax3.set_title("c) 8 bit")
    ax3.set_xlabel("ms", fontsize=8)

    plt.savefig("hist_nbit.svg")
#    plt.show()
    plt.clf()
    plt.cla()
    plt.close()


    # 4bit with lfsr
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_27["msgs"]), float)
    y2 = ((y2) - mea_27_xor_4bit_lfsr_fix.analyze.NOMINAL_S) * 1000

    plot_single_hist(
        data=y2,
        bins=mea_27_xor_4bit_lfsr_fix.analyze.HIST_BINS,
        filename="hist_4bit_lfsr.svg"
    )

    # 4bit with lfsr and spreading
    # Show histogram
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_28["msgs"]), float)
    y2 = ((y2) - mea_28_xor_4bit_lfsr_ss.analyze.NOMINAL_S) * 1000

    plot_single_hist(
        data=y2,
        bins=mea_28_xor_4bit_lfsr_ss.analyze.HIST_BINS,
        filename="hist_4bit_ss.svg"
    )

    # Show despreaded histogram
    y2 = np.array(list(ele["gwTs"]["despreaded"] for ele in mea_28["msgs"]), float)
    y2 = ((y2) - mea_28_xor_4bit_lfsr_ss.analyze.NOMINAL_S) * 1000

    plot_single_hist(
        data=y2,
        bins=mea_28_xor_4bit_lfsr_ss.analyze.HIST_BINS,
        filename="hist_4bit_ss_despread.svg"
    )

    # Show ecc histogram
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_29["msgs"]), float)
    y2 = ((y2) - mea_29_xor_4bit_hamming_50ms.analyze.NOMINAL_S) * 1000

    plot_single_hist(
        data=y2,
        bins=mea_29_xor_4bit_hamming_50ms.analyze.HIST_BINS,
        filename="hist_4bit_ecc.svg"
    )

    # Feld temperature/vdd plot
    for msg in mea_30["msgs"]:
        msg["vdd_V"] = ((msg["payload"]["raw"] >> 16) & 0xffff)/1000
        msg["temp_C"] = ((msg["payload"]["raw"] & 0xffff) / 2**6 ) - 273.15

    max_msgs = int(mea_30["msgs"][-1]["loraMsgId"])
    msg_received = np.zeros((1, max_msgs+1), bool)

    for msg in mea_30["msgs"]:
        msg_received[0, int(msg["loraMsgId"])] = True

    plot_temp_vdd(
        list(ele["loraMsgId"] for ele in mea_30["msgs"]),
        np.array(list(ele["temp_C"] for ele in mea_30["msgs"]), float),
        np.array(list(ele["vdd_V"] for ele in mea_30["msgs"]), float),
        msg_received,
        filename = "feld_temp.svg",
        legend_loc='lower left',
        show = False
    )

    # Feld histogram
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_30["msgs"]), float)
    y2 = ((y2) - mea_30_xor_4bit_feld.analyze.NOMINAL_S) * 1000

    plot_single_hist(
        data=y2,
        bins=mea_30_xor_4bit_feld.analyze.HIST_BINS,
        filename="feld_hist.svg"
    )

    mea_31 = mea_31_xor_4bit_hochstand.analyze.analyze(mea_31_xor_4bit_hochstand.analyze.readMeasurements("mea_31_xor_4bit_hochstand/hochstand.json"), gw_eui="58A0CBFFFE802A21", gw_ts_name="gwTs")

    # Hochstand temperature/vdd plot
    for msg in mea_31["msgs"]:
        msg["vdd_V"] = ((msg["payload"]["raw"] >> 16) & 0xffff)/1000
        msg["temp_C"] = ((msg["payload"]["raw"] & 0xffff) / 2**6 ) - 273.15

    max_msgs = int(mea_31["msgs"][-1]["loraMsgId"])
    msg_received = np.zeros((1, max_msgs+1), bool)

    for msg in mea_31["msgs"]:
        msg_received[0, int(msg["loraMsgId"])] = True

    plot_temp_vdd(
        list(ele["loraMsgId"] for ele in mea_31["msgs"]),
        np.array(list(ele["temp_C"] for ele in mea_31["msgs"]), float),
        np.array(list(ele["vdd_V"] for ele in mea_31["msgs"]), float),
        msg_received,
        filename = "hochstand_temp.svg",
        legend_loc='lower left',
        show = False
    )

    # Hochstand histogram
    y2 = np.array(list(ele["gwTs"]["delta"] for ele in mea_31["msgs"]), float)
    y2 = ((y2) - mea_31_xor_4bit_hochstand.analyze.NOMINAL_S) * 1000

    plot_single_hist(
        data=y2,
        bins=mea_31_xor_4bit_hochstand.analyze.HIST_BINS,
        filename="hochstand_hist.svg"
    )

#    mea_31 = mea_31_xor_4bit_hochstand.analyze.analyze(mea_31_xor_4bit_hochstand.analyze.readMeasurements("mea_31_xor_4bit_hochstand/hochstand.json"), gw_eui="58A0CBFFFE802A21", gw_ts_name="time")

    # Jitter with us_timestamp
    ipd = [list(ele["loraMsgId"] for ele in mea_11["msgs"])[239:298], list(ele["modemTs"]["seconds"] for ele in mea_11["msgs"])[239:298]]

    plot_single_ipd(
        data = ipd,
        filename = "usts_jitter_abs.svg",
        ylabel="µs timestamp [s]"
    )

    ipd = [list(ele["loraMsgId"] for ele in mea_11["msgs"]), list(ele["modemTs"]["delta"] for ele in mea_11["msgs"])]
    plot_single_ipd(
        data = ipd,
        filename = "usts_jitter_ipd.svg"
    )

    y2 = np.array(list(ele["modemTs"]["delta"] for ele in mea_11["msgs"]), float)
    y2 = y2[y2>299] # Delete first, this is an outlier
    y2 = ((y2) - mea_11_jitter.analyze.NOMINAL_S) * 1000

    plot_single_hist(
        data=y2,
        bins=mea_11_jitter.analyze.HIST_BINS,
        filename="usts_jitter_hist.svg"
    )

    y2 = np.array(list(ele["modemTs"]["delta"] for ele in mea_13["msgs"]), float)
    y2 = ((y2) - mea_13_xor_dpsk_20ms.analyze.NOMINAL_S) * 1000
    y2 = y2[y2>-500]

    plot_single_hist(
        data=y2,
        bins=mea_13_xor_dpsk_20ms.analyze.HIST_BINS,
        filename="usts_20ms_hist.svg"
    )


if __name__ == "__main__":
    plot()
