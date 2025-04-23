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
  lib,
  system,
  clangStdenv,
  fetchFromGitHub,
  nix-gitignore,
  # Tools
  klayout,
  libparse,
  magic-vlsi,
  netgen,
  opensta,
  openroad,
  ruby,
  surelog,
  tclFull,
  verilator,
  verilog,
  ciel,
  yosys,
  yosysFull,
  # Python
  buildPythonPackage,
  poetry-core,
  click,
  cloup,
  pyyaml,
  yamlcore,
  rich,
  requests,
  pcpp,
  tkinter,
  lxml,
  deprecated,
  psutil,
  pytestCheckHook,
  pytest-xdist,
  pyfakefs,
  rapidfuzz,
  ioplace-parser,
  semver,
}: let
  yosys-env = (yosys.withPythonPackages.override {target = yosysFull;}) (ps:
    with ps; [
      click
    ]);
  openroad-env = openroad.withPythonPackages (ps:
    with ps; [
      click
      rich
      pyyaml
      ioplace-parser
    ]);
  self = buildPythonPackage {
    pname = "librelane";
    version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).tool.poetry.version;
    format = "pyproject";

    src = nix-gitignore.gitignoreSourcePure ./.gitignore ./.;

    nativeBuildInputs = [
      poetry-core
    ];

    includedTools = [
      opensta
      yosys-env
      openroad-env
      klayout
      netgen
      magic-vlsi
      verilog
      verilator
      tclFull
      surelog
      ruby
    ];

    propagatedBuildInputs =
      [
        # Python
        click
        cloup
        pyyaml
        yamlcore
        rich
        requests
        pcpp
        ciel
        tkinter
        lxml
        deprecated
        libparse
        psutil
        klayout.pymod
        rapidfuzz
        ioplace-parser
        semver
      ]
      ++ self.includedTools;

    doCheck = true;
    checkInputs = [pytestCheckHook pytest-xdist pyfakefs];

    computed_PATH = lib.makeBinPath self.propagatedBuildInputs;

    # Make PATH available to LibreLane subprocesses
    makeWrapperArgs = [
      "--prefix PATH : ${self.computed_PATH}"
    ];

    meta = with lib; {
      description = "Hardware design and implementation infrastructure library and ASIC flow";
      homepage = "https://efabless.com/librelane";
      mainProgram = "librelane";
      license = licenses.asl20;
      platforms = platforms.linux ++ platforms.darwin;
    };
  };
in
  self
