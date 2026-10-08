import csv, sys
path = sys.argv[1]
with open(path, newline='') as f:
    rows = list(csv.reader(f))
hdr = rows[0]; idx = {h:i for i,h in enumerate(hdr)}
byid = {r[0]: r for r in rows[1:]}

s02 = ("Faces and fine detail smeared, faint checker texture in dark areas; t1 'BIRTHPLACE of' turned into gibberish, 'BEATLES' letters deformed and the round logos lose their wording (wrong letters); t2 'Quarry' reads like '{q}' (wrong letters); t3 lettering reduced to dark blobs (blur); t4 fascia 'arry' deformed into wrong letters (round 'Q' sign intact); t5 red fascia blank (blur) and the tall sign's small lettering turned into a grid pattern (blur).")
byid['S02-B'][idx['notes']] = s02.format(q='Qlanny')
byid['S02-C'][idx['notes']] = s02.format(q='Qlanny')
byid['S02-D'][idx['notes']] = s02.format(q='Quanny')

s04 = ("t1 sign lettering turned into blocky marks with no recognisable letters (wrong letters and blur); t2 word smeared into an unreadable dark line and the two bicycle pictograms replaced by digit-like squiggles (wrong letters and blur).")
for k in ('S04-A','S04-C','S04-D'):
    byid[k][idx['notes']] = s04
byid['S04-B'][idx['t1']] = 'GARBLED'
byid['S04-B'][idx['notes']] = ("t1 'NIEUWE UILENBURGER / STRAAT' only barely legible through heavy softening and the small 'CENTRUM' is unreadable (blur, no invented letters); t2 'uitgezonderd' barely legible through blur, bicycle pictograms intact.")

s05 = ("Both fascia cartoon mascots lose facial detail (left face becomes a pale blue blob, right eyes merge); t2 still reads 'in our new webstor / ...uilingbooks.co' but 'new' is broken toward 'now' and the 'p' looks like a 'g'; t4 'SAVE LIVES' / 'STOP THE CITY' rendered with wrong letters (like '{x}'); t5 sticker lettering reduced to white bars (blur).")
byid['S05-A'][idx['notes']] = s05.format(x='CAVE IIVES')
byid['S05-D'][idx['notes']] = s05.format(x='CAVE IIVES')
byid['S05-E'][idx['notes']] = s05.format(x='GAHE IIVES')
byid['S05-B'][idx['notes']] = ("Both mascots recoloured from lime green to orange/red and distorted; t1 'Beguiling' fine but the small 'The' is deformed (the e closes up like a B); t2 reads like 'inaur new wehsto' (wrong letters); t3 number smeared into unreadable marks (wrong letters and blur); t4 poster lettering unreadable with wrong letter shapes (wrong letters and blur); t5 sticker lettering gone (blur).")
byid['S05-C'][idx['t4']] = 'GARBLED'
byid['S05-C'][idx['notes']] = ("Left mascot's face smeared (right mascot close to ORIGINAL); t3 first digit deformed toward an S/8 shape but the number still reads; t4 'SAVE LIVES' and 'STOP THE CITY' still read correctly but the top line 'TORONTO TINY SHELTERS' is unreadable (blur, no invented letters); t5 sticker lettering reduced to white bars (blur).")

s06 = ("t1 still reads 'MATHEW STREET / BIRTHPLACE of THE BEATLES' but the B of BIRTHPLACE breaks into vertical strokes and STREET's R is deformed; t3 reads like '{x}' instead of 'Club Cut' (wrong letters); t5 red fascia 'LIVE SPORTS SHOWN' turned into blocky shapes with the first word wrong, like 'LBE' (wrong letters), while the tall sign's 'ELL' and 'You' stay intact.")
byid['S06-A'][idx['notes']] = s06.format(x='Chib Car')
byid['S06-B'][idx['notes']] = s06.format(x='Chib Car')
byid['S06-D'][idx['notes']] = s06.format(x='Clab Car')

byid['S07-C'][idx['t4']] = 'DEGRADED'
byid['S07-C'][idx['notes']] = ("t4 'TORONTO TINY SHELTERS / SAVE LIVES / STOP THE CITY' read correctly but the tiny lines below are only barely legible; t5 'blogTO' and 'BEST OF' read correctly but the tiny 'TORONTO' line is only barely legible.")

with open(path, 'w', newline='') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerows(rows)
