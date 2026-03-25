# Linux

* **Minimum Requirements**
    * Quad-core CPU running at 2.0 GHz+
    * 8 GiB of RAM
    
* **Recommended Requirements**
    * 6th Gen Intel® Core CPU or later OR AMD Ryzen™ 1000-series or later
    * 16 GiB of RAM

For Ubuntu, only 22.04 and above are officially supported.

```{include} ../_ubuntu_packages.md
:heading-offset: 1
```

## Downloading the LibreLane AppImage

Download the latest release from
<https://github.com/librelane/librelane/releases/latest> using your browser.

Most people should download `librelane-devshell-x86_64.AppImage`, but those on
ARM-based computers should download `librelane-devshell-aarch64.AppImage`.

In a terminal, do the following:

1. Move the downloaded AppImage to your home directory, e.g.:

    ```console
    $ mv ~/Downloads/librelane-devshell-$(uname -m).AppImage ~
    ```

1. Give execution permissions for the LibreLane AppImage:

    ```console
    $ chmod a+x ~/librelane-devshell-$(uname -m).AppImage
    ```


```{include} _common.md
:heading-offset: 1

```
