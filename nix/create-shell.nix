# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2024 UmbraLogic Technologies LLC
{
  extra-packages ? [ ],
  extra-python-packages ? ps: [ ],
  extra-env ? [ ],
  librelane-plugins ? ps: [ ],
  librelane-extra-python-interpreter-packages ? ps: [ ],
  librelane-extra-yosys-plugins ? [ ],
  include-librelane ? true,
}:
(
  {
    lib,
    git,
    zsh,
    delta,
    gtkwave,
    coreutils,
    graphviz,
    iverilog,
    python3,
    devshell,
  }:
  let
    plugins-resolved = librelane-plugins python3.pkgs;
    plugin-included-tools = lib.lists.flatten (map (n: n.includedTools) plugins-resolved);
    plugin-yosys-plugins = lib.lists.flatten (map (n: n.addedYosysPlugins or [ ]) plugins-resolved);
    librelane' = python3.pkgs.librelane.override {
      extra-python-interpreter-packages = librelane-extra-python-interpreter-packages;
      extra-yosys-plugins = librelane-extra-yosys-plugins ++ plugin-yosys-plugins;
    };
    plugins-overridden = map (p: p.override { librelane = librelane'; }) plugins-resolved;
    plugins-propagatedBuildInputs = lib.lists.flatten (
      map (p: (lib.filter (d: d.pname != "librelane") p.propagatedBuildInputs)) plugins-resolved
    );
    librelane-env = (
      python3.withPackages (
        pp:
        (
          if include-librelane then
            ([ librelane' ] ++ plugins-overridden)
          else
            (librelane'.propagatedBuildInputs ++ plugins-propagatedBuildInputs)
        )
        ++ extra-python-packages pp
      )
    );
    librelane-env-sitepackages = "${librelane-env}/${librelane-env.sitePackages}";
    prompt = ''\[\033[1;32m\][nix-shell:\w]\$\[\033[0m\] '';
    packages = [
      librelane-env

      # Conveniences
      git
      zsh
      delta
      gtkwave
      iverilog
      coreutils
      graphviz
    ]
    ++ extra-packages
    ++ librelane'.includedTools
    ++ plugin-included-tools;
  in
  devshell.mkShell {
    devshell.packages = packages;
    env = [
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
  }
)
