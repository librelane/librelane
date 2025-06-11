# Installation Overview

LibreLane offers two primary methods of installation: using **Nix** and using
**Docker**.

## Nix (Recommended)

Nix is a build system for Linux and macOS allowing for _cachable_ and
_reproducible_ builds, and is the primary build system for LibreLane.

Compared to the Docker method, Nix offers:

* **Native Execution on macOS:** LibreLane is built natively for both Intel and
  Apple Silicon-based Macs, unlike Docker which uses a Virtual Machine, and
  thus requires more resources.
* **Filesystem integration:** No need to worry about which folders are being
  mounted like in the Docker containers- Nix apps run natively in your userspace.
* **Smaller deltas:** if one tool is updated, you do not need to re-download
  everything, which is not the case with Docker.
* **Dead-simple customization:** You can modify any tool versions and/or any
  LibreLane code and all you need to do is re-invoke `nix-shell`. Nix's smart
  cache-substitution feature will automatically figure out whether your build is
  cached or not, and if not, will automatically attempt to build any tools that
  have been changed.

Because of the advantages afforded by Nix, we recommend trying to install using
Nix first. Follow the installation guide here:
{ref}`nix-based-installation`

## Docker (Alternative)

Docker containers offer:

* Support for Windows, Mac and Linux on both `x86-64` and `aarch64`
* **Sandboxing:** A completely different environment for using LibreLane
* **Familiarity:** Users of previous versions of LibreLane will already have
  Docker installed

If Nix doesn't work for you for whatever reason, you may want to try Docker.
Follow the installation guide here:
[Docker-based Installation](./common/docker_installation/index.md).

## Other Options

You may elect to somehow provide the tools yourself. Here is a non-exhaustive
list:

* [Python 3.8 or higher](https://www.python.org/)
* [Yosys](https://yosyshq.net/)
* [OpenROAD](https://github.com/The-OpenROAD-Project/OpenROAD)
* [KLayout](https://klayout.de)
* [Magic](http://opencircuitdesign.com/magic/)
* [Netgen](http://opencircuitdesign.com/netgen/)

However, as the versions will likely not match those packaged with LibreLane,
some incompatibilities may arise, and we will not be able to support them.
