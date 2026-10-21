# `warning: setlocale: cannot change locale (en_US.UTF-8)`

This usually indicates either en_US.UTF-8 is missing or the entire locale
archive is missing. For consistency, LibreLane uses the American English UTF-8
locale exclusively.

We are currently investigating a platform-agnostic solution, but in the
meantime, the fix is as follows: The archive is typically located in
`/usr/lib/locale/locale-archive`. If it exists, the fix can be as simple as
`export LOCALE_ARCHIVE=/usr/lib/locale/locale-archive` before starting
LibreLane.

```{note}
Make sure you run any of the commands in this section outside of the LibreLane
environment.
```

You can check if it exists at all using this command:

```console
$ [ -f /usr/lib/locale/locale-archive ] && echo 'Exists' || echo 'Not found'
```

If it either doesn't exist at all or does exist but the error still occurs,
here is how to fix it on some major distributions:

## Fixing missing archive or locale on Debian/Ubuntu

```console
$ sudo dpkg-reconfigure locales
```

Follow the on-screen instructions: make sure `en_US.UTF-8 UTF-8` is checked.

You should also include any locales you use.

After that, `export LOCALE_ARCHIVE=/usr/lib/locale/locale-archive` before
entering the LibreLane environment.

## Fixing missing archive or locale on RHEL derivatives or Fedora

We found that this command works on the latest version of Fedora.

```console
$ sudo localedef --add-to-archive /usr/lib/locale/en_US.utf8
```

After that, `export LOCALE_ARCHIVE=/usr/lib/locale/locale-archive` before
entering the LibreLane environment.
