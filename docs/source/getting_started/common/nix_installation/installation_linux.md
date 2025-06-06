# Ubuntu/Other Linux

* **Minimum Requirements**
    * Quad-core CPU running at 2.0 GHz+
    * 8 GiB of RAM
    
* **Recommended Requirements**
    * 6th Gen Intel® Core CPU or later OR AMD Ryzen™️ 1000-series or later
    * 16 GiB of RAM

We will primarily support Ubuntu 20.04+ for LibreLane.

If you're looking to build a virtual machine, we recommend [Ubuntu 22.04](https://releases.ubuntu.com/jammy/).

## Installing Nix

```{warning}
Do **not** install Nix using `apt`. The version of Nix offered by `apt` is more
often than not severely out-of-date and may cause issues.
```

You will need `curl` to install Nix.

To install curl on Ubuntu, simply type in the following in your terminal:

```console
$ sudo apt-get install -y curl
```

After that, simply run this command:

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
