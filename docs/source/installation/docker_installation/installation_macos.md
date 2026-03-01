# macOS 14+

```{note}
macOS 12 and 13 may work, but they are not officially supported.
```

* **Minimum Requirements**
    * macOS 14 (Sonoma)
    * 6th Gen Intel® Core CPU or later
    * 16 GiB of RAM
    
* **Recommended**
    * macOS 14 (Sonoma)
    * Apple Silicon CPU
    * 32 GiB of RAM

## Installing Dependencies

First install [Homebrew](https://brew.sh/) then run script below to install the required packages:

```sh
brew install make python python-tk
brew install --cask docker
```

## Configuring Docker

Under **Preferences** > **Resources** > **File Sharing**, make sure `/Users` is mounted as follows, as using LibreLane with Docker requires access to your home folder.

:::{figure} ./mac_docker_settings.webp
:::

It may also be prudent to enable Full Disk Access permissions for Docker: Under **System Settings** > **Privacy** > **Full Disk Access**, tick Docker as shown:

:::{figure} ./mac_docker_privacy.webp
:::

```{include} _common.md
:heading-offset: 1

```
