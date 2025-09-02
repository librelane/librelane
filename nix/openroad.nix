# Copyright 2023-2024 Efabless Corporation
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
  llvmPackages,
  fetchFromGitHub,
  openroad-abc,
  libsForQt5,
  opensta,
  boost186,
  eigen,
  cudd,
  tcl,
  tclreadline,
  python3,
  readline,
  spdlog,
  libffi,
  lemon-graph,
  or-tools_9_14,
  glpk,
  zlib,
  clp,
  cbc,
  re2,
  swig4,
  pkg-config,
  gnumake,
  flex,
  bison,
  buildEnv,
  makeBinaryWrapper,
  cmake,
  ctestCheckHook,
  ninja,
  git,
  gtest,
  # environments,
  openroad,
  buildPythonEnvForInterpreter,
  # top
  rev ? "c47bc3b81431e1ce5f305ab75bad126c3adb2858",
  rev-date ? "2025-09-01",
  sha256 ? "sha256-MtQe6CFFg9aJ3LOVjUZ5zD6QGPHNIV3ebNJhQoLCgSM=",
}: let
  stdenv = llvmPackages.stdenv;
  cmakeFlagsCommon = debug: [
    "-DTCL_LIBRARY=${tcl}/lib/libtcl${stdenv.hostPlatform.extensions.sharedLibrary}"
    "-DTCL_HEADER=${tcl}/include/tcl.h"
    "-DUSE_SYSTEM_BOOST:BOOL=ON"
    "-DCMAKE_CXX_FLAGS=-DBOOST_STACKTRACE_GNU_SOURCE_NOT_REQUIRED=1 -I${eigen}/include/eigen3 ${lib.strings.optionalString debug "-g -O0"}"
    "-DCUDD_LIB=${cudd}/lib/libcudd.a"
  ];
  join_flags = lib.strings.concatMapStrings (x: " \"${x}\" ");
in
  stdenv.mkDerivation (finalAttrs: {
    __structuredAttrs = true; # better serialization; enables spaces in cmakeFlags

    pname = "openroad";
    version = rev-date;

    src = fetchFromGitHub {
      owner = "The-OpenROAD-Project";
      repo = "OpenROAD";
      inherit rev;
      inherit sha256;
    };

    cmakeFlags =
      (cmakeFlagsCommon false)
      ++ [
        "-DUSE_SYSTEM_ABC:BOOL=ON"
        "-DUSE_SYSTEM_OPENSTA:BOOL=ON"
        "-DOPENSTA_HOME=${opensta.dev}"
        "-DABC_LIBRARY=${openroad-abc}/lib/libabc.a"
      ];

    patches = [
    ];

    postPatch = ''
      sed -i "s/GITDIR-NOTFOUND/${rev}/" ./cmake/GetGitRevisionDescription.cmake
      patchShebangs ./etc
    '';

    buildInputs = [
      openroad-abc
      boost186
      eigen
      cudd
      tcl
      python3
      readline
      tclreadline
      spdlog
      libffi
      libsForQt5.qtbase
      libsForQt5.qt5.qtcharts
      llvmPackages.openmp
      llvmPackages.libunwind

      lemon-graph
      opensta
      glpk
      zlib
      clp
      cbc
      gtest

      or-tools_9_14
    ];

    nativeBuildInputs = [
      swig4
      pkg-config
      cmake
      gnumake
      flex
      bison
      ninja
      libsForQt5.wrapQtAppsHook
      llvmPackages.clang-tools
      python3.pkgs.tclint
      ctestCheckHook
    ];

    shellHook = ''
      ord-format-changed() {
        ${git}/bin/git diff --name-only | grep -E '\.(cpp|cc|c|h|hh)$' | xargs clang-format -i -style=file:.clang-format
        ${git}/bin/git diff --name-only | grep -E '\.(tcl)$' | xargs tclfmt --in-place
      }
      alias ord-cmake-nix='cmake -DCMAKE_BUILD_TYPE=Release ${join_flags finalAttrs.cmakeFlags} -G Ninja'
      alias ord-cmake-debug='cmake -DCMAKE_BUILD_TYPE=Debug ${join_flags (cmakeFlagsCommon
        /*
        debug:
        */
        true)} -G Ninja'
      alias ord-cmake-release='cmake -DCMAKE_BUILD_TYPE=Release ${join_flags (cmakeFlagsCommon
        /*
        debug:
        */
        false)} -G Ninja'
    '';

    # it takes 8 billion years set it to true on your own machine to test
    doCheck = false;

    passthru = {
      inherit python3;
      withPythonPackages = buildPythonEnvForInterpreter {
        target = openroad;
        inherit lib;
        inherit buildEnv;
        inherit makeBinaryWrapper;
      };
    };

    meta = {
      description = "OpenROAD's unified application implementing an RTL-to-GDS flow";
      homepage = "https://theopenroadproject.org";
      # OpenROAD code is BSD-licensed, but OpenSTA is GPLv3 licensed,
      # so the combined work is GPLv3
      license = lib.licenses.gpl3Plus;
      platforms = lib.platforms.linux ++ lib.platforms.darwin;
    };
  })
