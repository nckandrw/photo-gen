import json, sys
# args: out.json  ox oy scale  x0n y0n per05x per05y? -> generic: convert crop-scaled coords to normalised
# usage: mkpoly.py W H ox oy scale "X,Y X,Y ..."  -> prints normalised list
W,H,ox,oy,s=map(float,sys.argv[1:6])
pts=[]
for tok in sys.argv[6].split():
    X,Y=map(float,tok.split(","))
    pts.append([round((X/s+ox)/W,4), round((Y/s+oy)/H,4)])
print(json.dumps(pts))
