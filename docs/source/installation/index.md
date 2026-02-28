# Installation

There are a number of ways to install LibreLane on your Windows, Mac, or Linux
computer.

## Nix (Best)

Nix is a build system for Linux and macOS allowing for _cachable_ and
_reproducible_ builds, and is the primary build system for LibreLane.

Compared to the other methods, Nix offers:

* **Smaller deltas:** if one tool is updated, you do not need to re-download
  everything, which is not the case with the AppImage and Docker.
* **Dead-simple customization:** You can modify any tool versions and/or any
  LibreLane code and all you need to do is re-invoke `nix-shell`. Nix's smart
  cache-substitution feature will automatically figure out whether your build is
  cached or not, and if not, will automatically attempt to build any tools that
  have been changed.
* **Native Execution on macOS:** LibreLane is built natively for both Intel and
  Apple Silicon-based Macs, unlike the AppImage or Docker which would use a
  Virtual Machine, and thus requires more resources.
  
Because of the advantages afforded by Nix, we recommend trying to install using
Nix. Follow the installation guide here: {ref}`nix-based-installation`.

## AppImage (Easiest)

If you're on Linux or are willing to use the Windows Subsystem for Linux (WSL),
the easiest way to get up and running with LibreLane is by downloading an
[AppImage](https://appimage.org) of LibreLane, which is a single-file download
that requires no further installation, but does not work in certain environments
such as inside Docker containers.

Follow the installation guide here: `doc`{/installation/appimage_installation/index}.

## Docker

Docker containers offer:

* Support for Windows, Mac and Linux on both `x86-64` and `aarch64`.
* **Sandboxing:** A completely different environment for using LibreLane, where
  you can choose which directories to expose to LibreLane.
* **Familiarity:** Users of OpenLane will already have Docker installed.

If both the AppImage and Nix don't work for you for whatever reason, you may
want to try Docker. Follow the installation guide here:
{doc}`/installation/docker_installation/index`.

## Other Options

You may elect to somehow provide the tools yourself. Here is a non-exhaustive
list:

* [Python 3.10 or higher](https://www.python.org/)
* [Yosys](https://yosyshq.net/)
* [OpenROAD](https://github.com/The-OpenROAD-Project/OpenROAD)
* [KLayout](https://klayout.de)
* [Magic](http://opencircuitdesign.com/magic/)
* [Netgen](http://opencircuitdesign.com/netgen/)

However, as the versions will likely not match those packaged with LibreLane,
some incompatibilities may arise, and we will not be able to support them.

```{toctree}
:hidden:
:glob:
:maxdepth: 2

nix_installation/index
appimage_installation/index
docker_installation/index
```
