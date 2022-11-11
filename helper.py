import base64
import struct
import datetime
import numpy as np
import copy

template_msg = {
    "numLost": None,

    "loraMsgId": None,

    "rssi": None,
    "snr": None,

    "modemTs": {"raw": None, "seconds": None, "delta": None},
    "gwTs": {"raw": None, "seconds": None, "delta": None},
    "nwTs": {"raw": None, "seconds": None, "delta": None},

    "payload": {"raw": None, "delta": None, "seconds": None, "secondsDelta": None},

    "calculation": {"watermark": None, "effWatermark": None},

    "extraction": {"symbol": None, "effWatermark": None},

    "symbolCorrect": None,
}

# Calculate watermark of sensordata
def calcWatermark(oldData, newData, key=0xa5a5, shift=13):
    reg = (oldData >> shift) ^ (newData >> shift) ^ key
    return reg

def calcEffWatermark(watermark, bits):
    return watermark & (2**bits -1)

def extractSymbol(deltaTimestamp, nominal, phaseDelta, tolerance, bits):
    delta = abs(deltaTimestamp-nominal)/phaseDelta
    tol = tolerance/phaseDelta
    for i in range(2**bits):
        if delta >= -tol and delta <= tol:
            return i
        elif delta < -tol:
            return None
        else:
            delta -= 1
    return None

def getPhase_nBits_spreading(deltaTimestamp, nominal, phaseDelta, tolerance, bits, prevSpreadingDelay, spreadingDelay):

    delta = abs(deltaTimestamp-nominal-spreadingDelay+prevSpreadingDelay)/phaseDelta

    tol = tolerance/phaseDelta

    print("deltaTimestamp: {0}, nominal: {1}, phaseDelta: {2}, tolerance: {3}, bits: {4}, delta: {5}, tol: {6}, prevSpreadingDelay: {7}, spreadingDelay: {8}".format(deltaTimestamp, nominal, phaseDelta, tolerance, bits, delta, tol, prevSpreadingDelay, spreadingDelay))

    for i in range(2**bits):

        if delta >= -tol and delta <= tol:
            print("delta: {0}, encoded bit is {1}!".format(delta, i))
            return i
        elif delta < -tol:
            print("delta: {0}, can't find encoded bit".format(delta))
            return None
        else:
            delta -= 1

    print("Can't find encoded bit")
    return None

def getPhase_nBits_ecc(deltaTimestamp, nominal, phaseDelta, tolerance, bits):

    symbol = getPhase_nBits(deltaTimestamp, nominal, phaseDelta, tolerance, bits*2)
    ecc_errors = 0

    if symbol == None:
        return [None, None]

    # Now perform error correction according to ham(8,4)
    # format = 0b (d3) (d2) (d1) (c2) (d0) (c1) (c0) (p)

    p = symbol & 0x1
    c = [
        symbol >> 1 & 0x1,
        symbol >> 2 & 0x1,
        symbol >> 4 & 0x1,
        ]
    d = [
        symbol >> 3 & 0x1,
        symbol >> 5 & 0x1,
        symbol >> 6 & 0x1,
        symbol >> 7 & 0x1,
        ]

    s = [
        c[0] ^ d[0] ^ d[1] ^ d[3],
        c[1] ^ d[0] ^ d[2] ^ d[3],
        c[2] ^ d[1] ^ d[2] ^ d[3],
        ]

    syndrome = s[2] << 2 | s[1] << 1 | s[0]

    corrected = 0
    bitCorrected = False

    if (syndrome != 0):
        corrected = symbol ^ ( 1 << syndrome )
        ecc_errors = 1
    else:
        corrected = symbol

    parity = corrected ^ (corrected >> 16)
    parity = parity ^ (parity >> 8)
    parity = parity ^ (parity >> 4)
    parity = parity ^ (parity >> 2)
    parity = parity ^ (parity >> 1)

    d = [
        corrected >> 3 & 0x1,
        corrected >> 5 & 0x1,
        corrected >> 6 & 0x1,
        corrected >> 7 & 0x1,
        ]

    data = d[3] << 3 | d[2] << 2 | d[1] << 1 | d[0]

    print("Syndrome = {0}, symbol = {1}, corrected = {2}, data = {3}".format(hex(syndrome), hex(symbol), hex(corrected), data))

    if p != (parity & 0x1):
        # Either double bit flip, or parity bit is wrong
        if (syndrome != 0):
            # Means double bit flip
            print("Double bit flip detected!")
            ecc_errors = 2
            return [ecc_errors, None]
        else:
            # parity bit flip
            ecc_errors = 1
            return [ecc_errors, data]
    else:
        return [ecc_errors, data]

def _conv_timestamp(s):
    # Convert timestamps from the format given by TTN to internal one
    # Example:
    # "2022-06-23T20:54:01.621829032Z" -> len() = 30
    # "2022-06-23T20:49:01.625Z"

    # datetime.strptime() can only work with fractionals
    # at a maximum of 6

    # Delete Z at end
    s = s[:-1]

    # Delete fractual seconds that are too long
    if (len(s) > 26):
        s = s[:26]

    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")

def calcUsDelta(ts, substractor):
    # Need to compensate for:
    # 1) Overflow
    # 2) 24h reset
    temp = ts - substractor

    if (temp < -501):
        temp += ((2**32)-1) / (1000 * 1000)
    elif (temp < 0 and temp > -501):
        # 24h overflow
        temp += (24*60*60) - (20 * ((2**32)-1) / (1000*1000))
    return temp

def readGw(element, gw_eui, onAirTime_s, msg):
    for gw in element["result"]["uplink_message"]["rx_metadata"]:
        if gw["gateway_ids"]["eui"] == gw_eui:

            msg["modemTs"]["raw"] = int(gw["timestamp"])
            msg["modemTs"]["seconds"] = calcUsDelta(msg["modemTs"]["raw"] / (1000 * 1000), onAirTime_s)

            msg["gwTs"]["raw"] = _conv_timestamp(gw["time"]).timestamp()
            msg["gwTs"]["seconds"] = msg["gwTs"]["raw"] - onAirTime_s

            try:
                msg["rssi"] = float(gw["rssi"])
                msg["snr"] = float(gw["snr"])
            except:
                pass

def calcIpd(element, msg, preMsg, tsName):
    # Check if a frame was lost
    msg["numLost"] = (msg["loraMsgId"] - preMsg["loraMsgId"])-1

    if (msg["numLost"] != 0 ):
        print("ID: {0}".format(msg["loraMsgId"]))
        print("\t{0} frame(s) after ID {1} lost".format(msg["numLost"], preMsg["loraMsgId"]))
        print("\tGW   TS: {0:.3f} s".format(msg[tsName]["seconds"]))
        print("\tPAYLOAD: {0}".format(msg["payload"]["raw"]))

    else:
        msg["modemTs"]["delta"] = calcUsDelta(msg["modemTs"]["seconds"], preMsg["modemTs"]["seconds"])
        msg["gwTs"]["delta"] = msg["gwTs"]["seconds"] - preMsg["gwTs"]["seconds"]
        msg["nwTs"]["delta"] = msg["nwTs"]["seconds"] - preMsg["nwTs"]["seconds"]
        msg["payload"]["delta"] = msg["payload"]["seconds"] - preMsg["payload"]["seconds"]

def readMessages(data, nominal, tolerance, phaseDelta, bits, printMatches, watermarkShift=13, gw_eui="58A0CBFFFE802A21", gw_ts_name="time"):
    msgs = []
    numMsgsLost = 0
    symbols = {
        "possible": 0,
        "errors": 0
        }

    # Go through messages and extract info
    for element in data:
        msg = copy.deepcopy(template_msg)

        msg["loraMsgId"] = element["result"]["uplink_message"]["f_cnt"]

        onAirTime_s = float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        readGw(element, gw_eui, onAirTime_s, msg)

        msg["nwTs"]["raw"] = _conv_timestamp(element["result"]["received_at"]).timestamp()
        msg["nwTs"]["seconds"] = msg["nwTs"]["raw"] - onAirTime_s

        a = element["result"]["uplink_message"]["frm_payload"]
        a = int(base64.b64decode(a).hex(),16) # Convert base64 to hexstring
        a = int(struct.pack("<Q", a).hex(), 16) # Convert to little endian
        msg["payload"]["raw"] = int(a / 2**32)  # Pad to 32 bit and use [ms]
        msg["payload"]["seconds"] = msg["payload"]["raw"] / 1000

        if not len(msgs) == 0:
            preMsg = msgs[-1]
            calcIpd(element, msg, preMsg, gw_ts_name)
            numMsgsLost += msg["numLost"]

            # To calculate the watermark and to extract the symbol,
            # at least 2 subsequent messages are needed
            if (msg["numLost"] == 0):
                msg["calculation"]["watermark"] = calcWatermark(preMsg["payload"]["raw"], msg["payload"]["raw"])
                msg["calculation"]["effWatermark"] = calcEffWatermark(msg["calculation"]["watermark"], bits)
                msg["extraction"]["symbol"] = extractSymbol(msg[gw_ts_name]["delta"], nominal, phaseDelta, tolerance, bits)

                if (bits == 1):
                    # Due to DPSK modulation, for 1 bit another subsequent message is needed
                    if ( preMsg["numLost"] == 0 ):
                        if (preMsg["extraction"]["symbol"] != None):
                            msg["extraction"]["effWatermark"] = preMsg["extraction"]["symbol"] ^ msg["calculation"]["effWatermark"]
                        symbols["possible"] += 1
                    else:
                        msgs.append(msg)
                        continue

                else:
                    symbols["possible"] += 1
                    msg["extraction"]["effWatermark"] = msg["extraction"]["symbol"]

                msg["symbolCorrect"] = (msg["extraction"]["effWatermark"] == msg["calculation"]["effWatermark"])

                if (not msg["symbolCorrect"]):
                    print("ID: {0}".format(msg["loraMsgId"]))
                    print("\tGW   TS: {0:.3f} s".format(msg[gw_ts_name]["seconds"]))
                    print("\tPAYLOAD: {0}".format(msg["payload"]["raw"]))
                    print("\tCalculated Watermark: 0x{0:x}, effWatermark: 0x{1:x}".format(msg["calculation"]["watermark"], msg["calculation"]["effWatermark"]))
                    print("\tExtracted Symbol: {0}, effWatermark: {1}".format(msg["extraction"]["symbol"], msg["extraction"]["effWatermark"]))
                    print("\teffWatermark does not match!")
                    symbols["errors"] += 1
                elif (printMatches):
                    print("ID: {0}".format(msg["loraMsgId"]))
                    print("\tGW   TS: {0:.3f} s".format(msg[gw_ts_name]["seconds"]))
                    print("\tPAYLOAD: {0}".format(msg["payload"]["raw"]))
                    print("\tCalculated Watermark: 0x{0:x}, effWatermark: 0x{1:x}".format(msg["calculation"]["watermark"], msg["calculation"]["effWatermark"]))
                    print("\tExtracted Symbol: 0x{0:x}, effWatermark: 0x{1:x}".format(msg["extraction"]["symbol"], msg["extraction"]["effWatermark"]))
                    print("\teffWatermark match!")

        else:
            # First message -> Handle like a lost message
            msg["numLost"] = 1
            print("ID: {0}".format(msg["loraMsgId"]))
            print("\tFirst message")
            print("\tGW   TS: {0:.3f} s".format(msg[gw_ts_name]["seconds"]))
            print("\tPAYLOAD: {0}".format(msg["payload"]["raw"]))

        msgs.append(msg)

    return {"msgs": msgs, "numMsgsLost": numMsgsLost, "numSymolsPossible": symbols["possible"], "numSymbolErrors": symbols["errors"]}

def readMessages_ustimestamp(data, nominal, tolerance, printMatches):

    msgs = []
    numMsgsLost = 0
    phases = {
        "decoded": 0,
        "errors": 0
        }

    # Go through messages and extract info
    for element in data:
        msg = {
            "previous_lost": False,
            "lora_msg_id": None,
            "gw_timestamp": None,
            "gw_timestamp_delta": None,
            "nw_timestamp": None,
            "nw_timestamp_delta": None,
            "mcu_timestamp": None,
            "mcu_timestamp_s": None,
            "mcu_timestamp_delta": None,
            "mcu_timestamp_delta_s": None,
            "calculation": {"watermark": None, "phase": None},
            "extraction": {"phase": None},
            "phase_correct": None,
            "snr": None,
            "rssi": None,
        }

        msg["lora_msg_id"] = element["result"]["uplink_message"]["f_cnt"]

#        for gw in element["result"]["uplink_message"]["rx_metadata"]:
#            if gw["gateway_ids"]["eui"] == "58A0CBFFFE802A21":
#                a = _conv_timestamp(gw["time"])

#        msg["gw_timestamp_not_compensated"] = a.timestamp()
#        msg["gw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

#        a = _conv_timestamp(element["result"]["received_at"])
#        msg["nw_timestamp_not_compensated"] = a.timestamp()
#        msg["nw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        for gw in element["result"]["uplink_message"]["rx_metadata"]:
            if gw["gateway_ids"]["eui"] == "58A0CBFFFE802A21":
                a_us = int(gw["timestamp"])
                try:
                    msg["rssi"] = float(gw["rssi"])
                    msg["snr"] = float(gw["snr"])
                except:
                    pass

        msg["gw_timestamp_not_compensated"] = a_us / (1000 * 1000)
        msg["gw_timestamp"] = a_us / (1000 * 1000) - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        a = _conv_timestamp(element["result"]["received_at"])
        msg["nw_timestamp_not_compensated"] = a.timestamp()
        msg["nw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        a = element["result"]["uplink_message"]["frm_payload"]
        a = int(base64.b64decode(a).hex(),16) # Convert base64 to hexstring
        a = int(struct.pack("<Q", a).hex(), 16) # Convert to little endian
        msg["mcu_timestamp"] = int( a / 2**32)  # Pad to 32 bit and use [ms]
        msg["mcu_timestamp_s"] = msg["mcu_timestamp"] / 1000

        # Get previous message if possible
        if not len(msgs) == 0:
            preMsg = msgs[-1]
            # Check if a frame was lost
            if (not ((msg["lora_msg_id"] - preMsg["lora_msg_id"]) == 1) ):
                print("ID: {0}".format(msg["lora_msg_id"]))
                print("\t{0} frame(s) after ID {1} lost".format((msg["lora_msg_id"] - preMsg["lora_msg_id"])-1, preMsg["lora_msg_id"]))
                print("\tGW  TS: {0:.3f} s".format(msg["gw_timestamp"]))
                print("\tMCU TS: {0:.3f} s".format(msg["mcu_timestamp"]/1000))
                msg["previous_lost"] = True
                numMsgsLost += (msg["lora_msg_id"] - preMsg["lora_msg_id"])-1

            elif (preMsg["previous_lost"] == True):
                # Calc time deltas
                msg["gw_timestamp_delta"] = msg["gw_timestamp"] - preMsg["gw_timestamp"]
#                if   (msg["gw_timestamp_delta"] < 0 and msg["gw_timestamp_delta"] > -600):
#                    msg["gw_timestamp_delta"] += 500.65408
#                elif (msg["gw_timestamp_delta"] < -600):
#                    msg["gw_timestamp_delta"] += (2**32) / (1000 * 1000)
                if (msg["gw_timestamp_delta"] < -501):
                    msg["gw_timestamp_delta"] += ((2**32)-1) / (1000 * 1000)

                elif (msg["gw_timestamp_delta"] < 0 and msg["gw_timestamp_delta"] > -501):
                    msg["gw_timestamp_delta"] += (((24*60*60*1000*1000)%((2**32)-1)) - ((20*((2**32)-1)))) / (1000*1000)

                msg["nw_timestamp_delta"] = msg["nw_timestamp"] - preMsg["nw_timestamp"]
                msg["mcu_timestamp_delta"] = msg["mcu_timestamp"] - preMsg["mcu_timestamp"]
                msg["mcu_timestamp_delta_s"] = msg["mcu_timestamp_delta"] / 1000

                # Calc watermark
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"])

                # Get extracted phase
                msg["extraction"]["phase"] = getPhase(msg["gw_timestamp_delta"], nominal, tolerance)

                print("ID: {0}".format(msg["lora_msg_id"]))
                print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                print("\tPrevious Lost, cannot verify phase")
            else:
                # Calc time deltas
                msg["gw_timestamp_delta"] = msg["gw_timestamp"] - preMsg["gw_timestamp"]
                if (msg["gw_timestamp_delta"] < -501):
                    msg["gw_timestamp_delta"] += ((2**32)-1) / (1000 * 1000)

                elif (msg["gw_timestamp_delta"] < 0 and msg["gw_timestamp_delta"] > -501):
                    msg["gw_timestamp_delta"] += (((24*60*60*1000*1000)) - ((20*((2**32)-1)))) / (1000*1000)

                msg["nw_timestamp_delta"] = msg["nw_timestamp"] - preMsg["nw_timestamp"]
                msg["mcu_timestamp_delta"] = msg["mcu_timestamp"] - preMsg["mcu_timestamp"]
                msg["mcu_timestamp_delta_s"] = msg["mcu_timestamp_delta"] / 1000

                # Calc watermark and phase
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"])
                msg["calculation"]["phase"] = calcPhase(preMsg["extraction"]["phase"], msg["calculation"]["watermark"])
                msg["extraction"]["phase"] = getPhase(msg["gw_timestamp_delta"], nominal, tolerance)

                phases["decoded"] += 1

                if not (msg["calculation"]["phase"] == msg["extraction"]["phase"]):
                    msg["phase_correct"] = False
                    phases["errors"] += 1
                    print("ID: {0}".format(msg["lora_msg_id"]))
                    print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                    print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                    print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                    print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                    print("\tCalculated and Extracted phases do not match")
                else:
                    msg["phase_correct"] = True
                    if (printMatches == True):
                        print("ID: {0}".format(msg["lora_msg_id"]))
                        print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                        print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                        print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                        print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                        print("\tCalculated and Extracted phases match")

        else:
            # First message
            msg["calculation"]["phase"] = 0
            msg["extraction"]["phase"] = 0
            print("ID: {0}".format(msg["lora_msg_id"]))
            print("\tFirst message")
            print("\tGW  TS: {0:.3f} s".format(msg["gw_timestamp"]))
            print("\tMCU TS: {0:.3f} s".format(msg["mcu_timestamp"]/1000))

        msgs.append(msg)

    return {"msgs": msgs, "numMsgsLost": numMsgsLost, "numPhasesDecoded": phases["decoded"], "numPhasesErrors": phases["errors"]}


def readMessages_nBit(data, nominal, tolerance, phaseDelta, bits, printMatches, watermarkShift=13, gw_eui="58A0CBFFFE802A21", gw_ts_name="time"):

    msgs = []
    numMsgsLost = 0
    phases = {
        "decoded": 0,
        "errors": 0
        }

    # Go through messages and extract info
    for element in data:
        msg = {
            "previous_lost": False,
            "lora_msg_id": None,
            "gw_timestamp": None,
            "gw_timestamp_delta": None,
            "nw_timestamp": None,
            "nw_timestamp_delta": None,
            "mcu_timestamp": None,
            "mcu_timestamp_s": None,
            "mcu_timestamp_delta": None,
            "mcu_timestamp_delta_s": None,
            "calculation": {"watermark": None, "phase": None},
            "extraction": {"phase": None},
            "phase_correct": None,
            "snr": None,
            "rssi": None,
        }

        msg["lora_msg_id"] = element["result"]["uplink_message"]["f_cnt"]

        a = None

        for gw in element["result"]["uplink_message"]["rx_metadata"]:
            if gw["gateway_ids"]["eui"] == gw_eui:
                a = _conv_timestamp(gw[gw_ts_name])
                try:
                    msg["rssi"] = float(gw["rssi"])
                    msg["snr"] = float(gw["snr"])
                except:
                    pass
        if a == None:
            print("Gateway not found!")
            continue

        msg["gw_timestamp_not_compensated"] = a.timestamp()
        msg["gw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        a = _conv_timestamp(element["result"]["received_at"])
        msg["nw_timestamp_not_compensated"] = a.timestamp()
        msg["nw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        a = element["result"]["uplink_message"]["frm_payload"]
        a = int(base64.b64decode(a).hex(),16) # Convert base64 to hexstring
        a = int(struct.pack("<Q", a).hex(), 16) # Convert to little endian
        msg["mcu_timestamp"] = int( a / 2**32)  # Pad to 32 bit and use [ms]
        msg["mcu_timestamp_s"] = msg["mcu_timestamp"] / 1000

        # Get previous message if possible
        if not len(msgs) == 0:
            preMsg = msgs[-1]
            # Check if a frame was lost
            if (not ((msg["lora_msg_id"] - preMsg["lora_msg_id"]) == 1) ):
                print("ID: {0}".format(msg["lora_msg_id"]))
                print("\t{0} frame(s) after ID {1} lost".format((msg["lora_msg_id"] - preMsg["lora_msg_id"])-1, preMsg["lora_msg_id"]))
                print("\tGW  TS: {0:.3f} s".format(msg["gw_timestamp"]))
                print("\tMCU TS: {0:.3f} s".format(msg["mcu_timestamp"]/1000))
                msg["previous_lost"] = True
                numMsgsLost += (msg["lora_msg_id"] - preMsg["lora_msg_id"])-1

            elif (preMsg["previous_lost"] == True):
                # Calc time deltas
                msg["gw_timestamp_delta"] = msg["gw_timestamp"] - preMsg["gw_timestamp"]
                msg["nw_timestamp_delta"] = msg["nw_timestamp"] - preMsg["nw_timestamp"]
                msg["mcu_timestamp_delta"] = msg["mcu_timestamp"] - preMsg["mcu_timestamp"]
                msg["mcu_timestamp_delta_s"] = msg["mcu_timestamp_delta"] / 1000

                # Calc watermark
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"], shift=watermarkShift)

                # Get extracted phase
                msg["extraction"]["phase"] = getPhase_nBits(msg["gw_timestamp_delta"], nominal, phaseDelta, tolerance, bits)

                print("ID: {0}".format(msg["lora_msg_id"]))
                print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                print("\tPrevious Lost, cannot verify phase")
            else:
                # Calc time deltas
                msg["gw_timestamp_delta"] = msg["gw_timestamp"] - preMsg["gw_timestamp"]
                msg["nw_timestamp_delta"] = msg["nw_timestamp"] - preMsg["nw_timestamp"]
                msg["mcu_timestamp_delta"] = msg["mcu_timestamp"] - preMsg["mcu_timestamp"]
                msg["mcu_timestamp_delta_s"] = msg["mcu_timestamp_delta"] / 1000

                # Calc watermark and phase
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"], shift=watermarkShift)
                msg["calculation"]["phase"] = calcPhase_nBits(msg["calculation"]["watermark"], bits)
                msg["extraction"]["phase"] = getPhase_nBits(msg["gw_timestamp_delta"], nominal, phaseDelta, tolerance, bits)

                phases["decoded"] += 1

                if not (msg["calculation"]["phase"] == msg["extraction"]["phase"]):
                    msg["phase_correct"] = False
                    phases["errors"] += 1
                    print("ID: {0}".format(msg["lora_msg_id"]))
                    print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                    print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                    print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                    print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                    print("\tCalculated and Extracted phases do not match")
                else:
                    msg["phase_correct"] = True
                    if (printMatches == True):
                        print("ID: {0}".format(msg["lora_msg_id"]))
                        print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                        print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                        print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                        print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                        print("\tCalculated and Extracted phases match")

        else:
            # First message
            msg["calculation"]["phase"] = 0
            msg["extraction"]["phase"] = 0
            print("ID: {0}".format(msg["lora_msg_id"]))
            print("\tFirst message")
            print("\tGW  TS: {0:.3f} s".format(msg["gw_timestamp"]))
            print("\tMCU TS: {0:.3f} s".format(msg["mcu_timestamp"]/1000))

        msgs.append(msg)

    return {"msgs": msgs, "numMsgsLost": numMsgsLost, "numPhasesDecoded": phases["decoded"], "numPhasesErrors": phases["errors"]}

def xorshift(lfsr):
    # Hattip to: http://www.retroprogramming.com/2017/07/xorshift-pseudorandom-numbers-in-z80.html
    lfsr ^= ( lfsr << 7 ) % 2**16
    lfsr ^= ( lfsr >> 9 ) % 2**16
    lfsr ^= ( lfsr << 8 ) % 2**16
    return lfsr

def readMessages_nBit_ss(data, nominal, tolerance, phaseDelta, bits, printMatches, spreadingSeed, watermarkShift=13):

    msgs = []
    numMsgsLost = 0
    phases = {
        "decoded": 0,
        "errors": 0
        }

    spreadingSeq = spreadingSeed
    delayWindow_ms = 2**bits * phaseDelta * 1000 # From lora_app.c

    # Go through messages and extract info
    for element in data:

        msg = {
            "previous_lost": False,
            "lora_msg_id": None,
            "gw_timestamp": None,
            "gw_timestamp_delta": None,
            "gw_timestamp_delta_despread": None,
            "nw_timestamp": None,
            "nw_timestamp_delta": None,
            "mcu_timestamp": None,
            "mcu_timestamp_s": None,
            "mcu_timestamp_delta": None,
            "mcu_timestamp_delta_s": None,
            "spreading_delay": None,
            "calculation": {"watermark": None, "phase": None},
            "extraction": {"phase": None},
            "phase_correct": None,
            "snr": None,
            "rssi": None,
        }

        msg["lora_msg_id"] = element["result"]["uplink_message"]["f_cnt"]

        spreadingSeq = spreadingSeed
        for i in range(msg["lora_msg_id"]):
            # This is a very very dirty workaround....
            spreadingSeq = xorshift(spreadingSeq)

        spreadingDelay_ms = delayWindow_ms + ((spreadingSeq * 2*delayWindow_ms) / 2**16)
        spreadingDelay_s = spreadingDelay_ms / 1000
        msg["spreading_delay"] = spreadingDelay_s

        for gw in element["result"]["uplink_message"]["rx_metadata"]:
            if gw["gateway_ids"]["eui"] == "58A0CBFFFE802A21":
                a = _conv_timestamp(gw["time"])
                try:
                    msg["rssi"] = float(gw["rssi"])
                    msg["snr"] = float(gw["snr"])
                except:
                    pass

        msg["gw_timestamp_not_compensated"] = a.timestamp()
        msg["gw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        a = _conv_timestamp(element["result"]["received_at"])
        msg["nw_timestamp_not_compensated"] = a.timestamp()
        msg["nw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        a = element["result"]["uplink_message"]["frm_payload"]
        a = int(base64.b64decode(a).hex(),16) # Convert base64 to hexstring
        a = int(struct.pack("<Q", a).hex(), 16) # Convert to little endian
        msg["mcu_timestamp"] = int( a / 2**32)  # Pad to 32 bit and use [ms]
        msg["mcu_timestamp_s"] = msg["mcu_timestamp"] / 1000

        # Get previous message if possible
        if not len(msgs) == 0:
            preMsg = msgs[-1]
            # Check if a frame was lost
            if (not ((msg["lora_msg_id"] - preMsg["lora_msg_id"]) == 1) ):
                print("ID: {0}".format(msg["lora_msg_id"]))
                print("\t{0} frame(s) after ID {1} lost".format((msg["lora_msg_id"] - preMsg["lora_msg_id"])-1, preMsg["lora_msg_id"]))
                print("\tGW  TS: {0:.3f} s".format(msg["gw_timestamp"]))
                print("\tMCU TS: {0:.3f} s".format(msg["mcu_timestamp"]/1000))
                msg["previous_lost"] = True
                numMsgsLost += (msg["lora_msg_id"] - preMsg["lora_msg_id"])-1

            elif (preMsg["previous_lost"] == True):
                # Calc time deltas
                msg["gw_timestamp_delta"] = msg["gw_timestamp"] - preMsg["gw_timestamp"]
                msg["nw_timestamp_delta"] = msg["nw_timestamp"] - preMsg["nw_timestamp"]
                msg["mcu_timestamp_delta"] = msg["mcu_timestamp"] - preMsg["mcu_timestamp"]
                msg["mcu_timestamp_delta_s"] = msg["mcu_timestamp_delta"] / 1000

                # Calc watermark
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"], shift=watermarkShift)

                # Calc despreaded delta
                msg["gw_timestamp_delta_despread"] = msg["gw_timestamp_delta"] - msg["spreading_delay"] + preMsg["spreading_delay"]

                # Get extracted phase
                msg["extraction"]["phase"] = getPhase_nBits_spreading(msg["gw_timestamp_delta"], nominal, phaseDelta, tolerance, bits, preMsg["spreading_delay"], msg["spreading_delay"])

                print("ID: {0}".format(msg["lora_msg_id"]))
                print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                print("\tPrevious Lost, cannot verify phase")
            else:
                # Calc time deltas
                msg["gw_timestamp_delta"] = msg["gw_timestamp"] - preMsg["gw_timestamp"]
                msg["nw_timestamp_delta"] = msg["nw_timestamp"] - preMsg["nw_timestamp"]
                msg["mcu_timestamp_delta"] = msg["mcu_timestamp"] - preMsg["mcu_timestamp"]
                msg["mcu_timestamp_delta_s"] = msg["mcu_timestamp_delta"] / 1000

                # Calc watermark and phase
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"], shift=watermarkShift)
                msg["calculation"]["phase"] = calcPhase_nBits(msg["calculation"]["watermark"], bits)
                msg["extraction"]["phase"] = getPhase_nBits_spreading(msg["gw_timestamp_delta"], nominal, phaseDelta, tolerance, bits, preMsg["spreading_delay"], msg["spreading_delay"])
                # Calc despreaded delta
                msg["gw_timestamp_delta_despread"] = msg["gw_timestamp_delta"] - msg["spreading_delay"] + preMsg["spreading_delay"]

                phases["decoded"] += 1

                if not (msg["calculation"]["phase"] == msg["extraction"]["phase"]):
                    msg["phase_correct"] = False
                    phases["errors"] += 1
                    print("ID: {0}".format(msg["lora_msg_id"]))
                    print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                    print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                    print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                    print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                    print("\tCalculated and Extracted phases do not match")
                else:
                    msg["phase_correct"] = True
                    if (printMatches == True):
                        print("ID: {0}".format(msg["lora_msg_id"]))
                        print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                        print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                        print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                        print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                        print("\tCalculated and Extracted phases match")

        else:
            # First message
            msg["calculation"]["phase"] = 0
            msg["extraction"]["phase"] = 0
            print("ID: {0}".format(msg["lora_msg_id"]))
            print("\tFirst message")
            print("\tGW  TS: {0:.3f} s".format(msg["gw_timestamp"]))
            print("\tMCU TS: {0:.3f} s".format(msg["mcu_timestamp"]/1000))

        msgs.append(msg)

    return {"msgs": msgs, "numMsgsLost": numMsgsLost, "numPhasesDecoded": phases["decoded"], "numPhasesErrors": phases["errors"]}

def readMessages_nBit_ecc(data, nominal, tolerance, phaseDelta, bits, printMatches, watermarkShift=13):

    msgs = []
    numMsgsLost = 0
    phases = {
        "decoded": 0,
        "errors": 0
        }
    ecc = {
        "dualBit": 0,   # Invalid
        "singleBit": 0, # Corrected
        "noErr": 0
        }

    # Go through messages and extract info
    for element in data:
        msg = {
            "previous_lost": False,
            "lora_msg_id": None,
            "gw_timestamp": None,
            "gw_timestamp_delta": None,
            "nw_timestamp": None,
            "nw_timestamp_delta": None,
            "mcu_timestamp": None,
            "mcu_timestamp_s": None,
            "mcu_timestamp_delta": None,
            "mcu_timestamp_delta_s": None,
            "calculation": {"watermark": None, "phase": None},
            "extraction": {"bit_errors": None, "phase": None},
            "phase_correct": None,
            "snr": None,
            "rssi": None,
        }

        msg["lora_msg_id"] = element["result"]["uplink_message"]["f_cnt"]

        for gw in element["result"]["uplink_message"]["rx_metadata"]:
            if gw["gateway_ids"]["eui"] == "58A0CBFFFE802A21":
                a = _conv_timestamp(gw["time"])
                try:
                    msg["rssi"] = float(gw["rssi"])
                    msg["snr"] = float(gw["snr"])
                except:
                    pass

        msg["gw_timestamp_not_compensated"] = a.timestamp()
        msg["gw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        a = _conv_timestamp(element["result"]["received_at"])
        msg["nw_timestamp_not_compensated"] = a.timestamp()
        msg["nw_timestamp"] = a.timestamp() - float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        a = element["result"]["uplink_message"]["frm_payload"]
        a = int(base64.b64decode(a).hex(),16) # Convert base64 to hexstring
        a = int(struct.pack("<Q", a).hex(), 16) # Convert to little endian
        msg["mcu_timestamp"] = int( a / 2**32)  # Pad to 32 bit and use [ms]
        msg["mcu_timestamp_s"] = msg["mcu_timestamp"] / 1000

        # Get previous message if possible
        if not len(msgs) == 0:
            preMsg = msgs[-1]
            # Check if a frame was lost
            if (not ((msg["lora_msg_id"] - preMsg["lora_msg_id"]) == 1) ):
                print("ID: {0}".format(msg["lora_msg_id"]))
                print("\t{0} frame(s) after ID {1} lost".format((msg["lora_msg_id"] - preMsg["lora_msg_id"])-1, preMsg["lora_msg_id"]))
                print("\tGW  TS: {0:.3f} s".format(msg["gw_timestamp"]))
                print("\tMCU TS: {0:.3f} s".format(msg["mcu_timestamp"]/1000))
                msg["previous_lost"] = True
                numMsgsLost += (msg["lora_msg_id"] - preMsg["lora_msg_id"])-1

            elif (preMsg["previous_lost"] == True):
                # Calc time deltas
                msg["gw_timestamp_delta"] = msg["gw_timestamp"] - preMsg["gw_timestamp"]
                msg["nw_timestamp_delta"] = msg["nw_timestamp"] - preMsg["nw_timestamp"]
                msg["mcu_timestamp_delta"] = msg["mcu_timestamp"] - preMsg["mcu_timestamp"]
                msg["mcu_timestamp_delta_s"] = msg["mcu_timestamp_delta"] / 1000

                # Calc watermark
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"], shift=watermarkShift)

                # Get extracted phase
                msg["extraction"]["bit_errors"], msg["extraction"]["phase"] = getPhase_nBits_ecc(msg["gw_timestamp_delta"], nominal, phaseDelta, tolerance, bits)

                if (msg["extraction"]["bit_errors"] == 0):
                    ecc["noErr"] += 1
                elif (msg["extraction"]["bit_errors"] == 1):
                    ecc["singleBit"] += 1
                elif (msg["extraction"]["bit_errors"] == 2):
                    ecc["dualBit"] += 1

                print("ID: {0}".format(msg["lora_msg_id"]))
                print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                print("\tPrevious Lost, cannot verify phase")
            else:
                # Calc time deltas
                msg["gw_timestamp_delta"] = msg["gw_timestamp"] - preMsg["gw_timestamp"]
                msg["nw_timestamp_delta"] = msg["nw_timestamp"] - preMsg["nw_timestamp"]
                msg["mcu_timestamp_delta"] = msg["mcu_timestamp"] - preMsg["mcu_timestamp"]
                msg["mcu_timestamp_delta_s"] = msg["mcu_timestamp_delta"] / 1000

                # Calc watermark and phase
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"], shift=watermarkShift)
                msg["calculation"]["phase"] = calcPhase_nBits(msg["calculation"]["watermark"], bits)
                msg["extraction"]["bit_errors"], msg["extraction"]["phase"] = getPhase_nBits_ecc(msg["gw_timestamp_delta"], nominal, phaseDelta, tolerance, bits)

                phases["decoded"] += 1

                if (msg["extraction"]["bit_errors"] == 0):
                    ecc["noErr"] += 1
                elif (msg["extraction"]["bit_errors"] == 1):
                    ecc["singleBit"] += 1
                elif (msg["extraction"]["bit_errors"] == 2):
                    ecc["dualBit"] += 1

                if not (msg["calculation"]["phase"] == msg["extraction"]["phase"]):
                    msg["phase_correct"] = False
                    phases["errors"] += 1
                    print("ID: {0}".format(msg["lora_msg_id"]))
                    print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                    print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                    print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                    print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                    print("\tCalculated and Extracted phases do not match")
                else:
                    msg["phase_correct"] = True
                    if (printMatches == True):
                        print("ID: {0}".format(msg["lora_msg_id"]))
                        print("\tGW  TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["gw_timestamp"], preMsg["gw_timestamp"], msg["gw_timestamp_delta"]*1000))
                        print("\tMCU TS: {0:.3f} s (pre: {1:.3f} s), delta: {2:.3f} ms".format(msg["mcu_timestamp"]/1000, preMsg["mcu_timestamp"]/1000, msg["mcu_timestamp_delta"]))
                        print("\tCalculated Watermark: 0x{0:x}, Phase: {1}".format(msg["calculation"]["watermark"], msg["calculation"]["phase"]))
                        print("\tExtracted Phase: {0}".format(msg["extraction"]["phase"]))
                        print("\tCalculated and Extracted phases match")

        else:
            # First message
            msg["calculation"]["phase"] = 0
            msg["extraction"]["phase"] = 0
            print("ID: {0}".format(msg["lora_msg_id"]))
            print("\tFirst message")
            print("\tGW  TS: {0:.3f} s".format(msg["gw_timestamp"]))
            print("\tMCU TS: {0:.3f} s".format(msg["mcu_timestamp"]/1000))

        msgs.append(msg)

    return {"msgs": msgs, "numMsgsLost": numMsgsLost, "numPhasesDecoded": phases["decoded"], "numPhasesErrors": phases["errors"], "ecc":ecc}
