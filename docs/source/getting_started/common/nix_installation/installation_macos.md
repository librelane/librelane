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
    extra-substituters = https://nix-cache.fossi-foundation.org
    extra-trusted-public-keys = nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=
"
```

Enter your password if prompted. This should take around 5 minutes.

Make sure to close all terminals after you're done with this step.

```{include} _common.md
:heading-offset: 1

```
