# Tower Massing Agent — brief to BIM on a Dell Pro Precision GB10

A development brief is written in prose. Getting from it to a massing study that provably meets the planning
constraints is slow, and the numbers are easy to get wrong. This reads the brief with a local model, tests massing
options against the brief's own figures, sizes a structural grid for the one that passes, and writes a real IFC file
for the design review — on the workstation, with the brief never leaving the building.

## Watch it first

The overview video is under [Releases](../../releases).

## What happens, stage by stage

| Stage | What happens | Who stays in charge |
|---|---|---|
| 1. Read the brief | a local model turns the written brief into nine numbered constraints, shown on screen | an architect checks the table before anything is built on it |
| 2. Massing | three options inside the setback envelope, each tested against those constraints | options that fail are shown failing, with the number that failed |
| 3. Structure | a column grid and core are sized for the option that passes | rule-of-thumb sizing for a review, never an engineering design |
| 4. BIM output | an IFC4 file: site, building, storeys with elevations | it opens in the practice's own BIM tool for a real review |

A run against the sample brief (48 × 62 m plot, 120 m cap, 6 m setback, 70% coverage, 42,000 m² required), measured
on the hardware below on 19 November 2026:

```
A  slender    31 floors   120.0 m   27,416 m²   fails: gross floor area not met
B  balanced   31 floors   120.0 m   42,606 m²   passes   <- chosen
C  broad      31 floors   120.0 m   57,734 m²   passes
```

Reading the brief takes about 19 seconds; everything after it takes under a tenth of a second. **Option A failing is
the demo working**, not a fault: it is the check catching an option that does not meet the brief. The agent picks B,
which meets the brief without maxing the envelope, over the overbuilt C.

## Hardware

**Built and run on**

| | |
|---|---|
| Dell system | Dell Pro Precision GB10 |
| GPU | NVIDIA GB10 Grace Blackwell Superchip |
| GPU memory | 128 GB unified LPDDR5x, shared with the CPU |
| CPU | NVIDIA Grace, 20 cores |
| RAM | 128 GB unified LPDDR5x, shared with the GPU |
| Storage | 4 TB SSD |
| Operating system | NVIDIA DGX OS 7 |
| Key software | Ollama serving Qwen3.6, build123d/OpenCascade, IfcOpenShell, Shapely, FastAPI |

The requirement is the system above: a Dell Pro Precision GB10 with 128 GB of unified memory. That is what this
was built and run on, and it is the only configuration it has been measured on. No other system is listed here,
because none has been tested. A smaller local model can be used by changing `MODEL` in
`app/massing.py`.

## What's in this repo

| Path | What it is |
|---|---|
| `app/massing.py` | the four stages: read the brief, generate and test options, size structure, write IFC |
| `app/main.py` | the review sheet the design team looks at, with plan and elevation drawings |
| `record/record.py` | the Playwright script that records a run at 1920×1080 |

## Setup (Linux)

1. Install [Ollama](https://ollama.com) and pull a model: `ollama pull qwen3.6` (about 22 GB).
2. `python3 -m venv venv && ./venv/bin/pip install build123d ifcopenshell shapely fastapi uvicorn`
3. If Ollama is not on `http://127.0.0.1:11534`, change `OLLAMA` at the top of `app/massing.py`.
4. From `app/`: `../venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8803`
5. Open <http://127.0.0.1:8803/>, edit the brief if you like, and press **Run the study**.

Full setup and a run-and-reset runbook are in [SETUP.md](SETUP.md).

The pipeline also runs headless: `../venv/bin/python massing.py` prints the table above.

## Known limits

- **No Rhino.** The workflow this is modelled on drives Rhino, which is Windows-only and licensed. This uses open CAD
  libraries instead. It is not the same software and does not claim to be.
- **No concept sketch is read.** It works from the written brief only.
- **The structural sizing is a rule of thumb** — about 9 m column spacing and a core at 18% of the floorplate, the
  usual range for an office tower of this height. It is for a massing review. It is not an engineering design, it has
  not been checked by an engineer, and nothing may be built from it.
- **The IFC carries the storey structure and elevations**, not full solid geometry for each floor.
- A local model reading a brief can misread it. The constraints table is on screen for exactly that reason: check it.

## A note for anyone building something similar

`(120 - 8.4) / 3.6` evaluates to `30.999999999999996` in binary floating point, so an early version of this silently
dropped the top floor of a tower that fits the height cap exactly. Floor counts and the height check both carry a
small tolerance now. Anything that counts storeys out of a height budget has the same trap.

## Credits

- Independently built by Dell Technologies. Inspired by an NVIDIA multi-application agentic AI workflow; no NVIDIA
  code, assets or footage are used.
- [IfcOpenShell](https://ifcopenshell.org/) (LGPL-3.0), [build123d](https://github.com/gumyr/build123d) (Apache-2.0),
  [Shapely](https://github.com/shapely/shapely) (BSD-3-Clause), [Ollama](https://ollama.com) (MIT). Please star them.
- Qwen3.6 by Alibaba Cloud, under its own licence.
- **Trademarks.** NVIDIA, Grace and Blackwell are trademarks of NVIDIA Corporation; Rhino and Rhinoceros are
  trademarks of Robert McNeel & Associates; Ollama is a trademark of Ollama Inc.; Qwen is a trademark of Alibaba
  Cloud; IFC and buildingSMART are trademarks of buildingSMART International. Their mention here is descriptive. It
  is not an endorsement of Dell Technologies by them, and it is not an endorsement of them by Dell Technologies.
- The sample brief is fictitious; "Westmoor district, plot W-14" is not a real site.

## Support

Logan Lawler, logan.lawler@dell.com

## License

MIT, see [LICENSE](LICENSE). Third-party notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
