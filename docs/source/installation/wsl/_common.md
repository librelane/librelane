# Setting up WSL

1. Follow [official Microsoft documentation for WSL located here](https://docs.microsoft.com/en-us/windows/wsl/install) to install the WSL 2.


```{note}
LibreLane *requires* WSL2. Make sure that you're using Windows 11, or
Windows 10 is up-to-date.
```

1. If you have an installation of WSL2 from 2023 or earlier, follow [Microsoft's official documention to enable `systemd`](https://learn.microsoft.com/en-us/windows/wsl/systemd)
    * `systemd` is enabled by default for installations of WSL2 from mid-2023 or later.

1. Click the Windows icon, type in "Windows PowerShell" and open it.

    ![The Windows 11 Start Menu with "powershell" typed into the search box, showing "Windows PowerShell" as the first match](./powershell.webp)

1. Install Ubuntu using the following command: `wsl --install -d Ubuntu`

1. Check the version of WSL using following command: `wsl --list --verbose`

    It should produce the following output:

    ```powershell
    PS C:\Users\user> wsl --list --verbose
    NAME                   STATE           VERSION
    * Ubuntu                 Running         2
    ```

1. Launch "Ubuntu" from your Start Menu.

    ![The Windows 11 Start Menu showing a search for the "Ubuntu" app, next to which is a window of the Windows Terminal which opens after clicking it](./wsl.webp)
