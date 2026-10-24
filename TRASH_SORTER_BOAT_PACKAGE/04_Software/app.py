"""Phone dashboard + control server. Run on the Raspberry Pi:

    python3 app.py            (then open http://<pi-address>:8080 on the phone)
    python3 app.py --mock     (laptop test: no motors, cameras or model needed)
"""
import logging
import sys
import threading
import time

from flask import Flask, Response, jsonify, request

import config
import hardware
import sorter
import vision

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("app")
MOCK = "--mock" in sys.argv

hw = hardware.Hardware()
nav = vision.NavCamera()
cam = vision.SortCamera()
try:
    clf = None if MOCK else vision.Classifier()
except Exception as e:
    log.warning("classifier not loaded (%s) - every item goes to the fallback bin", e)
    clf = None
srt = sorter.Sorter(hw, cam, clf)

app = Flask(__name__)
_last_drive = [0.0]


def watchdog():
    while True:
        if time.time() - _last_drive[0] > config.DRIVE_TIMEOUT_S:
            hw.stop_drive()
        time.sleep(0.1)


threading.Thread(target=watchdog, daemon=True).start()


@app.post("/api/drive")
def drive():
    d = request.get_json(force=True)
    _last_drive[0] = time.time()
    hw.drive(float(d.get("x", 0)), float(d.get("y", 0)))
    return "", 204


@app.post("/api/sorting/<state>")
def sorting(state):
    srt.set_enabled(state == "on")
    return "", 204


@app.post("/api/intake/reverse")
def intake_reverse():
    """Back the intake belt off for 1.5 s to clear a jam."""
    hw.conveyor(1, -config.C1_SPEED)
    time.sleep(1.5)
    hw.conveyor(1, config.C1_SPEED if srt.enabled else 0)
    return "", 204


@app.post("/api/bin/<int:n>/<state>")
def bin_flap(n, state):
    hw.flap(n, state == "open")
    return "", 204


@app.get("/api/status")
def status():
    last = srt.last and {k: v for k, v in srt.last.items() if k != "votes"}
    return jsonify(state=srt.state, enabled=srt.enabled, counts=srt.counts, last=last,
                   item=hw.item_present(), nav_camera=nav.ok, model=clf is not None)


@app.get("/video.mjpg")
def video():
    def gen():
        while True:
            jpg = nav.latest()
            if jpg:
                yield b"--f\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            time.sleep(0.06)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=f")


@app.get("/")
def index():
    return PAGE


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>Trash Sorter Boat</title><style>
body{margin:0;font-family:system-ui,sans-serif;background:#101418;color:#e8eaed;touch-action:none}
.wrap{max-width:900px;margin:auto;padding:10px}
#cam{width:100%;border-radius:8px;background:#000;aspect-ratio:4/3;object-fit:cover}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
#pad{width:220px;height:220px;border-radius:50%;background:#1f2933;position:relative;flex:none}
#knob{width:70px;height:70px;border-radius:50%;background:#f2a33a;position:absolute;left:75px;top:75px}
button{flex:1;min-width:90px;padding:12px;border:0;border-radius:8px;background:#2d3a45;color:#e8eaed;font-size:15px}
button.on{background:#2e7d32}.bins{display:grid;grid-template-columns:1fr 1fr;gap:8px;flex:1;min-width:220px}
.card{background:#1f2933;border-radius:8px;padding:10px}.big{font-size:22px;font-weight:600}
</style></head><body><div class="wrap">
<img id="cam" src="/video.mjpg" alt="navigation camera">
<div class="row"><div id="pad"><div id="knob"></div></div>
<div class="bins">
<div class="card">Bin 1<div class="big" id="b1">0</div><button onclick="flap(1)">open</button></div>
<div class="card">Bin 2<div class="big" id="b2">0</div><button onclick="flap(2)">open</button></div>
<div class="card">Bin 3<div class="big" id="b3">0</div><button onclick="flap(3)">open</button></div>
<div class="card">Bin 4<div class="big" id="b4">0</div><button onclick="flap(4)">open</button></div>
</div></div>
<div class="row"><button id="sort" onclick="toggle()">Sorting OFF</button><button onclick="post('/api/intake/reverse')">Unjam intake</button></div>
<div class="row"><div class="card" style="flex:1"><span id="state">-</span> &middot; last: <span id="last">-</span></div></div>
</div><script>
const post=(u,b)=>fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):null});
let on=false,x=0,y=0,held=false;
function toggle(){on=!on;post('/api/sorting/'+(on?'on':'off'));}
function flap(n){post('/api/bin/'+n+'/open');setTimeout(()=>post('/api/bin/'+n+'/closed'),2000);}
const pad=document.getElementById('pad'),knob=document.getElementById('knob');
function move(e){const r=pad.getBoundingClientRect(),t=e.touches?e.touches[0]:e;
 x=Math.max(-1,Math.min(1,(t.clientX-r.left-r.width/2)/(r.width/2)));
 y=Math.max(-1,Math.min(1,-(t.clientY-r.top-r.height/2)/(r.height/2)));
 knob.style.left=(75+x*75)+'px';knob.style.top=(75-y*75)+'px';}
function end(){held=false;x=0;y=0;knob.style.left='75px';knob.style.top='75px';post('/api/drive',{x:0,y:0});}
pad.addEventListener('touchstart',e=>{held=true;move(e)});pad.addEventListener('touchmove',move);pad.addEventListener('touchend',end);
pad.addEventListener('mousedown',e=>{held=true;move(e)});addEventListener('mousemove',e=>{if(held)move(e)});addEventListener('mouseup',()=>{if(held)end()});
setInterval(()=>{if(held)post('/api/drive',{x,y});},100);
setInterval(async()=>{try{const s=await (await fetch('/api/status')).json();on=s.enabled;
 const b=document.getElementById('sort');b.textContent='Sorting '+(on?'ON':'OFF');b.className=on?'on':'';
 for(const k in s.counts)document.getElementById('b'+k).textContent=s.counts[k];
 document.getElementById('state').textContent=s.state;
 document.getElementById('last').textContent=s.last?(s.last.label||'unsure')+' \\u2192 bin '+s.last.bin:'-';}catch(e){}},500);
</script></body></html>"""


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=config.HTTP_PORT, threaded=True)
    finally:
        hw.all_stop()
