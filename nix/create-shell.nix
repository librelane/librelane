# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2024 UmbraLogic Technologies LLC
{
  extra-packages ? [],
  extra-python-packages ? [],
  extra-env ? [],
  librelane-plugins ? [],
  include-librelane ? true,
}: ({
  lib,
  git,
  zsh,
  delta,
  gtkwave,
  coreutils,
  graphviz,
  python3,
  devshell,
}: let
  librelane = python3.pkgs.librelane;
  librelane-env = (
    python3.withPackages (pp:
      (
        if include-librelane
        then [librelane]
        else librelane.propagatedBuildInputs
      )
      ++ extra-python-packages
      ++ librelane-plugins)
  );
  librelane-env-sitepackages = "${librelane-env}/${librelane-env.sitePackages}";
  pluginIncludedTools = lib.lists.flatten (map (n: n.includedTools) librelane-plugins);
  prompt = ''\[\033[1;32m\][nix-shell:\w]\$\[\033[0m\] '';
  packages =
    [
      librelane-env

      # Conveniences
      git
      zsh
      delta
      gtkwave
      coreutils
      graphviz
    ]
    ++ extra-packages
    ++ librelane.includedTools
    ++ pluginIncludedTools;
in
  devshell.mkShell {
    devshell.packages = packages;
    env =
      [
        {
          name = "NIX_PYTHONPATH";
          value = "${librelane-env-sitepackages}";
        }
      ]
      ++ extra-env;
    devshell.interactive.PS1 = {
      text = ''PS1="${prompt}"'';
    };
    motd = "";
  })
