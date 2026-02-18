# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2025 UmbraLogic Technologies LLC
{
  flake ? null,
  lib,
  clangStdenv,
  fetchFromGitHub,
  nix-gitignore,
  # Tools
  klayout-app,
  libparse,
  magic-vlsi,
  netgen,
  opensta,
  openroad,
  ruby,
  tcl,
  tclPackages,
  verilator,
  iverilog,
  yosys,
  yosys-sby,
  yosys-eqy,
  yosys-lighter,
  yosys-slang,
  yosys-ghdl,
  # Python
  buildPythonPackage,
  poetry-core,
  ciel,
  click,
  cloup,
  pyyaml,
  yamlcore,
  rich,
  requests,
  tkinter,
  lxml,
  deprecated,
  psutil,
  pytestCheckHook,
  pytest-xdist,
  pyfakefs,
  rapidfuzz,
  semver,
  klayout,
}:
let
  yosys-with-plugins = yosys.withPlugins (
    [
      yosys-sby
      yosys-eqy
      yosys-lighter
      yosys-slang
    ]
    ++ lib.optionals (lib.lists.any (
      el: el == clangStdenv.hostPlatform.system
    ) yosys-ghdl.meta.platforms) [ yosys-ghdl ]
  );
  yosys-env = (yosys.withPythonPackages.override { target = yosys-with-plugins; }) (
    ps: with ps; [ click ]
  );
  openroad-env = openroad.withPythonPackages (
    ps: with ps; [
      click
      rich
      pyyaml
    ]
  );
  self = buildPythonPackage {
    pname = "librelane";
    version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).project.version;
    format = "pyproject";

    src = if (flake != null) then flake else nix-gitignore.gitignoreSourcePure ./.gitignore ./.;

    nativeBuildInputs = [
      poetry-core
    ];

    includedTools = lib.map lib.getBin [
      opensta
      yosys-env
      openroad-env
      netgen
      magic-vlsi
      klayout-app
      iverilog
      verilator
      tcl
      ruby
    ];

    propagatedBuildInputs = self.includedTools;

    dependencies = [
      # Python
      click
      cloup
      pyyaml
      yamlcore
      rich
      requests
      ciel
      tkinter
      lxml
      deprecated
      libparse
      psutil
      klayout
      rapidfuzz
      semver
    ];

    doCheck = true;
    checkInputs = [
      pytestCheckHook
      pytest-xdist
      pyfakefs
    ];

    computed_PATH = lib.makeBinPath self.includedTools;

    # Make PATH available to LibreLane subprocesses
    makeWrapperArgs = [
      "--prefix PATH : ${self.computed_PATH}"
    ];

    meta = {
      description = "Hardware design and implementation infrastructure library and ASIC flow";
      homepage = "https://librelane.org/";
      mainProgram = "librelane";
      license = lib.licenses.asl20;
      platforms = with lib.platforms; linux ++ darwin;
    };
  };
in
self
