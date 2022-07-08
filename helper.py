import base64
import struct
import datetime
import numpy as np

# Calculate watermark of sensordata
def calcWatermark(oldData, newData, key=0xa5a5):
    reg = (oldData >> 13) ^ (newData >> 13) ^ key
    return reg

# Calculate phase of sensordata
def calcPhase(oldPhase, newWatermark):
    return (oldPhase ^ (newWatermark & 0x1)) & 0x1

def calcPhase_nBits(watermark, bits):
    return watermark & (2**bits -1)

# Extract phase of gw timestamps
def getPhase(deltaTimestamp, nominal, tolerance):
    if deltaTimestamp < (nominal-tolerance) or deltaTimestamp > (nominal+tolerance):
        return 1
    else:
        return 0

def getPhase_nBits(deltaTimestamp, nominal, phaseDelta, tolerance, bits):

    delta = abs(deltaTimestamp-nominal)/phaseDelta

    tol = tolerance/phaseDelta

    print("deltaTimestamp: {0}, nominal: {1}, phaseDelta: {2}, tolerance: {3}, bits: {4}, delta: {5}, tol: {6}".format(deltaTimestamp, nominal, phaseDelta, tolerance, bits, delta, tol))

    for i in range(2**bits -1):

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

def readMessages(data, nominal, tolerance, printMatches):

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
        }

        msg["lora_msg_id"] = element["result"]["uplink_message"]["f_cnt"]

        for gw in element["result"]["uplink_message"]["rx_metadata"]:
            if gw["gateway_ids"]["eui"] == "58A0CBFFFE802A21":
                a = _conv_timestamp(gw["time"])

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

def readMessages_nBit(data, nominal, tolerance, phaseDelta, bits, printMatches):

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
        }

        msg["lora_msg_id"] = element["result"]["uplink_message"]["f_cnt"]

        for gw in element["result"]["uplink_message"]["rx_metadata"]:
            if gw["gateway_ids"]["eui"] == "58A0CBFFFE802A21":
                a = _conv_timestamp(gw["time"])

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
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"])

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
                msg["calculation"]["watermark"] = calcWatermark(preMsg["mcu_timestamp"], msg["mcu_timestamp"])
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
