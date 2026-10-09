import json, sys
path, case, src = sys.argv[1:4]
d = json.load(open(path))
d[case] = json.load(open(src))
json.dump(d, open(path, "w"), indent=1)
print("set", case, len(d[case]["polygons"]), "polygons")
