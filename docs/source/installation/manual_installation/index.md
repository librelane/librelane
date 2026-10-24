# Manual Installation

```{warning}
We do not advise bringing your own tools.

LibreLane is built with certain versions of tools in mind, and using other
versions of tools can introduce instability or break LibreLane's (aspired)
replicability guarantees.
```

At its core, LibreLane is a Python tool that uses a number of binary utilties
over the command line. You may at your own risk elect to provide these binaries
yourself. This document is a non-exhaustive guide on how to do this, and some
common pitfalls.

## Getting LibreLane

Running the LibreLane infrastructure and flows natively requires:

- Either:
  - macOS 11 "Big Sur" or later
  - Linux with either:
    - glibc 2.27 or later
    - musl 1.2 or later
- Python 3.10 or later

  <https://www.python.org/downloads/>

  This translates to Ubuntu 22.04 or later if you're not willing to build from
  source on Linux. macOS includes an out-of-date version by default but it is
  trivial to install other versions via a GUI installer from the link above.

We recommend you use a virtual environment:

```bash
python3.14 -m venv ~librelane-venv 
source ~/librelane-venv/bin/activate
python3.14 -m pip install --upgrade librelane==<VERSION>
librelane --version
```

Then, every time you want to run LibreLane, just:

```bash
source ~/librelane-venv/bin/activate
librelane --version
```

## Getting Tools

You have to build the right versions of tools and make them available in PATH
for the PIP version of LibreLane to consume them.

### Versions

As part of our Nix build system, the "derivations" (at a very high level, build
recipes) store the versions and locations of sources for all the tools.

Starting LibreLane 3.0.17, every GitHub release of LibreLane uploads a
"tool_versions.txt" file. This is a best-effort compilation of the tool versions
LibreLane expects from the Nix data. The file is is in this format:

```
nix-eda 6.11.0 git revision 8f990fb77529c09e540e453cd836af9930ec58db
nixpkgs nixos-25.11 git revision b3aad468604d3e488d627c0b43984eb60e75e782

iverilog s20250103-60-gdb82380ce git revision db82380cecf9943fcc397818e6899b7146442127
klayout 0.30.7 + 2 patches
magic-vlsi 8.3.623 git revision 8.3.623
netgen 1.5.316 git revision 1.5.316
openroad 2026-02-17 git revision dcf36133a369abc8f3c5e5738cd4d82e4903c0e0 + 1 patches
openroad-abc 2026-01-04 git revision 4c756ffb8dff7c583e80c7970d117abd3dfddb5c + 1 patches
opensta 2026-02-14 git revision 857316ff001b2a8dbbdc5996944d08a6d38c87ab + 2 patches
python3 3.13.9 + 3 patches
ruby 3.3.10 + 1 patches
tcl 8.6.16
verilator 5.044 git revision v5.044
yosys 0.62
```

The first section is simply the versions of nixpkgs and nix-eda, which form the
base for LibreLane's build system. The second section is a list of tools
LibreLane uses.

The first is the tool's Nix identifier, the second is its Nix version, the rest
is Git information (if available). We plan to continue improving the script
and Nix derivations to add more information.

You'll note some of them have patches. These patches are sometimes just small
changes to get the source code to compile in Nix, but sometimes they are
backported critical bugfixes from future versions. You can find the patches in
these locations (you may ignore patches for Ruby, Python and Tcl):

- https://github.com/librelane/librelane/tree/<LIBRELANE_VERSION>/nix/patches
- https://github.com/fossi-foundation/nix-eda/tree/<NIX-EDA_VERSION>/nix/patches

Using newer versions and/or using the tools unpatched may work, but may yield
unexpected results.

### General note for macOS

For macOS, getting build systems to recognize the non-system versions of flex,
bison, and tcl-tk is something of a pain. In general, it is advised to add these
exports before doing anything (assuming you're using the
[Homebrew](https://brew.sh) package manager):

```bash
export PATH="$(brew --prefix tcl-tk@8)/bin:$(brew --prefix flex)/bin:$(brew --prefix bison)/bin:$PATH"
export CMAKE_PREFIX_PATH="$(brew --prefix tcl-tk@8):$(brew --prefix flex):$(brew --prefix bison):$CMAKE_PREFIX_PATH"
```

### Python, Ruby, and Tcl

Generally speaking, you are not bound to the versions of these three tools used
by LibreLane, with a couple catches:

- Only Tcl 8.6 is confirmed supported and should be available on all operating
  systems. Tcl 9 should work, but we wouldn't risk it:

  <https://www.tcl-lang.org/software/tcltk/>

- Once again, Python 3.10 or later is required, but you already know that if
  you've read the "Getting LibreLane" section.

  <https://www.python.org/downloads/>

  This translates to Ubuntu 22.04 or later if you're not willing to build from
  source on Linux. macOS includes an out-of-date version by default but it is
  trivial to install other versions via a GUI installer from the link above.

- You need a fairly recent (> 3.0.0) version of Ruby for certain KLayout DR
  scripts:

  <https://www.ruby-lang.org/en/documentation/installation/>

  macOS does include Ruby by default, but it is Ruby 2.X, which is out of date.


### Yosys

Yosys is the primary synthesis tool for LibreLane flows. LibreLane uses the
regular upstream version of Yosys from YosysHQ:

- <https://github.com/YosysHQ/yosys>

However, you **must** compile it with Python interpreter support. To do so, add
the flag `-DYOSYS_ENABLE_PYTHON:BOOL=ON` to your initial CMake invocation.

You can confirm that it works fine by running:

```bash
yosys -qQy /dev/stdin <<EOF
from pyosys import libyosys
print(libyosys.Globals.yosys_version_str)
print("Ok!")
EOF
```

Do note the Yosys Python interpreter must also be able to access the `click`,
`rich`, and `pyyaml` libraries. Depending on how you installed Python, you may
need to install them it using `pip` or your package manager.


```bash
yosys -qQy /dev/stdin <<EOF
import click; import rich; import yaml
print("Ok!")
EOF
```

If you'd like VHDL support, you also need to compile the GHDL Yosys plugin by
following the instructions in the source code. Good luck.

- <https://github.com/ghdl/ghdl-yosys-plugin>

### OpenSTA

OpenSTA is the primary tool for timing signoff used by LibreLane flows.
LibreLane uses **OpenROAD's fork** of OpenSTA.

- <https://github.com/The-OpenROAD-Project/OpenSTA>

You will need the [**CUDD**](https://github.com/cuddorg/cudd) library for this,
which is not available in most major package managers. You may choose to build
it from source, but you may also install it as follows on macOS:

```console
$ brew install silimate/silimate/cudd
```


### OpenROAD

```{note}
Unlike the Nix build setup, there is no need to build OpenROAD ABC separately,
which is done purely to save time on the Nix build.

The build instructions for OpenROAD will vendor in a verified version of abc
as a submodule.
```

OpenROAD, and its internal API, `odb`, is central to most LibreLane flows,
handling most placement-and-routing tasks, as well as parasitics extraction.
Build the upstream version of OpenROAD:

- <https://github.com/The-OpenROAD-Project/OpenROAD>

Check the
[Build OpenROAD](https://github.com/The-OpenROAD-Project/OpenROAD#build-openroad)
section of the Readme for instructions: the LibreLane core team explicitly will
_not_ help with this as it is a complex and time-consuming process.

Do note as with Yosys, OpenROAD must be built with the Python interpreter,
though the build scripts will automatically include the Python interpreter if a
valid installation of Python is found.

```console
$ openroad -exit -python -c 'import openroad; print("Ok!"); exit'
```

Like with Yosys, the Python interpreter must also be able to see the `click`,
`rich`, and `pyyaml` libraries.

```console
$ openroad -exit -python -c 'import click; import rich; import yaml; print("Ok!"); exit'
```

### Magic and Netgen

Magic is the primary streamout and signoff tool for most PDKs compatible with
LibreLane. Netgen is used for both device and transistor-level LVS. LibreLane
uses the upstream versions of both Magic and Netgen:

- <https://github.com/RTimothyEdwards/magic>
- <https://github.com/RTimothyEdwards/netgen>

Depending on how recent your compiler is, you may need to disable a number of
C99 deprecations and warnings when compiling these tools. These flags may be
helpful:

```console
$ CFLAGS="-std=gnu99 -Wno-deprecated-non-prototype -Wno-implicit-function-declaration -Wno-parentheses -Wno-macro-redefined" ./configure
```

Furthermore, on macOS, if you're using Homebrew, you will need to pass tcl and
tk explicitly to `./configure`:

```console
$ ./configure --with-tcl=$(brew --prefix tcl-tk@8) --with-tk=$(brew --prefix tcl-tk@8)
```

### KLayout

KLayout is used as a secondary streamout and signoff tool for redundancy on most
PDKs, and as the primary streamout and signoff tool for some.

The KLayout Python wheels will be automatically installed with the LibreLane
Python package, so ideally you don't need to build it manually.

However, if you intend on using the {flow}`OpenInKLayout` flow, you will need
the KLayout application. We recommend grabbing the binaries from
<https://klayout.de>. It is available for a wide variety of platforms.

### Verilator

Verilator is primarily used as a linter. We recommend following the build
instructions from the documentation.

- <https://verilator.org/guide/latest/install.html#git-install>

### IcarusVerilog

Strictly speaking, IcarusVerilog is not required as it is only currently used
by an optional step ({step}`Yosys.EQY`) that also requires additional plugins.

Nonetheless, it is a useful tool to just have around.

- <https://github.com/steveicarus/iverilog>

## Validating

After building all tools and making sure they are available in PATH, just run:

```console
$ librelane --smoke-test
```

If everything works fine, you've successfully set up LibreLane manually.
