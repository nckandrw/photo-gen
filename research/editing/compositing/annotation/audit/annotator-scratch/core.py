import json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
A="/Users/nckandrw/Dev/photo-gen/research/editing/compositing/annotation/"
cases=json.load(open(A+"cases.json"))
masks=json.load(open(A+"masks-draft.json"))
for case in sys.argv[1:]:
    im=Image.open(A+cases[case]["view"]["file"]).convert("RGB"); w,h=im.size
    sh=Image.new("L",(w,h),0); d=ImageDraw.Draw(sh)
    for p in masks[case]["polygons"]: d.polygon([(x*w,y*h) for x,y in p],fill=255)
    band=round(0.0135*max(w,h))
    arr=np.pad(np.array(sh),30,mode="edge")
    core=Image.fromarray(arr)
    for _ in range(band): core=core.filter(ImageFilter.MinFilter(3))
    core=core.crop((30,30,30+w,30+h))
    red=Image.new("RGB",(w,h),(255,0,0)); blue=Image.new("RGB",(w,h),(0,90,255))
    over=Image.composite(Image.blend(im,red,0.4),im,sh)
    over=Image.composite(Image.blend(im,blue,0.45),over,core)
    over.save(f"{case}-core.png"); print(case,"band",band)
