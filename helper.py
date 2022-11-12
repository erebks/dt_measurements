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

    "modemTs": {"raw": None, "seconds": None, "despreaded": None, "delta": None},
    "gwTs": {"raw": None, "seconds": None, "despreaded": None, "delta": None},
    "nwTs": {"raw": None, "seconds": None, "despreaded": None, "delta": None},

    "payload": {"raw": None, "delta": None, "seconds": None, "secondsDelta": None},

    "calculation": {"watermark": None, "effWatermark": None},

    "extraction": {"symbol": None, "effWatermark": None, "eccErrors": None},

    "spreading": {"seqence": None, "delay": None},

    "symbolCorrect": None,
}

# Calculate watermark of sensordata
def calcWatermark(oldData, newData, key=0xa5a5, shift=13):
    reg = (oldData >> shift) ^ (newData >> shift) ^ key
    return reg

def calcEffWatermark(watermark, bits):
    return watermark & (2**bits -1)

def _extractSymbol_onebit(deltaTimestamp, nominal, phaseDelta, tolerance):
    delta = abs(deltaTimestamp-nominal)/phaseDelta
    tol = tolerance/phaseDelta

    if delta >= -tol and delta <= tol:
        return 0
    else:
        return 1

def extractSymbol(deltaTimestamp, nominal, phaseDelta, tolerance, bits):
    if bits == 1:
        return _extractSymbol_onebit(deltaTimestamp, nominal, phaseDelta, tolerance)

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

def extractSymbol_ss(deltaTimestamp, nominal, phaseDelta, tolerance, bits, spreadingDelay, prevSpreadingDelay):
    deltaDespread = deltaTimestamp - spreadingDelay + prevSpreadingDelay

    delta = abs(deltaDespread-nominal)/phaseDelta
    tol = tolerance/phaseDelta

    for i in range(2**bits):
        if delta >= -tol and delta <= tol:
            return [i, deltaDespread]
        elif delta < -tol:
            return [None, deltaDespread]
        else:
            delta -= 1

def extractSymbol_ecc(deltaTimestamp, nominal, phaseDelta, tolerance, bits):

    symbol = extractSymbol(deltaTimestamp, nominal, phaseDelta, tolerance, bits*2)
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

    if p != (parity & 0x1):
        # Either double bit flip, or parity bit is wrong
        if (syndrome != 0):
            # Means double bit flip
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
            return True
    return False

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

def getSpreadingParam(msgId, spreadingSeed, delayWindow_ms):
    spreadingSeq = spreadingSeed
    for i in range(msgId):
        spreadingSeq = xorshift(spreadingSeq)

    spreadingDelay_ms = delayWindow_ms + ((spreadingSeq * 2*delayWindow_ms) / 2**16)
    spreadingDelay_s = spreadingDelay_ms / 1000

    return [spreadingSeq, spreadingDelay_s]

def readMessages(data, nominal, tolerance, phaseDelta, bits, printMatches, watermarkShift=13, gw_eui="58A0CBFFFE802A21", gw_ts_name="gwTs", spreading=False, spreadingSeed=int("BEEF", 16), ecc=False):
    msgs = []
    numMsgsLost = 0
    symbols = {
        "possible": 0,
        "errors": 0
        }
    ecc = {
        "dualBit": 0,   # Invalid
        "singleBit": 0, # Corrected
        "noErr": 0
        }

    # Go through messages and extract info
    for element in data:
        msg = copy.deepcopy(template_msg)

        msg["loraMsgId"] = element["result"]["uplink_message"]["f_cnt"]

        onAirTime_s = float(element["result"]["uplink_message"]["consumed_airtime"][:-1])

        if (not readGw(element, gw_eui, onAirTime_s, msg)):
            # Not found, treat like a lost message and do not store in msgs
            continue

        msg["nwTs"]["raw"] = _conv_timestamp(element["result"]["received_at"]).timestamp()
        msg["nwTs"]["seconds"] = msg["nwTs"]["raw"] - onAirTime_s

        a = element["result"]["uplink_message"]["frm_payload"]
        a = int(base64.b64decode(a).hex(),16) # Convert base64 to hexstring
        a = int(struct.pack("<Q", a).hex(), 16) # Convert to little endian
        msg["payload"]["raw"] = int(a / 2**32)  # Pad to 32 bit and use [ms]
        msg["payload"]["seconds"] = msg["payload"]["raw"] / 1000

        if spreading:
            msg["spreading"]["sequence"], msg["spreading"]["delay"] = getSpreadingParam(msg["loraMsgId"], spreadingSeed, 2**bits * phaseDelta * 1000)

        if len(msgs) == 0:
            # First message -> Handle like a lost message
            msg["numLost"] = 1
            print("ID: {0}".format(msg["loraMsgId"]))
            print("\tFirst message")
            print("\tGW   TS: {0:.3f} s".format(msg[gw_ts_name]["seconds"]))
            print("\tPAYLOAD: {0}".format(msg["payload"]["raw"]))

        else:
            preMsg = msgs[-1]
            calcIpd(element, msg, preMsg, gw_ts_name)
            numMsgsLost += msg["numLost"]

            # To calculate the watermark and to extract the symbol,
            # at least 2 subsequent messages are needed
            if (msg["numLost"] == 0):
                msg["calculation"]["watermark"] = calcWatermark(preMsg["payload"]["raw"], msg["payload"]["raw"], shift=watermarkShift)
                msg["calculation"]["effWatermark"] = calcEffWatermark(msg["calculation"]["watermark"], bits)

                if spreading:
                    msg["extraction"]["symbol"], msg[gw_ts_name]["despreaded"] = extractSymbol_ss(msg[gw_ts_name]["delta"], nominal, phaseDelta, tolerance, bits, msg["spreading"]["delay"], preMsg["spreading"]["delay"])
                elif ecc:
                    msg["extraction"]["eccErrors"], msg["extraction"]["symbol"] = extractSymbol_ecc(msg[gw_ts_name]["delta"], nominal, phaseDelta, tolerance, bits)
                    if (msg["extraction"]["eccErrors"] == 0):
                        ecc["noErr"] += 1
                    elif (msg["extraction"]["eccErrors"] == 1):
                        ecc["singleBit"] += 1
                    elif (msg["extraction"]["eccErrors"] == 2):
                        ecc["dualBit"] += 1

                elif not ecc and not spreading:
                    msg["extraction"]["symbol"] = extractSymbol(msg[gw_ts_name]["delta"], nominal, phaseDelta, tolerance, bits)
                else:
                    print("Sorry boss can't do that!")
                    a = 0/0

                if (bits == 1):
                    # Due to DPSK modulation, for 1 bit another subsequent message is needed
                    if ( preMsg["numLost"] == 0 ):
                        if (preMsg["extraction"]["symbol"] != None):
                            msg["extraction"]["effWatermark"] = preMsg["extraction"]["symbol"] ^ msg["extraction"]["symbol"]
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

        msgs.append(msg)

    return {"msgs": msgs, "numMsgsLost": numMsgsLost, "numSymbolsPossible": symbols["possible"], "numSymbolErrors": symbols["errors"], "ecc": ecc}

def xorshift(lfsr):
    # Hattip to: http://www.retroprogramming.com/2017/07/xorshift-pseudorandom-numbers-in-z80.html
    lfsr ^= ( lfsr << 7 ) % 2**16
    lfsr ^= ( lfsr >> 9 ) % 2**16
    lfsr ^= ( lfsr << 8 ) % 2**16
    return lfsr

def printCalculations(res):
    msgs = res["msgs"]
    # Show calculations
    y1 = []
    for ele in msgs:
        if not (ele["gwTs"]["delta"] == None):
            y1.append(ele["gwTs"]["delta"]*1000)

    y1 = np.array(y1)

    print("Packetloss: \n\t{0} (of {1} sent) = {2:.2f}%".format(res["numMsgsLost"], msgs[-1]["loraMsgId"]+1, (res["numMsgsLost"]/(msgs[-1]["loraMsgId"]+1))*100))

    print("Jitter:")
    print("\tmin:  {0:.2f} ms".format(np.min(y1)))
    print("\tmax:  {0:.2f} ms".format(np.max(y1)))
    print("\tavg:  {0:.2f} ms".format(np.average(y1)))

    print("Symbols:")
    print("\tPossible: {0}".format(res["numSymbolsPossible"]))
    print("\tCorrect: {0}\t({1:.2f}%)".format((res["numSymbolsPossible"]-res["numSymbolErrors"]), (((res["numSymbolsPossible"]-res["numSymbolErrors"]) / res["numSymbolsPossible"])*100)))
    print("\tErrors:  {0}\t({1:.2f}%)".format(res["numSymbolErrors"], (res["numSymbolErrors"] / res["numSymbolsPossible"])*100))

    print("Duration: {0}h".format((msgs[-1]["gwTs"]["seconds"] - msgs[0]["gwTs"]["seconds"])/(60*60)))

    # Read SNR/RSSI
    snr = []
    rssi = []

    for ele in msgs:
        if ele["snr"] != None:
            snr.append(ele["snr"])
        if ele["rssi"] != None:
            rssi.append(ele["rssi"])

    print("SNR:")
    print("\tmin: {0} dB".format(np.min(snr)))
    print("\tmax: {0} dB".format(np.max(snr)))
    print("\tavg: {0} dB".format(np.average(snr)))

    print("RSSI:")
    print("\tmin: {0} dBm".format(np.min(rssi)))
    print("\tmax: {0} dBm".format(np.max(rssi)))
    print("\tavg: {0} dBm".format(np.average(rssi)))
