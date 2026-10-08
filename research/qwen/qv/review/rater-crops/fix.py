import csv, io, sys
p = sys.argv[1] + "/scores-draft.csv"
lines = open(p, newline="").read().split("\n")
out = []
for ln in lines:
    if ln.startswith("V05-A,"):
        row = next(csv.reader([ln]))
        row[1] = "MINOR"; row[2] = "detail-loss/blur"
        row[8] = row[8].replace("Scene otherwise matches ORIGINAL.", "Crowd faces and small figures are smeared (e.g. the blonde woman at the left becomes a colour blob) where B keeps them.")
        buf = io.StringIO(); csv.writer(buf, lineterminator="").writerow(row); ln = buf.getvalue()
    out.append(ln)
open(p, "w", newline="").write("\n".join(out))
