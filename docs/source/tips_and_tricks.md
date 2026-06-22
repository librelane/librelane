# Tips and Tricks
LibreLane is both a complex and powerful tool that is used in many different operating environments. With such
a wide community of users and developers, we (the LibreLane developers) have decided to collect some common
Tips and Tricks for getting the most out of LibreLane in your workflows on this page.

**This is a community-led page**, contributions are welcome and highly encouraged. Join us on the [LibreLane FOSSi
Chat Matrix room](https://matrix.to/#/#librelane:fossi-chat.org) to chat more.

## For users
### Continuous integration
_Contributed by:_ [Mel Young](https://github.com/mlyoung101)

Continuous integration is becoming much more common in chip design, and LibreLane is a great tool for running
this. Using runners based on GitHub Actions (e.g. act, Forgejo Actions, etc), you will often find that
LibreLane truncates the line width to 80 characters, which can make logs unreadable. This is a
[known issue](https://github.com/Textualize/rich/issues/2769) with one of LibreLane's Python dependencies,
`act`.

To fix this, you can set the `COLUMNS` environment variable to something much larger, for example, 120.
To do this in a GitHub Actions-based runner, you can add the following YAML for example:

```yaml
env:
  COLUMNS: 120
```

One of the most powerful features of LibreLane is that it can be reproducibly built with all its dependencies
using Nix. Although most CI runners use Docker, you can still setup Nix and LibreLane inside your CI runners.
The following YAML snippet, in Forgejo Actions syntax, will do that for you:

```yaml
- name: Setup Nix
  uses: https://github.com/cachix/install-nix-action@v31

- name: Configure Nix
  run: |
    echo "extra-substituters = https://nix-cache.fossi-foundation.org" | sudo tee -a /etc/nix/nix.conf;
    echo "extra-trusted-public-keys = nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=" | sudo tee -a /etc/nix/nix.conf;
    cat /etc/nix/nix.conf

- name: Run LibreLane
  run: nix run github:librelane/librelane/main -- --smoke-test
```

## For developers
TBA

## Editing this page
In the LibreLane repository, open `docs/source/tips_and_tricks.md`. Choose the correct section ("For users" or
"For developers") and insert:

```md
### Your tip or trick name
_Contributed by:_ [Your Name](https://github.com/YourNameOnGitHub)

Put your tip or trick here.
```
