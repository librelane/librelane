# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2024 UmbraLogic Technologies LLC
{
  createDockerImage,
  dockerTools,
  system,
  pkgs,
  lib,
  python3,
  librelane,
  git,
  zsh,
  silver-searcher,
  coreutils,
}: let
  # # We're fetchurl-ing this one so we don't want to use a fixed-output derivation
  # # like fetchFromGitHub
  # # See https://nixos.org/manual/nix/stable/language/import-from-derivation
  # nix-docker-image-script = builtins.fetchurl {
  #   url = "https://raw.githubusercontent.com/NixOS/nix/master/docker.nix";
  #   sha256 = "sha256:0kpj0ms09v7ss86cayf3snpsl6pnjgjzk5wcsfp16ggvr2as80ai";
  # };
  librelane-env = python3.withPackages (ps: with ps; [librelane]);
  librelane-env-sitepackages = "${librelane-env}/${librelane-env.sitePackages}";
  librelane-env-bin = "${librelane-env}/bin";
in
  createDockerImage {
    inherit pkgs;
    inherit lib;
    name = "librelane";
    tag = "tmp-${system}";
    extraPkgs = with dockerTools; [
      git
      zsh
      silver-searcher

      librelane-env
    ];
    nixConf = {
      extra-experimental-features = "nix-command flakes repl-flake";
    };
    maxLayers = 2;
    channelURL = "https://nixos.org/channels/nixos-23.11";

    image-created = "now";
    image-extraCommands = ''
      mkdir -p ./etc
      mkdir -p ./tmp
      chmod 1777 ./tmp

      cat <<HEREDOC > ./etc/zshrc
      autoload -U compinit && compinit
      autoload -U promptinit && promptinit && prompt suse && setopt prompt_sp
      autoload -U colors && colors

      export PS1=$'%{\033[31m%}LibreLane Container (${librelane.version})%{\033[0m%}:%{\033[32m%}%~%{\033[0m%}%% ';
      HEREDOC
    '';
    image-config-cmd = ["${zsh}/bin/zsh"];
    image-config-extra-env = [
      "LANG=C.UTF-8"
      "LC_ALL=C.UTF-8"
      "LC_CTYPE=C.UTF-8"
      "EDITOR=nvim"
      "NIX_PYTHONPATH=/host_librelane:${librelane-env-sitepackages}"
      "TMPDIR=/tmp"
    ];
    image-config-extra-path = [
      "${librelane-env-bin}"
      "${librelane.computed_PATH}"
    ];
  }
