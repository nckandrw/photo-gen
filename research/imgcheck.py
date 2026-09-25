#!/usr/bin/env python3
"""Minimal PNG sanity check (no deps): dimensions + per-channel mean/std on RGB 8-bit PNGs."""
import struct, sys, zlib
def paeth(a,b,c):
    p=a+b-c; pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
    return a if pa<=pb and pa<=pc else (b if pb<=pc else c)
for path in sys.argv[1:]:
    d=open(path,'rb').read(); i=8; idat=b''
    while i<len(d):
        n=struct.unpack('>I',d[i:i+4])[0]; t=d[i+4:i+8]
        if t==b'IHDR': w,h,bd,ct=struct.unpack('>IIBB',d[i+8:i+18])
        if t==b'IDAT': idat+=d[i+8:i+8+n]
        i+=12+n
    bpp={2:3,6:4}[ct]; raw=zlib.decompress(idat); stride=w*bpp; prev=bytearray(stride); px=bytearray()
    for y in range(h):
        f=raw[y*(stride+1)]; line=bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)])
        for x in range(stride):
            a=line[x-bpp] if x>=bpp else 0; b=prev[x]; c=prev[x-bpp] if x>=bpp else 0
            line[x]=(line[x]+(0,a,b,(a+b)//2,paeth(a,b,c))[f])&255
        px+=line; prev=line
    ch=[px[k::bpp] for k in range(3)]
    stats=[(sum(c)/len(c),(sum(v*v for v in c)/len(c)-(sum(c)/len(c))**2)**.5) for c in ch]
    blank=all(s<2 for _,s in stats)
    print(f"{path}: {w}x{h} mean={[round(m,1) for m,_ in stats]} std={[round(s,1) for _,s in stats]} {'BLANK/UNIFORM' if blank else 'non-uniform'}")
