"""Record the Tower Massing Agent run at 1920x1080. Nothing is faked: the page is driven as a person would drive it,
and the waits are the real time the local model and the CAD step take on the GB10."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8803/"
out = Path(__file__).parent / "out"
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1920, "height": 1080},
                        record_video_dir=str(out), record_video_size={"width": 1920, "height": 1080})
    pg = ctx.new_page()
    pg.goto(URL)
    pg.wait_for_timeout(2500)

    # let the brief be read on screen before anything happens
    pg.hover("#rfp")
    pg.wait_for_timeout(3500)

    pg.click("#go")
    pg.wait_for_timeout(2000)                       # "reading…" is honest dead time, kept short on screen
    pg.wait_for_selector("table", timeout=120000)   # stage 1: the constraints the model pulled out
    pg.wait_for_timeout(5000)

    pg.wait_for_selector(".opt", timeout=120000)    # stage 2: the three options
    pg.wait_for_timeout(1000)
    pg.mouse.wheel(0, 420)
    pg.wait_for_timeout(5500)

    pg.wait_for_selector("svg", timeout=120000)     # stages 3 and 4: drawings, numbers, IFC
    pg.mouse.wheel(0, 460)
    pg.wait_for_timeout(6500)
    pg.mouse.wheel(0, 320)
    pg.wait_for_timeout(5000)

    ctx.close()
    b.close()

vids = sorted(out.glob("*.webm"), key=lambda x: x.stat().st_mtime)
print("recorded:", vids[-1] if vids else "nothing")
