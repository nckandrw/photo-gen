import csv, sys
with open(sys.argv[1], "a", newline="") as f:
    csv.writer(f, lineterminator="\n").writerow(sys.argv[2:])
