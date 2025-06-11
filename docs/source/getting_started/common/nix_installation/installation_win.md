# Windows 10+

* **Minimum Requirements**
    * Windows 10 version 2004 (Build 19041 and higher)
    * Quad-core CPU running at 2.0 GHz+
    * 8 GiB of RAM
    
* **Recommended**
    * Windows 11
    * 6th Gen Intel® Core CPU or later OR AMD Ryzen™️ 1000-series or later
    * 16 GiB of RAM

## Setting up WSL

1. Follow [official Microsoft documentation for WSL located here](https://docs.microsoft.com/en-us/windows/wsl/install) to install the WSL 2.


```{note}
LibreLane *requires* WSL2. Make sure that you're using Windows 11, or
Windows 10 is up-to-date.
```

1. If you have an installation of WSL2 from 2023 or earlier, follow [Microsoft's official documention to enable `systemd`](https://learn.microsoft.com/en-us/windows/wsl/systemd)
    * `systemd` is enabled by default for installations of WSL2 from mid-2023 or later.

1. Click the Windows icon, type in "Windows PowerShell" and open it.

    ![The Windows 11 Start Menu with "powershell" typed into the search box, showing "Windows PowerShell" as the first match](../wsl/powershell.webp)

1. Install Ubuntu using the following command: `wsl --install -d Ubuntu`

1. Check the version of WSL using following command: `wsl --list --verbose`

    It should produce the following output:

    ```powershell
    PS C:\Users\user> wsl --list --verbose
    NAME                   STATE           VERSION
    * Ubuntu                 Running         2
    ```

1. Launch "Ubuntu" from your Start Menu.

    ![The Windows 11 Start Menu showing a search for the "Ubuntu" app, next to which is a window of the Windows Terminal which opens after clicking it](../wsl/wsl.webp)

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
$ curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install --no-confirm --extra-conf "
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
