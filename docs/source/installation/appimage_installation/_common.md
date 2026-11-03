# Entering the LibreLane Environment

From your terminal, simply type `~/librelane-devshell-$(uname -m).AppImage`.

Your prompt should now look kind of like this:

```console
[nix-shell:~]$ 
```

That's it! You are now inside the LibreLane environment and can run any of the
included tools.

You can test that LibreLane works correctly by running `librelane --smoke-test`.

# Troubleshooting

## Launching fails with `cannot write uid_map: Operation not permitted`

From our testing, this is usually an issue on Ubuntu. You may unfortunately need
root privileges to enable running the LibreLane AppImage.

First of all, ensure that the `uidmap` package is installed. On Debian-based
distributions (like Ubuntu), that's:

```console
$ sudo apt update
$ sudo apt-get install -y uidmap
```

Furthermore, starting **Ubuntu 24.04**, if AppArmor is enabled, you may need to
take additional steps. First, run the following command:

```console
$ sysctl kernel.apparmor_restrict_unprivileged_userns
```

If the output is `kernel.apparmor_restrict_unprivileged_userns = 1`, you will
need to disable the restriction on unprivileged user namespaces. You can do
this using this one-liner:

```console
$ echo "kernel.apparmor_restrict_unprivileged_userns = 0" | sudo tee /etc/sysctl.d/99-userns.conf && sudo sysctl --system
```

```{include} ../_glibc_locale_issues.md
:heading-offset: 1

```
