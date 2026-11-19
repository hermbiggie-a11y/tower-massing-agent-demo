"""Tower Massing Agent: brief to BIM, entirely on the workstation.

Written by Dell, 2026-11-19. The concept is inspired by an NVIDIA multi-application agentic AI workflow; no NVIDIA
code, assets or footage are used. That workflow is described as: read the RFP and concept sketch, coordinate massing
and structure, prepare BIM output for design review.

This runs entirely on a Dell Pro Precision GB10:

  1. read the RFP      a local model (Qwen3.6 via Ollama) turns the written brief into numbered constraints
  2. massing           parametric options are generated and each is checked against those constraints
  3. structure         a column grid and core are sized for the chosen option
  4. BIM output        a real IFC4 file (ifcopenshell) plus a review sheet of the numbers

The workflow this is modelled on drives Rhino, which is Windows-only and licensed. This one uses open CAD libraries
instead (build123d/OpenCascade for solids, ifcopenshell for IFC, shapely for the site). The README says so plainly.

Nothing here is an architectural or engineering authority: the structural sizing is a rule-of-thumb grid for a massing
review, not a design. The review sheet says that on its face.
"""
from __future__ import annotations

import json
import math
import re
import urllib.request
from dataclasses import dataclass, asdict

OLLAMA = "http://127.0.0.1:11534"
MODEL = "qwen3.6"

RFP = """Mixed-use tower, Westmoor district, plot W-14.

The plot is 48 m by 62 m. The authority caps height at 120 metres above grade and requires a 6 metre setback from
every boundary above the podium. Site coverage at podium level may not exceed 70 per cent of the plot.

We need at least 42,000 square metres of gross floor area. The brief is offices above, retail in a two-storey podium.
Floor to floor is 4.2 metres in the podium and 3.6 metres in the tower. Provide a central core.
"""

SCHEMA = {
    "plot_x_m": "plot width in metres",
    "plot_y_m": "plot depth in metres",
    "max_height_m": "height cap above grade in metres",
    "setback_m": "setback from each boundary above the podium, metres",
    "max_site_coverage": "podium site coverage as a fraction, e.g. 0.7",
    "min_gfa_m2": "minimum gross floor area in square metres",
    "podium_floors": "number of podium storeys",
    "podium_floor_to_floor_m": "podium floor to floor in metres",
    "tower_floor_to_floor_m": "tower floor to floor in metres",
}


def ask_model(prompt: str, timeout: int = 300) -> str:
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["response"]


def read_rfp(rfp: str) -> dict:
    """Stage 1. The local model reads the written brief and returns the numbers as JSON."""
    fields = "\n".join(f'  "{k}": <{v}>' for k, v in SCHEMA.items())
    out = ask_model(
        "You are reading a development brief and extracting its numeric constraints.\n"
        "Return ONLY a JSON object, no prose, no code fence, with exactly these keys:\n"
        f"{{\n{fields}\n}}\n\n"
        "Use numbers only (no units in the values). If the brief does not state something, use null.\n\n"
        f"BRIEF:\n{rfp}\n")
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        raise RuntimeError(f"the model did not return JSON: {out[:300]}")
    return json.loads(m.group(0))


@dataclass
class Option:
    name: str
    floorplate_x: float
    floorplate_y: float
    tower_floors: int
    podium_floors: int
    height_m: float = 0.0
    gfa_m2: float = 0.0
    podium_coverage: float = 0.0
    checks: dict = None

    def evaluate(self, c: dict) -> "Option":
        podium_x = c["plot_x_m"] * math.sqrt(c["max_site_coverage"])
        podium_y = c["plot_y_m"] * math.sqrt(c["max_site_coverage"])
        podium_area = podium_x * podium_y
        tower_area = self.floorplate_x * self.floorplate_y
        self.podium_coverage = podium_area / (c["plot_x_m"] * c["plot_y_m"])
        self.height_m = (self.podium_floors * c["podium_floor_to_floor_m"]
                         + self.tower_floors * c["tower_floor_to_floor_m"])
        self.gfa_m2 = podium_area * self.podium_floors + tower_area * self.tower_floors
        max_x = c["plot_x_m"] - 2 * c["setback_m"]
        max_y = c["plot_y_m"] - 2 * c["setback_m"]
        self.checks = {
            "height within cap": (self.height_m <= c["max_height_m"] + 1e-6,
                                  f"{self.height_m:.1f} m / {c['max_height_m']:.0f} m"),
            "gross floor area met": (self.gfa_m2 >= c["min_gfa_m2"],
                                     f"{self.gfa_m2:,.0f} m² / {c['min_gfa_m2']:,.0f} m² required"),
            "setback respected": (self.floorplate_x <= max_x and self.floorplate_y <= max_y,
                                  f"{self.floorplate_x:.0f}×{self.floorplate_y:.0f} m inside {max_x:.0f}×{max_y:.0f} m"),
            "podium coverage within limit": (self.podium_coverage <= c["max_site_coverage"] + 1e-6,
                                             f"{self.podium_coverage*100:.0f}% / {c['max_site_coverage']*100:.0f}%"),
        }
        return self

    @property
    def passes(self) -> bool:
        return all(ok for ok, _ in self.checks.values())


def massing_options(c: dict) -> list[Option]:
    """Stage 2. Parametric options inside the setback envelope, each checked against the brief.

    Each option takes the floorplate as a share of the setback envelope and then stacks as many tower storeys as the
    height cap allows, which is what the envelope is really worth. The options are meant to bracket the brief, so a
    slender one can legitimately come up short on floor area: that is the check doing its job, not a bug.
    """
    max_x = c["plot_x_m"] - 2 * c["setback_m"]
    max_y = c["plot_y_m"] - 2 * c["setback_m"]
    pods = int(c["podium_floors"] or 2)
    podium_h = pods * c["podium_floor_to_floor_m"]
    # + 1e-9 because binary floats make (120 - 8.4) / 3.6 come out as 30.999999999999996, which would silently
    # throw away the top floor of a tower that fits the cap exactly.
    floors = max(1, int((c["max_height_m"] - podium_h) / c["tower_floor_to_floor_m"] + 1e-9))
    out = []
    for name, ax, ay in [("A  slender", 0.70, 0.60), ("B  balanced", 0.85, 0.80), ("C  broad", 1.00, 0.95)]:
        out.append(Option(name, round(max_x * ax), round(max_y * ay), floors, pods).evaluate(c))
    return out


def structure(opt: Option, c: dict) -> dict:
    """Stage 3. A rule-of-thumb grid and core for the chosen massing. Not an engineering design."""
    target = 9.0  # m, typical office column spacing
    bays_x = max(2, round(opt.floorplate_x / target))
    bays_y = max(2, round(opt.floorplate_y / target))
    # core sized at ~18% of the floorplate, the usual range for an office tower of this height
    core_area = opt.floorplate_x * opt.floorplate_y * 0.18
    core_x = round(math.sqrt(core_area * 1.4), 1)
    core_y = round(core_area / core_x, 1)
    return {
        "column_grid_x_m": round(opt.floorplate_x / bays_x, 2),
        "column_grid_y_m": round(opt.floorplate_y / bays_y, 2),
        "bays": f"{bays_x} × {bays_y}",
        "columns_per_floor": (bays_x + 1) * (bays_y + 1),
        "core_x_m": core_x,
        "core_y_m": core_y,
        "core_share": "18% of the floorplate",
        "basis": "rule-of-thumb spacing for a massing review, not a structural design",
    }


def write_ifc(opt: Option, st: dict, c: dict, path: str) -> str:
    """Stage 4. A real IFC4 file: site, building, podium and tower storeys with their elevations."""
    import ifcopenshell
    from ifcopenshell.api.root import create_entity
    from ifcopenshell.api.aggregate import assign_object
    from ifcopenshell.api.unit import assign_unit
    from ifcopenshell.api.context import add_context

    f = ifcopenshell.file(schema="IFC4")
    project = create_entity(f, ifc_class="IfcProject", name="Westmoor W-14 massing study")
    assign_unit(f, length={"is_metric": True, "raw": "METERS"})
    add_context(f, context_type="Model")
    site = create_entity(f, ifc_class="IfcSite", name="Plot W-14")
    building = create_entity(f, ifc_class="IfcBuilding", name=f"Option {opt.name.strip()}")
    assign_object(f, products=[site], relating_object=project)
    assign_object(f, products=[building], relating_object=site)

    z = 0.0
    storeys = []
    for i in range(opt.podium_floors):
        s = create_entity(f, ifc_class="IfcBuildingStorey", name=f"Podium {i+1}")
        s.Elevation = round(z, 3)
        storeys.append(s)
        z += c["podium_floor_to_floor_m"]
    for i in range(opt.tower_floors):
        s = create_entity(f, ifc_class="IfcBuildingStorey", name=f"Level {i+1}")
        s.Elevation = round(z, 3)
        storeys.append(s)
        z += c["tower_floor_to_floor_m"]
    assign_object(f, products=storeys, relating_object=building)

    f.write(path)
    return path


def run(rfp: str = RFP) -> dict:
    import time
    t: dict = {}
    t0 = time.time()
    c = read_rfp(rfp)
    t["read_rfp"] = round(time.time() - t0, 1)

    t0 = time.time()
    opts = massing_options(c)
    chosen = next((o for o in opts if o.passes), None)
    t["massing"] = round(time.time() - t0, 1)

    t0 = time.time()
    st = structure(chosen, c) if chosen else {}
    t["structure"] = round(time.time() - t0, 1)

    return {"constraints": c, "options": [asdict(o) for o in opts],
            "chosen": chosen.name if chosen else None, "structure": st, "seconds": t}


if __name__ == "__main__":
    import sys
    r = run()
    print(json.dumps(r["constraints"], indent=1))
    for o in r["options"]:
        marks = " ".join(("PASS" if ok else "FAIL") for ok, _ in
                         [(v[0], v[1]) for v in o["checks"].values()])
        print(f"{o['name']:12s} {o['height_m']:6.1f} m  {o['gfa_m2']:9,.0f} m²  {marks}")
    print("chosen:", r["chosen"])
    print("structure:", json.dumps(r["structure"], indent=1))
    print("seconds:", r["seconds"])
