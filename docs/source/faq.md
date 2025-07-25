# Frequently-Asked Questions (FAQ)

```{contents}
:local:
:class: this-will-duplicate-information-and-it-is-still-useful-here
```

## General


(faq-whats-librelane)=

### What is LibreLane?

Originally started as version 2.0 of OpenLane, LibreLane is a piece of software
for {term}`ASIC` implementation, initially developed by Efabless Corporation,
but its currently maintained by the same developers at the
[American University in Cairo Open Hardware Lab](https://github.com/aucohl)
under the stewardship of the [FOSSi Foundation](https://fossi-foundation.org).

Version 1.0 of OpenLane was a simple but stable and battle-tested flow, primarily
intended for implementing  designs for Efabless's {term}`MPW` programs.

LibreLane reimagines it as not just a single flow, but as an infrastructure by
which flows can be implemented. An OpenLane 1-compatible flow named "Classic"
exists, but is in beta pending further silicon validation.

(faq-1v2)=

### Should I use OpenLane or LibreLane?

Since the liquidation of Efabless Corporation, the authors of OpenLane have lost
control of the trademark, and OpenLane's original developers currently maintain
LibreLane under the stewardship of the FOSSi Foundation.

OpenLane 1.0 as hosted under
[The OpenROAD Project](https://github.com/The-OpenROAD-Project/OpenLane) is
a super-stable version that was used for countless tapeouts, but we no longer
support it actively.

(faq-librelane-vs-openroad)=

### How is LibreLane different from OpenROAD?

OpenROAD is one of many utilities used by LibreLane, which integrates it and many
other tools in order to achieve a full RTL-to-GDSII flow.

OpenROAD is primarily developed by The OpenROAD Project, which involves many
corporations and academic institutions (primarily the University of California,
San Diego, Parallax Software, and Precision Innovations). LibreLane, on the other
hand, was primarily developed by Efabless Corporation and is currently maintained
by the American University in Cairo, Open Hardware Lab.

(faq-proprietary-pdks)=

### Can I use LibreLane with my (company's) proprietary PDK?

In general, yes, but you would have to create LibreLane configuration files for
said PDK. See {ref}`porting-pdks` for more info.

(faq-silicon-proven)=

### Is LibreLane silicon-proven?

OpenLane 1.0 has been used for countless verified tapeouts, including more or
less every open-source design on the Google MPW shuttles.

LibreLane/OpenLane 2.0 has been silicon-proven in a relatively more limited
capacity, having been used for all [Tiny Tapeout](https://tinytapeout.com) shuttles
since 3.5 and a number of internal tape-outs at Efabless Corporation.

(faq-comparison)=

### Why should I use LibreLane over other open-source RTL-to-GDS-II flows?

| Point of Comparison | [OpenROAD Flow Scripts](https://github.com/The-OpenROAD-Project/OpenROAD-Flow-Scripts) | [SiliconCompiler](https://github.com/siliconcompiler/siliconcompiler) | [OpenLane](https://github.com/The-OpenROAD-Project/OpenLane) | LibreLane |
| - | - | - | - | - |
| Architecture | Monolithic | Plugin-based | Monolithic | Plugin-based |
| Configuration | Tcl Files | Python Files | JSON/Tcl Files | JSON/Tcl/Python Files |
| Programming Language | GNU Make | Python | Tcl | Type-checked Python |
| Maintainer | The OpenROAD Project | ZeroASIC | Efabless | AUCOHL |
| Dependencies | Separate (Build Scripts) | Separate (Build Scripts) | Bundled | Bundled  |
| Cloud Service | No | Yes | No | No (Planned) |
| Proprietary Tool Support | No | Yes | No | Yes (with Plugins) |
| Pre-built Binaries | `.deb` (x86-64) | N/A | Docker (x86-64, ARM64) | * Natively through [Nix](https://nixos.org): Linux and macOS (x86-64, ARM64) <br /> * Docker (x86-64, ARM64)|
| Open-Source PDK Support | `sky130`, `gf180mcu`, `nangate45`, `asap7`| `sky130`, `gf180mcu`, `asap7` | `sky130`, `gf180mcu` | `sky130`, `gf180mcu` |
| Community Examples | Limited | Limited | 9+ public multi-project wafer shuttles with Efabless | Backwards Compatible with OL Examples |

## Setup

(faq-wsl)=

### Why does running LibreLane on Windows require the Windows Subsystem for Linux (WSL)?

In short, a lot of the open-source EDA tools LibreLane relies on presume a
Linux-based environment, so they would be non-trivial to port to Windows as we'd
have to make sure every tool both compiles *and* behaves as expected on Windows.

(faq-nix)=

### Why do you use Nix?

{term}`Nix` allows us to create a near-perfectly reproducible environment on
macOS and all Linux distributions with just a single set of scripts, and the
rich community ecosystem surrounding it also enables us to distribute these
environments in their entirety to end-users.

Similar to Docker, this mostly eliminates variables related to the user's
environment, although unlike Docker, it maintains integration with the user's
filesystem, doesn't add a virtualization penalty on macOS, and does not require
the entire image to be re-downloaded every time an update occurs.
