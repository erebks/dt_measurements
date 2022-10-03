import sys
import json
import operator

if (len(sys.argv) < 3):
    print("Too less arguments!")
    print("Use: python3 {0} in_file out_file".format(sys.argv[0]))
    exit(1)

try:
    in_file = open(sys.argv[1], "r")
    i_json = json.loads(in_file.read())
    in_file.close()
except OSError as e:
    print("Can't read in_file")
    exit(1)

# Put f_cnt at top level for sorting
for j in i_json:
    j["f_cnt"] = j["result"]["uplink_message"]["f_cnt"]

# Sorting
i_json.sort(key=operator.itemgetter('f_cnt'))

# Delte f_cnt at top level
for j in i_json:
    del j["f_cnt"]

# Write to file
out_file = open(sys.argv[2], "w")
out_file.write(json.dumps(i_json))
out_file.close()
