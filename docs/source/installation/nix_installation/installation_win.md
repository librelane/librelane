# Windows 10+

* **Minimum Requirements**
    * Windows 10 version 2004 (Build 19041 and higher)
    * Quad-core CPU running at 2.0 GHz+
    * 8 GiB of RAM
    
* **Recommended**
    * Windows 11
    * 6th Gen Intel® Core CPU or later OR AMD Ryzen™️ 1000-series or later
    * 16 GiB of RAM

```{include} ../wsl/_common.md
:heading-offset: 1
:relative-images:
```

## Installing Nix

```{warning}
Do **not** install Nix using `apt`. The version of Nix offered by `apt` is more
often than not severely out-of-date and may cause issues.
```

To install Nix, you first need to install `curl`:

```console
$ sudo apt-get install -y curl
```

Then install Nix by running the following command:

```console 
$ curl --proto '=https' --tlsv1.2 -fsSL https://artifacts.nixos.org/nix-installer | sh -s -- install --no-confirm --extra-conf "
    extra-substituters = https://nix-cache.fossi-foundation.org
    extra-trusted-public-keys = nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=
"
```

Enter your password if prompted. This should take around 5 minutes.

Make sure to close the Ubuntu terminal after you're done with this step and
start it again.

```{include} _common.md
:heading-offset: 1
```
