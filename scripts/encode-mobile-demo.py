import av
from fractions import Fraction
from pathlib import Path
root=Path('artifacts/mobile-video');c=av.open(str(root/'raw.webm'));start=None;seen=False
for f in c.decode(video=0):
 r,g,b=f.to_image().getpixel((5,5))
 marker=r>200 and g<70 and b>200
 if marker:seen=True
 elif seen:start=float(f.time);break
c.close()
if start is None:raise RuntimeError('Missing sync marker')
out=av.open(str(root/'math-explorer-mobile.mp4'),'w',options={'movflags':'+faststart'});s=out.add_stream('libx264',rate=25);s.width=1080;s.height=1350;s.pix_fmt='yuv420p';s.options={'crf':'18','preset':'medium'}
c=av.open(str(root/'raw.webm'));n=0
for f in c.decode(video=0):
 if float(f.time)<start:continue
 if n>=312:break
 if n==225:f.to_image().save(root/'math-explorer-mobile-poster.jpg',quality=95)
 f.pts=n;f.time_base=Fraction(1,25)
 for packet in s.encode(f):out.mux(packet)
 n+=1
for packet in s.encode():out.mux(packet)
out.close();c.close()
check=av.open(str(root/'math-explorer-mobile.mp4'));v=check.streams.video[0];print(v.codec_context.name,v.width,v.height,n/25,'seconds', (root/'math-explorer-mobile.mp4').stat().st_size,'bytes');assert n==312;check.close()
