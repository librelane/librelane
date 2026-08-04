# macOS 15+

```{note}
Earlier versions of macOS may work, but they are not officially supported.

The first version of LibreLane in 2027 will drop support for Intel-based Macs as
[NixOS will no longer support the platform](https://nixos.org/blog/announcements/2026/nixos-2605/#deprecation-of-x86_64-darwin).

If you would like to continue using new versions of LibreLane on your
Intel-based Mac, you have two options:
* Using a virtual machine solution of some kind (We recommend
  [lima](https://lima-vm.io)) and following
  [Linux installation instructions](./installation_linux.md)
* Using Docker as per {doc}`/installation/docker_installation/index`
```

* **Minimum Requirements**
    * macOS 15 (Sequoia)
    * 4th Gen Intel® Core CPU or later
    * 8 GiB of RAM
    
* **Recommended**
    * macOS 15 (Sequoia)
    * Apple M1 or later
    * 16 GiB of RAM

## Installing Nix

Simply run this (entire) command in `Terminal.app`:

```console
$ curl --proto '=https' --tlsv1.2 -fsSL https://artifacts.nixos.org/nix-installer | sh -s -- install --no-confirm --extra-conf "
    extra-substituters = https://nix-cache.fossi-foundation.org
    extra-trusted-public-keys = nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=
    extra-experimental-features = nix-command flakes
"
```

Enter your password if prompted. This should take around 5 minutes.

Make sure to close all terminals after you're done with this step.

```{include} _common.md
:heading-offset: 1

```
