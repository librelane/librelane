# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
{
  extra-packages ? [],
  extra-python-packages ? ps: [],
  extra-env ? [],
  librelane-plugins ? ps: [],
  librelane-extra-python-interpreter-packages ? ps: [],
  librelane-extra-yosys-plugins ? [],
  include-librelane ? true,
}: ({
  lib,
  git,
  zsh,
  delta,
  gtkwave,
  coreutils,
  graphviz,
  verilog,
  python,
  librelane,
  devshell,
}: let
  plugins-resolved = librelane-plugins python.pkgs;
  plugin-included-tools = lib.lists.flatten (map (n: n.includedTools) plugins-resolved);
  plugin-yosys-plugins = lib.lists.flatten (map (n: n.addedYosysPlugins or []) plugins-resolved);
  librelane' = librelane.override {
    extra-python-interpreter-packages = librelane-extra-python-interpreter-packages;
    extra-yosys-plugins = librelane-extra-yosys-plugins ++ plugin-yosys-plugins;
  };
  plugins-overridden = map (p: p.override {librelane = librelane';}) plugins-resolved;
  plugins-propagatedBuildInputs = lib.lists.flatten (map (p: (lib.filter (d: d.pname != "librelane") p.propagatedBuildInputs)) plugins-resolved);
  librelane-env = (
    python.withPackages (
      pp:
        (
          if include-librelane
          then ([librelane'] ++ plugins-overridden)
          else (librelane'.propagatedBuildInputs ++ plugins-propagatedBuildInputs)
        )
        ++ extra-python-packages pp
    )
  );
  librelane-env-sitepackages = "${librelane-env}/${librelane-env.sitePackages}";
  prompt = ''\[\033[1;32m\][nix-shell:\w]\$\[\033[0m\] '';
  packages =
    [
      librelane-env

      # Conveniences
      git
      zsh
      delta
      gtkwave
      verilog
      coreutils
      graphviz
    ]
    ++ extra-packages
    ++ librelane'.includedTools
    ++ plugin-included-tools;
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
