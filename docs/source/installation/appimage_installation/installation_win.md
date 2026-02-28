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

## Downloading the LibreLane AppImage

Download the latest release from
<https://github.com/librelane/librelane/releases/latest> using your browser.

Most people should download `librelane-devshell-x86_64.AppImage`, but those on
ARM-based computers should download `librelane-devshell-aarch64.AppImage`.

Inside WSL, do the following:

1. Move the downloaded AppImage from the Windows filesystem to the Linux
   filesystem as follows:

    ```console
    $ mv /mnt/c/Users/*/Downloads/librelane-devshell-$(uname -m).AppImage ~
    ```

1. Give execution permissions for the LibreLane AppImage:

    ```console
    $ chmod a+x ~/librelane-devshell-$(uname -m).AppImage
    ```

```{include} _common.md
:heading-offset: 1
```
