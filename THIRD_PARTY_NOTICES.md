# Third-party notices

This demo's own code is Dell's, under the MIT licence in `LICENSE`. It depends on software the customer installs from
PyPI and from Ollama; none of it is redistributed in this repository. Each keeps its own licence and notices.

## IfcOpenShell

<https://ifcopenshell.org/> — **LGPL-3.0-or-later**.

Used through its Python API to write the IFC4 file. Installed by the customer from PyPI; not vendored, not modified.
Because it is used as an unmodified library through its published interface and is not distributed here, this demo's
MIT licence applies to Dell's own code only. Anyone who redistributes IfcOpenShell itself, modified or not, must meet
the LGPL's terms, including making the library's source available.

## build123d

<https://github.com/gumyr/build123d> — **Apache-2.0**. Installed from PyPI by the customer.

```
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
```

It builds on Open CASCADE Technology, which is under the **LGPL-2.1 with an Open CASCADE exception**.

## Shapely

<https://github.com/shapely/shapely> — **BSD-3-Clause**. Installed from PyPI by the customer. It builds on GEOS,
which is **LGPL-2.1**.

## Ollama and Qwen3.6

[Ollama](https://ollama.com) is **MIT**. The **Qwen3.6** model weights are published by Alibaba Cloud under their own
licence and are downloaded by the customer with `ollama pull`. Neither is redistributed here. Read the model licence
before using its output commercially.

## Python packages

FastAPI (MIT), Uvicorn (BSD-3-Clause), Playwright (Apache-2.0). Installed from PyPI by the customer.

## Sample brief

The development brief in `app/massing.py` and on the review sheet is fictitious. "Westmoor district, plot W-14" is not a
real site, and the figures were written for this demo. It is not drawn from any client's project.

## Trademarks

NVIDIA, Grace and Blackwell are trademarks of NVIDIA Corporation. Rhino and Rhinoceros are marks of Robert McNeel &
Associates. Ollama is the mark of Ollama Inc. Qwen is the mark of Alibaba Cloud. IFC and buildingSMART are marks of
buildingSMART International. Their mention here is descriptive and is not an endorsement of Dell Technologies by them,
nor an endorsement of them by Dell Technologies.
