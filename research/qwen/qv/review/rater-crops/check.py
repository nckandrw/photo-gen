import csv, sys
b = sys.argv[1]
S = list(csv.reader(open(b + "/scores-draft.csv", newline="")))
P = list(csv.reader(open(b + "/preference-draft.csv", newline="")))
assert S[0] == next(csv.reader(open(b + "/scores-template.csv"))), "score header"
assert P[0] == next(csv.reader(open(b + "/preference-template.csv"))), "pref header"
sheets = ["V01","V02","V03","V04","V05","V06"]
ids = [f"{s}-{v}" for s in sheets for v in "AB"]
assert [r[0] for r in S[1:]] == ids, [r[0] for r in S[1:]]
assert [r[0] for r in P[1:]] == sheets
T = {"PRESERVED","DEGRADED","GARBLED","REMOVED","NA"}
FAM = {"seam/halo","grain/grid","malformed-object","texture-smear","lighting-mismatch","colour-cast","detail-loss/blur","ghosting/duplication","oversharpening"}
n = {"V03":2,"V04":2}
for r in S[1:]:
    assert len(r) == 9, (r[0], len(r))
    fid, fam = r[1], r[2]
    assert fid in {"PASS","MINOR","MAJOR"}
    assert (fam == "") == (fid == "PASS"), r[0]
    if fam: assert fam in FAM or fam.startswith("other:"), fam
    k = n.get(r[0][:3], 5)
    for i, t in enumerate(r[3:8]):
        assert (t in T) if i < k else (t == "-"), (r[0], i, t)
    assert r[8].strip()
by = {r[0]: r for r in S[1:]}
for s in sheets:
    for i in range(3, 8):
        a, bb = by[s+"-A"][i], by[s+"-B"][i]
        assert (a == "NA") == (bb == "NA"), (s, i)
for r in P[1:]:
    assert len(r) == 3 and r[1] in {"A","B","SAME"} and r[2].strip()
print("OK", len(S)-1, "score rows;", len(P)-1, "preference rows")
