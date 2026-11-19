"""The Tower Massing Agent's review sheet: the page a design team would look at.

Serves the four stages of massing.py and draws the chosen option as a plan and an elevation, so the run can be watched
rather than read from a terminal. Everything is computed locally on the Dell Pro Precision GB10.
"""
from __future__ import annotations

import threading
import time
import uuid

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

import massing as M

app = FastAPI(title="Tower Massing Agent")
RUNS: dict[str, dict] = {}
IFC_DIR = "/tmp/massing-ifc"


class Brief(BaseModel):
    rfp: str


def elevation_svg(opt: dict, c: dict) -> str:
    """A stacked-floor elevation, scaled to the height cap."""
    cap = c["max_height_m"]
    H, W = 260, 120
    scale = (H - 20) / cap
    parts = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    parts.append(f'<line x1="4" y1="{H-10}" x2="{W-4}" y2="{H-10}" stroke="#39414f"/>')
    # height cap line
    yc = H - 10 - cap * scale
    parts.append(f'<line x1="4" y1="{yc:.1f}" x2="{W-4}" y2="{yc:.1f}" stroke="#7a8697" stroke-dasharray="3 3"/>')
    parts.append(f'<text x="{W-4}" y="{yc-4:.1f}" fill="#9aa3b2" font-size="8" text-anchor="end">cap {cap:.0f} m</text>')
    z = 0.0
    bw = 54
    for i in range(opt["podium_floors"]):
        h = c["podium_floor_to_floor_m"] * scale
        y = H - 10 - (z + c["podium_floor_to_floor_m"]) * scale
        parts.append(f'<rect x="{(W-bw*1.35)/2:.1f}" y="{y:.1f}" width="{bw*1.35:.1f}" height="{h:.1f}" fill="#1d4e78" stroke="#2b6fa8"/>')
        z += c["podium_floor_to_floor_m"]
    for i in range(opt["tower_floors"]):
        h = c["tower_floor_to_floor_m"] * scale
        y = H - 10 - (z + c["tower_floor_to_floor_m"]) * scale
        parts.append(f'<rect x="{(W-bw)/2:.1f}" y="{y:.1f}" width="{bw}" height="{max(h-0.6,0.8):.1f}" fill="#0f3category" stroke="#2b6fa8"/>'.replace("#0f3category", "#123a5a"))
        z += c["tower_floor_to_floor_m"]
    parts.append(f'<text x="{W/2:.0f}" y="{H-1}" fill="#9aa3b2" font-size="8" text-anchor="middle">{opt["height_m"]:.1f} m</text>')
    parts.append("</svg>")
    return "".join(parts)


def plan_svg(opt: dict, st: dict, c: dict) -> str:
    """Site plan: plot, setback envelope, floorplate, column grid and core."""
    W, H = 300, 230
    pad = 14
    sx = (W - 2 * pad) / c["plot_x_m"]
    sy = (H - 2 * pad) / c["plot_y_m"]
    s = min(sx, sy)
    px, py = c["plot_x_m"] * s, c["plot_y_m"] * s
    ox, oy = (W - px) / 2, (H - py) / 2
    p = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    p.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{px:.1f}" height="{py:.1f}" fill="#11141b" stroke="#39414f"/>')
    sb = c["setback_m"] * s
    p.append(f'<rect x="{ox+sb:.1f}" y="{oy+sb:.1f}" width="{px-2*sb:.1f}" height="{py-2*sb:.1f}" fill="none" stroke="#7a8697" stroke-dasharray="4 3"/>')
    fw, fh = opt["floorplate_x"] * s, opt["floorplate_y"] * s
    fx, fy = ox + (px - fw) / 2, oy + (py - fh) / 2
    p.append(f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{fw:.1f}" height="{fh:.1f}" fill="#123a5a" stroke="#2b6fa8"/>')
    # column grid
    bx, by = [int(v) for v in st["bays"].split(" × ")]
    for i in range(bx + 1):
        for j in range(by + 1):
            cx = fx + fw * i / bx
            cy = fy + fh * j / by
            p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.8" fill="#9ccbf0"/>')
    cw, ch = st["core_x_m"] * s, st["core_y_m"] * s
    p.append(f'<rect x="{fx+(fw-cw)/2:.1f}" y="{fy+(fh-ch)/2:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="#2b6fa8" opacity="0.65"/>')
    p.append(f'<text x="{ox:.0f}" y="{oy-4:.0f}" fill="#9aa3b2" font-size="9">plot {c["plot_x_m"]:.0f} × {c["plot_y_m"]:.0f} m · setback {c["setback_m"]:.0f} m · core shaded</text>')
    p.append("</svg>")
    return "".join(p)


def do_run(rid: str, rfp: str) -> None:
    r = RUNS[rid]
    try:
        t0 = time.time()
        c = M.read_rfp(rfp)
        r["constraints"] = c
        r["t_read"] = round(time.time() - t0, 1)
        r["stage"] = 2

        t0 = time.time()
        opts = [o for o in M.massing_options(c)]
        r["options"] = [{**o.__dict__, "passes": o.passes,
                         "checks": {k: {"ok": v[0], "detail": v[1]} for k, v in o.checks.items()}} for o in opts]
        chosen = next((o for o in opts if o.passes), None)
        r["chosen"] = chosen.name if chosen else None
        r["t_massing"] = round(time.time() - t0, 2)
        r["stage"] = 3

        if chosen:
            st = M.structure(chosen, c)
            r["structure"] = st
            co = next(o for o in r["options"] if o["name"] == chosen.name)
            r["plan_svg"] = plan_svg(co, st, c)
            r["elevation_svg"] = elevation_svg(co, c)
            r["stage"] = 4

            import os
            os.makedirs(IFC_DIR, exist_ok=True)
            path = f"{IFC_DIR}/{rid}.ifc"
            M.write_ifc(chosen, st, c, path)
            import ifcopenshell
            f = ifcopenshell.open(path)
            r["ifc"] = {"file": f"{rid}.ifc", "schema": f.schema,
                        "storeys": len(f.by_type("IfcBuildingStorey")),
                        "top": f.by_type("IfcBuildingStorey")[-1].Name,
                        "bytes": os.path.getsize(path)}
        r["done"] = True
    except Exception as e:
        r["error"] = f"{type(e).__name__}: {e}"
        r["done"] = True


@app.post("/api/run")
def start(b: Brief):
    rid = uuid.uuid4().hex[:8]
    RUNS[rid] = {"stage": 1, "done": False, "error": "", "rfp": b.rfp}
    threading.Thread(target=do_run, args=(rid, b.rfp), daemon=True).start()
    return {"id": rid}


@app.get("/api/run/{rid}")
def poll(rid: str):
    r = RUNS.get(rid)
    return r or JSONResponse({"error": "no such run"}, status_code=404)


@app.get("/ifc/{name}")
def ifc(name: str):
    return FileResponse(f"{IFC_DIR}/{name}", media_type="application/x-step", filename=name)


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Tower Massing Agent</title><style>
:root{--dell:#0076CE;--line:#2a2f3a;--muted:#9aa3b2}
*{box-sizing:border-box}
body{margin:0;background:#0b0d12;color:#eef1f6;font:15px/1.55 "Segoe UI",system-ui,sans-serif}
header{padding:18px 28px;border-bottom:1px solid var(--line);display:flex;gap:14px;align-items:baseline}
h1{font-size:19px;margin:0;font-weight:600}.sub{color:var(--muted);font-size:13px}
main{padding:22px 28px;max-width:1220px}
.cols{display:flex;gap:20px;align-items:flex-start}
.brief{flex:0 0 330px}
textarea{width:100%;height:190px;background:#11141b;color:#eef1f6;border:1px solid var(--line);border-radius:8px;padding:12px;font:13px/1.5 ui-monospace,monospace;resize:vertical}
button{margin-top:10px;padding:11px 22px;border:0;border-radius:7px;background:var(--dell);color:#fff;font-weight:600;font-size:15px;cursor:pointer}
button:disabled{opacity:.5}
.work{flex:1;min-width:0}
.stage{border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:14px;background:#0f1218}
.stage h2{font-size:14px;margin:0 0 10px;font-weight:600;letter-spacing:.01em}
.time{float:right;color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;font-size:13px}
td,th{padding:4px 8px;text-align:left;border-bottom:1px solid #1b1f28}
th{color:var(--muted);font-weight:500}
.opt{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:9px;background:#11141b}
.opt.pick{border-color:var(--dell)}
.opt h3{margin:0 0 6px;font-size:13px;font-weight:600;display:flex;justify-content:space-between}
.chip{display:inline-block;padding:1px 7px;border-radius:99px;font-size:11px;margin:2px 4px 2px 0}
.ok{background:#15351f;color:#8fe3a6}.no{background:#3a1a1a;color:#ff9c9c}
.pickbadge{background:var(--dell);color:#fff;padding:1px 8px;border-radius:99px;font-size:11px}
.draw{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}
.muted{color:var(--muted);font-size:12px}
a{color:#7fc0f0}
.pending{color:var(--muted);font-size:13px}
.err{color:#ff8a8a}
</style></head><body>
<header><h1>Tower Massing Agent</h1><span class="sub">reads the brief, tests the options, writes the BIM file — locally on Dell Pro Precision GB10</span></header>
<main><div class="cols">
<div class="brief">
<div class="muted" style="margin-bottom:6px">Development brief (RFP)</div>
<textarea id="rfp"></textarea>
<button id="go">Run the study</button>
</div>
<div class="work" id="out"></div>
</div></main>
<script>
const RFP = `Mixed-use tower, Westmoor district, plot W-14.

The plot is 48 m by 62 m. The authority caps height at 120 metres above grade and requires a 6 metre setback from
every boundary above the podium. Site coverage at podium level may not exceed 70 per cent of the plot.

We need at least 42,000 square metres of gross floor area. The brief is offices above, retail in a two-storey podium.
Floor to floor is 4.2 metres in the podium and 3.6 metres in the tower. Provide a central core.`;
document.getElementById("rfp").value = RFP;
const LBL={plot_x_m:"Plot width",plot_y_m:"Plot depth",max_height_m:"Height cap",setback_m:"Setback",max_site_coverage:"Max site coverage",min_gfa_m2:"Gross floor area required",podium_floors:"Podium storeys",podium_floor_to_floor_m:"Podium floor to floor",tower_floor_to_floor_m:"Tower floor to floor"};
const UNIT={plot_x_m:"m",plot_y_m:"m",max_height_m:"m",setback_m:"m",max_site_coverage:"",min_gfa_m2:"m²",podium_floors:"",podium_floor_to_floor_m:"m",tower_floor_to_floor_m:"m"};
function render(d){
  let h="";
  h+=`<div class="stage">${d.t_read!==undefined?`<span class="time">${d.t_read}s</span>`:""}<h2>1 · Reading the brief <span class="muted">— local model, Qwen3.6</span></h2>`;
  if(d.constraints){h+="<table><tr><th>Constraint</th><th>Value</th></tr>";
    for(const k in LBL) h+=`<tr><td>${LBL[k]}</td><td>${d.constraints[k]} ${UNIT[k]}</td></tr>`;
    h+="</table>";}
  else h+=`<div class="pending">reading…</div>`;
  h+=`</div>`;
  if(d.options){
    h+=`<div class="stage"><span class="time">${d.t_massing}s</span><h2>2 · Massing options, checked against the brief</h2>`;
    d.options.forEach(o=>{
      h+=`<div class="opt ${o.name===d.chosen?"pick":""}"><h3><span>${o.name} — ${o.floorplate_x}×${o.floorplate_y} m, ${o.tower_floors} floors, ${o.height_m.toFixed(1)} m, ${Math.round(o.gfa_m2).toLocaleString()} m²</span>${o.name===d.chosen?'<span class="pickbadge">chosen</span>':""}</h3>`;
      for(const k in o.checks){const c=o.checks[k];h+=`<span class="chip ${c.ok?"ok":"no"}">${c.ok?"✓":"✗"} ${k} · ${c.detail}</span>`}
      h+=`</div>`;
    });
    h+=`</div>`;
  }
  if(d.structure){
    h+=`<div class="stage"><h2>3 · Structure and 4 · BIM output</h2><div class="draw">
      <div>${d.plan_svg||""}<div class="muted">plan: column grid and core</div></div>
      <div>${d.elevation_svg||""}<div class="muted">elevation</div></div>
      <div><table>
      <tr><td>Column grid</td><td>${d.structure.column_grid_x_m} × ${d.structure.column_grid_y_m} m (${d.structure.bays} bays)</td></tr>
      <tr><td>Columns per floor</td><td>${d.structure.columns_per_floor}</td></tr>
      <tr><td>Core</td><td>${d.structure.core_x_m} × ${d.structure.core_y_m} m (${d.structure.core_share})</td></tr>
      ${d.ifc?`<tr><td>IFC file</td><td>${d.ifc.schema}, ${d.ifc.storeys} storeys, top ${d.ifc.top} — <a href="/ifc/${d.ifc.file}">download</a></td></tr>`:""}
      </table><div class="muted" style="margin-top:8px">${d.structure.basis}</div></div>
    </div></div>`;
  }
  if(d.error) h+=`<div class="stage err">${d.error}</div>`;
  document.getElementById("out").innerHTML=h;
}
document.getElementById("go").onclick=async()=>{
  const b=document.getElementById("go"); b.disabled=true;
  const r=await fetch("/api/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({rfp:document.getElementById("rfp").value})});
  const {id}=await r.json();
  const t=setInterval(async()=>{
    const d=await (await fetch("/api/run/"+id)).json();
    render(d);
    if(d.done){clearInterval(t);b.disabled=false}
  },900);
};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
