# macOS 11+

* **Minimum Requirements**
    * macOS 11 (Big Sur)
    * 4th Gen Intel® Core CPU or later
    * 8 GiB of RAM
    
* **Recommended**
    * macOS 11 (Big Sur)
    * Apple Silicon CPU
    * 16 GiB of RAM

## Installing Nix

Simply run this (entire) command in `Terminal.app`:

```console
$ curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install --no-confirm --extra-conf "
    extra-substituters = https://librelane.cachix.org
    extra-trusted-public-keys = librelane.cachix.org-1:qqdwh+QMNGmZAuyeQJTH9ErW57OWSvdtuwfBKdS254E=
"
```

Enter your password if prompted. This should take around 5 minutes.

Make sure to close all terminals after you're done with this step.

```{include} _common.md
:heading-offset: 1

```
