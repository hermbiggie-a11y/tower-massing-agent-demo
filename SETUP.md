# Setup and runbook

## Before a demo

1. **Start Ollama** and make sure the model is pulled:
   `ollama serve` (or the container), then `ollama pull qwen3.6` once. It is about 22 GB.
2. **Start the review sheet** from `app/`:
   `../venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8803`
3. **Warm the model** by running the study once before the audience arrives. The first call loads the model and is
   much slower than the 19 seconds quoted; every run after that is representative. `ollama ps` shows it resident.

## Running it

Press **Run the study**. Stage 1 takes about nineteen seconds, because a local model is genuinely reading the brief;
everything after it is effectively instant. Say that out loud rather than filling the silence — the point is that the
slow part is the reading, and the reading happens on the workstation.

Edit the brief to show it is not scripted. Changing the required floor area to 60,000 m² makes option B fail too, and
only the broad option survives. Changing the height cap to 90 m changes every option's floor count.

## Reset between runs

Reload the page. Nothing is kept between runs. IFC files are written to `/tmp/massing-ifc/`; delete them when you
like.

## If something goes wrong

| What you see | What to do |
|---|---|
| Stage 1 never finishes | Ollama is not reachable. Check `OLLAMA` at the top of `app/massing.py` and that `ollama ps` lists the model. |
| "the model did not return JSON" | The local model answered with prose. Run it again; if it keeps happening, the model is too small for the task — use the one named in the README. |
| No option passes | That is a legitimate result for a brief the site cannot satisfy. Show it: it is the check doing its job. Relax a constraint in the brief and run again. |
| The IFC link 404s | The run did not reach stage 4, usually because no option passed. |

## Fallback if the machine will not cooperate

Play the overview video from the release and say plainly that it is a recording. Never present the recording as a
live run.
