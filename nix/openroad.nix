# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2025 UmbraLogic Technologies LLC
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
  yaml-cpp,
  spdlog,
  libffi,
  lemon-graph,
  or-tools_9_14,
  glpk,
  zlib,
  clp,
  cbc,
  re2,
  swig,
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
  darwin,
  # environments,
  openroad,
  buildPythonEnvForInterpreter,
  # top
  rev ? "dfc4f595dfb2e1c346492ff1f0274abb28725acf",
  rev-date ? "2026-01-06",
  sha256 ? "sha256-CVsWiOIYJSei2ur7KPlFu5CfLv3CBhvVSnzoAcKJNhs=",
  # tests tend to time out and fail, esp on Darwin. imperatively it's easy to
  # re-run them but in Nix it starts the long compile all over again.
  enableTesting ? false,
}:
let
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

  cmakeFlags = (cmakeFlagsCommon false) ++ [
    "-DENABLE_TESTS:BOOL=${if enableTesting then "ON" else "OFF"}"
    "-DUSE_SYSTEM_ABC:BOOL=ON"
    "-DUSE_SYSTEM_OPENSTA:BOOL=ON"
    "-DOPENSTA_HOME=${opensta.dev}"
    "-DABC_LIBRARY=${openroad-abc}/lib/libabc.a"
  ];

  postPatch = ''
    substituteInPlace ./cmake/GetGitRevisionDescription.cmake\
      --replace-fail "GITDIR-NOTFOUND" "${rev}"
    patchShebangs ./etc

    sed -i 's@cmake -B@cmake ${join_flags finalAttrs.cmakeFlags} -B@' ./etc/Env.sh
    echo "#!/bin/bash" > ./openroad.build_env_info
    echo "cat << EOF" >> ./openroad.build_env_info
    bash ./etc/Env.sh >> ./openroad.build_env_info
    echo "EOF" >> ./openroad.build_env_info
    chmod +x ./openroad.build_env_info
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
    yaml-cpp

    or-tools_9_14
  ];

  nativeBuildInputs = [
    swig
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
  ]
  ++ lib.optionals stdenv.isDarwin [
    darwin.DarwinTools # sw_vers
  ];

  shellHook = ''
    ord-format-changed() {
      ${git}/bin/git diff --name-only | grep -E '\.(cpp|cc|c|h|hh)$' | xargs clang-format -i -style=file:.clang-format
      ${git}/bin/git diff --name-only | grep -E '\.(tcl)$' | xargs tclfmt --in-place
    }
    alias ord-cmake-nix='cmake -DCMAKE_BUILD_TYPE=Release ${join_flags finalAttrs.cmakeFlags} -G Ninja'
    alias ord-cmake-debug='cmake -DCMAKE_BUILD_TYPE=Debug ${
      join_flags (
        cmakeFlagsCommon
          # debug:
          true
      )
    } -G Ninja'
    alias ord-cmake-release='cmake -DCMAKE_BUILD_TYPE=Release ${
      join_flags (
        cmakeFlagsCommon
          # debug:
          false
      )
    } -G Ninja'
  '';

  postInstall = ''
    cp ../openroad.build_env_info $out/bin/openroad.build_env_info
  '';

  doCheck = enableTesting;

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
