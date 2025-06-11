# CI Documentation

## Components

The LibreLane CI uses Nix and PIP to produce the following components:

* Python Package → Uploaded to [PyPI](https://pypi.org/)
  * Installable via `pip3 install librelane`
* Cached Linux Binaries -> Uploaded to the
  [FOSSi Foundation Nix Cache](https://nix-cache.fossi-foundation.org)
  * Usable by invoking `nix-shell` on the LibreLane repository
  * Derivative: **Docker Image** → Uploaded to [GHCR](https://ghcr.io/)
    * Usable by using the Python package and adding `--dockerized` at the
      beginning of an invocation, no Nix needed
* Cached macOS Binaries -> Uploaded to the
  [FOSSi Foundation Nix Cache](https://nix-cache.fossi-foundation.org)
  * Usable by invoking `nix-shell` on the LibreLane repository

All aforementioned products have their inputs linted for code-standards and have
a smoke-test of some kind run on them before publishing. Additionally, the Python
package build is attempted on all supported Python versions to account for
API breaks (admittedly, the test is not comprehensive.)

## Design Testing

In addition to the products, once the cached Linux binaries are produced, a test
suite involving multiple designs is run using these binaries. A fast (~15-20 minute)
test suite is run on every push and PR, and an extended test suite (~1h30m) is run
nightly.

Failing tests will bar a PR from being merged unless this requirement is waived
by a repository administrator.

```{note}
Do note that a commit pushed to `main` with a new tag, even if it does have
failing design tests, will ultimately still publish a new release. This is done
for several reasons, but chiefly because this gives administrators the discretion
to publish critical fixes even if a couple designs fail.
```
