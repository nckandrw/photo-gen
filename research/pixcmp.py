#!/usr/bin/env python3
"""Compare decoded RGB pixels of two PNGs (ignores metadata chunks). Prints identical / #diff pixels / max abs diff, and PNG chunk types."""
import struct, sys, zlib
def load(path):
    d=open(path,'rb').read(); i=8; idat=b''; chunks=[]
    while i<len(d):
        n=struct.unpack('>I',d[i:i+4])[0]; t=d[i+4:i+8]; chunks.append(t.decode())
        if t==b'IHDR': w,h,bd,ct=struct.unpack('>IIBB',d[i+8:i+18])
        if t==b'IDAT': idat+=d[i+8:i+8+n]
        i+=12+n
    bpp={2:3,6:4}[ct]; raw=zlib.decompress(idat); stride=w*bpp; prev=bytearray(stride); px=bytearray()
    for y in range(h):
        f=raw[y*(stride+1)]; line=bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)])
        for x in range(stride):
            a=line[x-bpp] if x>=bpp else 0; b=prev[x]; c=prev[x-bpp] if x>=bpp else 0
            if f==1: line[x]=(line[x]+a)&255
            elif f==2: line[x]=(line[x]+b)&255
            elif f==3: line[x]=(line[x]+(a+b)//2)&255
            elif f==4:
                p=a+b-c; pa,pb,pc=abs(p-a),abs(p-b),abs(p-c); line[x]=(line[x]+(a if pa<=pb and pa<=pc else (b if pb<=pc else c)))&255
        px+=line; prev=line
    return (w,h,bpp),px,sorted(set(chunks))
(a_meta,a,ac),(b_meta,b,bc)=load(sys.argv[1]),load(sys.argv[2])
if a_meta!=b_meta: print("shape differs",a_meta,b_meta); sys.exit()
diff=[abs(x-y) for x,y in zip(a,b) if x!=y]
print(f"{a_meta} chunks={ac}|{bc} pixels_identical={not diff} differing_bytes={len(diff)} max_abs={max(diff) if diff else 0}")
