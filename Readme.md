<h1 align="center">LibreLane</h1>
<p align="center">
    <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License: Apache 2.0"/></a>
    <a href="https://www.python.org"><img src="https://img.shields.io/badge/Python-3.8-3776AB.svg?style=flat&logo=python&logoColor=white" alt="Python 3.8.1 or higher" /></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: black"/></a>
    <a href="https://mypy-lang.org/"><img src="https://www.mypy-lang.org/static/mypy_badge.svg" alt="Checked with mypy"/></a>
    <a href="https://nixos.org/"><img src="https://img.shields.io/static/v1?logo=nixos&logoColor=white&label=&message=Built%20with%20Nix&color=41439a" alt="Built with Nix"/></a>
</p>
<p align="center">
    <a href="https://colab.research.google.com/github/librelane/librelane/blob/main/notebook.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"></a>
    <a href="https://librelane.readthedocs.io/"><img src="https://readthedocs.org/projects/librelane/badge/?version=latest" alt="Documentation Build Status Badge"/></a>
    <a href="https://fossi-chat.org"><img src="https://img.shields.io/badge/Community-FOSSi%20Chat-1bb378?logo=element" alt="Invite to FOSSi Chat"/></a>
</p>

LibreLane is an ASIC infrastructure library based on several components including
OpenROAD, Yosys, Magic, Netgen, CVC, KLayout and a number of custom scripts for
design exploration and optimization, currently developed and maintained by
members and affiliates of the
[American University in Cairo Open Hardware Lab](https://github.com/aucohl)
under the stewardship of the [FOSSi Foundation](https://fossi-foundation.org).

A reference flow, "Classic", performs all ASIC implementation steps from RTL all
the way down to GDSII.

You can find the documentation
[here](https://librelane.readthedocs.io/en/latest/getting_started/) to get
started. You can discuss LibreLane in the
[FOSSi Chat Matrix Server](https://fossi-chat.org).


## Try it out

You can try LibreLane right in your browser, free-of-charge, using Google
Colaboratory by following
[**this link**](https://colab.research.google.com/github/librelane/librelane/blob/main/notebook.ipynb).

## Installation

You'll need the following:

* Python **3.8.1** or higher with PIP, Venv and Tkinter

### Nix (Recommended)

Works for macOS and Linux (x86-64 and aarch64). Recommended, as it is more
integrated with your filesystem and overall has less upload and download deltas.

See
[Nix-based installation](https://librelane.readthedocs.io/en/latest/getting_started/common/nix_installation/index.html)
in the docs for more info.

### Docker

Works for Windows, macOS and Linux (x86-64 and aarch64).

See
[Docker-based installation](https://librelane.readthedocs.io/en/latest/getting_started/common/docker_installation/index.html)
in the docs for more info.

Do note you'll need to add `--dockerized` right after `librelane` in most CLI
invocations.

### Python-only Installation (Advanced, Not Recommended)

**You'll need to bring your own compiled utilities**, but otherwise, simply
install LibreLane as follows:

```sh
python3 -m pip install --upgrade librelane
```

Python-only installations are presently unsupported and entirely at your own
risk.

## Usage

In the root folder of the repository, you may invoke:

```sh
python3 -m librelane --pdk-root <path/to/pdk> </path/to/config.json>
```

To start with, you can try:

```sh
python3 -m librelane --pdk-root $HOME/.ciel ./designs/spm/config.json
```

## Publication

If you use LibreLane in your research, please cite the following paper.

* M. Shalan and T. Edwards, “Building OpenLANE: A 130nm OpenROAD-based
  Tapeout-Proven Flow: Invited Paper,” *2020 IEEE/ACM International Conference
  On Computer Aided Design (ICCAD)*, San Diego, CA, USA, 2020, pp. 1-6.
  [Paper](https://ieeexplore.ieee.org/document/9256623)

```bibtex
@INPROCEEDINGS{9256623,
  author={Shalan, Mohamed and Edwards, Tim},
  booktitle={2020 IEEE/ACM International Conference On Computer Aided Design (ICCAD)}, 
  title={Building OpenLANE: A 130nm OpenROAD-based Tapeout- Proven Flow : Invited Paper}, 
  year={2020},
  volume={},
  number={},
  pages={1-6},
  doi={}}
```

## License and Legal Info

LibreLane is a trademark of the [FOSSi Foundation](https://fossi-foundation.org).

LibreLane code and binaries are available under
[The Apache License, version 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt).

LibreLane is based on [OpenLane 2](https://github.com/efabless/openlane2)
by Efabless Corporation:

```
Copyright 2022-2025 Efabless Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
``` 
