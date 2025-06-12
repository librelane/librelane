!register migration_comparison

# Migrating from OpenLane

LibreLane, having started as OpenLane 2.0, is a complete re-imagining of
OpenLane not just as a simple, somewhat customizable flow, but rather as an
infrastructure that can support innumerable flows.

Being rebuilt from the ground up, there is a small learning curve to adopting
LibreLane. This document aims to help those making the jump.

## Why migrate?

At a minimum, the default flow for LibreLane, named {flow}`Classic`, is
essentially a more robust re-implementation of the OpenLane flow that is still
entirely backwards compatible, with some conveniences:


* Full configuration validation: if you have a typo, it will be caught, and if
  you accidentally provide a string to a number, it will be caught.
* More graceful failures: if the design fails mid-flow, because of a more strict
  separation of concerns, you still have access to metrics and reports from all
  previous steps.
  * In OpenLane, they are all extracted at the end.
* The ability to use command-line flow control options such as `--from`, `--to`,
  `--skip` and `--only`, with the ability to resume from a snapshot of your
  design at certain parts of flows, without worrying about surprises related
  to state variables missing.

```{figure} ./configurable_flow.webp
Writing custom flows and steps using LibreLane
```

Additionally, if you're a more savvy user, a _whole new world_ of possibilities
await with LibreLane. Built around "flows" composed of "steps," LibreLane can
implement hardware flows for ASIC implementation by relying on basic Python
object-oriented programming principles, and this naturally allows you to:

* Write your own step, in Python. For example, create a custom placement step
  for your design using OpenROAD Tcl or Python scripts, or even completely
  custom code.
* Write complex flows with decision-making capabilities, including the ability
  to repeat some steps or even try multiple strategies simultaneously and
  proceed with the best result.
  * You can even do this in a Python Notebook!
* Access a standardized and more formal form of design metrics based on
  {term}`METRICS2.1`.

For example, using a custom LibreLane-based flow, the team over at
[TinyTapeout](https://tinytapeout.com) were able to integrate dozens of tiny
designs together into a complex chip; leveraging custom flows and custom steps
to tape-out a complex chip for ChipIgnite.

## Installation

Like OpenLane, installations of LibreLane include all underlying utilities
for the default flow, including but not limited to; Yosys, OpenROAD, Magic, and
KLayout.

LibreLane uses a deterministic and reproducible environment builder called
[Nix](https://nixos.org) to both build its underlying utilities and distribute
them.

While using a Dockerized environment is still supported, Nix yields a number of
advantages and is overall recommended.

### Nix-based Installation (Recommended)

The Nix method involves installing the Nix build utility/package management
software and cloning the LibreLane repository.

You can install Nix and set up the LibreLane binary cache by following the
instructions at {ref}`nix-based-installation`.

Afterwards, you can run an example as follows:

```{include} ../common/nix_installation/_running_example.md

```

### Docker-based Installation (Not Preferred)

Docker is still supported if you have it installed from OpenLane, although the
Docker image is built with a Nix environment instead of CentOS. The way it is
invoked is also much simpler, with the Python script handling mounts and calling
the image for you, as you can see below:

```!migration_comparison[bash]
git clone https://github.com/The-OpenROAD-Project/LibreLane
make pdk
make mount
./flow.tcl -design spm
---
pip3 install --upgrade librelane
librelane --dockerized --run-example spm
---
This allows you to start the LibreLane environment from anywhere, without having
to rely on a Makefile.
```

```{warning}
`--dockerized` will make your home folder, your PDK root and your current
working directory available to the LibreLane Docker container.

If you need any other directories mounted, you can pass them in the following
manner: `--docker-mount <dir1> [--docker-mount <dir2> [--docker-mount <dir3>]]`.
```

## Designs and Configuration

The first question you may ask is if your existing designs are supported, and
we're happy to say that, for the most part, the answer is yes! LibreLane
supports about 99% of the config files from OpenLane, whether they're written
in JSON or Tcl, although Tcl is finicky at this point and we recommend rewriting
them in JSON.

```{note}
A small caveat is interactive scripts written in Tcl, however, are not supported
in LibreLane- we've replaced them with Python-based flows, which are much
more flexible and stable: you can check out how to write one under
{doc}`/usage/writing_custom_flows`.
```

A very limited number of variables, are a bit more of a pain to migrate. We've
documented them in the following sections for your convenience:

```{toctree}
./variables
```

## Running flows

The command line interface for LibreLane is more streamlined, and entirely
handled by the LibreLane Python module instead of relying on Makefiles.

```!migration_comparison[bash] ### PDK Installation
make pdk
---
---
LibreLane will automatically download and install the default PDK(s) version
using Volare.
```

```{tip}
Don't forget to add `--dockerized` to `librelane` invocations if you're using
the Docker-based installation.
```

```!migration_comparison[bash] ### Installation Smoke-Testing
make test
---
librelane --smoke-test
---
Being built into the command-line interface of LibreLane makes it runnable from
anywhere.
```

```!migration_comparison[bash] ### Running an example design
./flow.tcl -design spm
---
librelane --run-example spm
---
The example designs are now copied to the current working directory before being
run, instead of relying on a global "LibreLane installation" directory.
```

```{tip}
Whenever you don't specify a flow, the {flow}`Classic` flow will be used by
default.
```

```!migration_comparison[bash] ### Running your own design
./flow.tcl ~/my_designs/picorv32
---
librelane [--flow Classic] ~/my_designs/picorv32/config.json
---
We've done away with providing the design folder and automatically trying to
detect which configuration file should be run, instead opting to use the
configuration file automatically.
```

## Outputs

Examining outputs for LibreLane.0+ is very different compared to previous
versions.

### Run Folders

```!migration_comparison[]
runs/<run_tag>
├── OPENLANE_VERSION
├── PDK_SOURCES
├── cmds.log
├── config.tcl
├── config_in.tcl
├── errors.log
├── logs
├── librelane.log
├── reports
├── report.csv
├── results
├── runtime.yaml
├── tmp
└── warnings.log
---
runs/<run_tag>
├── final
├── tmp
├── error.log
├── info.log
├── resolved.json
├── warning.log
├── 01-verilator-lint
├── 02-checker-linttimingconstructs
├── 03-checker-linterrors
├── 04-yosys-jsonheader
├── 05-yosys-synthesis
├── 06-checker-yosysunmappedcells
├── 07-checker-yosyssynthchecks
├── 08-openroad-checksdcfiles
├── 09-openroad-staprepnr
├── 10-openroad-floorplan
├── 11-odb-setpowerconnections
├── 12-odb-manualmacroplacement
├── 13-openroad-cutrows
├── 14-openroad-tapendcapinsertion
├── 15-openroad-globalplacementskipio
⋮
---
For one thing, run folders have been redone entirely: instead of a haphazardly
and and ill-defined set of meta-step folders, each step now has its own folder.

By inspecting a step's folder, you'll find its outputs, including design views,
logs and reports. Each step is only allowed to write within its own step folder,
so to find the LVS report, for example, you'll have to look for the folder
`*-netgen-lvs`.
```

```!migration_comparison[] #### Final Views
./results/final
---
./final
---
Fairly straightforward translation. There may be a number of new views for
LibreLane ≥2.0 runs, but all the views from previous versions should continue
to exist.
```

````!migration_comparison[] #### Final Resolved Configuration
./config.tcl
OPENLANE_VERSION
---
./resolved.json
---
The final resolved configuration after loading defaults, values from the PDK,
the configuration file and any command-line overrides, and also some metadata
such as the flow used and the version of LibreLane.

The generated `resolved.json` is a valid LibreLane configuration file for the
same flow; so you may re-run a flow with the same exact configuration as follows:

```bash
librelane <path to run folder>/resolved.json
```
````

```!migration_comparison[] #### Warning/Error Logs
./errors.log
./warnings.log
---
./error.log
./warnings.log
---
In LibreLane, the error log lacks the level prefix (`[ERROR]`/`[WARNING]`) in
the files themselves.
```

```!migration_comparison[] #### Metrics
./report.csv
---
./final/metrics.csv
./final/metrics.json
---
The CSV table is transposed in comparison to OpenLane, i.e., where the fields
were columns in legacy versions, they have been made into rows into the new
versions, as metrics may vary greatly depending on the flow.

A more computer-friendly JSON representation of the metrics is also available.
```

```!migration_comparison[] ### Timing and Clock Reports
./reports/signoff/*-sta-rcx_<interconnect corner name>/summary.rpt
./reports/signoff/*-sta-rcx_<interconnect corner name>/multi_corner_sta.{checks,min,max,power,skew,summary}.rpt
---
./*-openroad-stapostpnr/summary.rpt
./*-openroad-stapostpnr/<IPVT corner name>/{checks,min,max,power,skew}.rpt
---
One summary table is created for all corners, instead of being grouped by
interconnect corner.

Other reports however are per "IPVT"-(Interconnect, Process, Voltage,
Temperature,) corner.
```

### Viewing Layouts

Instead of relying on an external script similar to OpenLane, LibreLane
implements flows to allow you to load your designs into a number of the GUI
tools included with LibreLane.

```!migration_comparison[bash] #### Opening final GDS in KLayout
python3 ./gui.py --viewer klayout --format gds <path to run folder>
---
librelane [--run-tag <run tag>|--last-run] --flow OpenInKLayout <run folder>/resolved.json
---
Opening in KLayout is implemented as a one-step flow named, well, {flow}`OpenInKLayout`.

LibreLane allows you to run multiple flows in the same run directory, and thus
opening the run in KLayout is just another step. When you do so, the last state
of the design is used as an input, meaning that KLayout will preview the latest
GDS stream-out in the design.
```

```!migration_comparison[bash] #### Opening earlier DEF view in KLayout
python3 ./gui.py --viewer klayout --stage routing --format def <path to run folder>
---
librelane --with-initial-state <run folder>/*-openroad-detailedrouting/state_out.json --flow OpenInKLayout <run folder>/resolved.json
---
For steps of the flow where there is no GDS view yet, {flow}`OpenInKLayout` will
preview the DEF view instead. You can tell LibreLane which state to use
explicitly, where here we've opted for the output state of the detailed routing
step.
```

```!migration_comparison[bash] #### Opening in OpenROAD
python3 ./gui.py --viewer openroad --stage routing --format def <path to run folder>
---
librelane --with-initial-state <run folder>/*-openroad-detailedrouting/state_out.json --flow OpenInOpenROAD <run folder>/resolved.json
---
Similar to KLayout, opening designs in OpenROAD is implemented as a one-step flow
named {flow}`OpenInOpenROAD`. Like with KLayout, you can give it a run folder.
```
