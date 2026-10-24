# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2025 UmbraLogic Technologies LLC
{
  lib,
  llvmPackages,
  fetchGitHubSnapshot,
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
  # Compile-time requirements
  cmake,
  ninja,
  git,
  gtest,
  darwin,
  swig,
  pkg-config,
  gnumake,
  flex,
  bison,
  buildEnv,
  makeBinaryWrapper,
  ctestCheckHook,
  tclint,
  # Environments
  openroad,
  buildPythonEnvForInterpreter,
  # top
  rev ? "26Q4",
  rev-date ? "2026-09-29",
  sha256 ? "sha256-iVijS6EMw6tQJo57aajl4xWwtz2EM/IWYQMzkQygH6U=",
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
    "-DCMAKE_CXX_FLAGS=-Wno-deprecated-declarations -DBOOST_STACKTRACE_GNU_SOURCE_NOT_REQUIRED=1 -I${eigen}/include/eigen3 ${lib.strings.optionalString debug "-g -O0"}"
    "-DCUDD_LIB=${cudd}/lib/libcudd.a"
  ];
  join_flags = lib.strings.concatMapStrings (x: " \"${x}\" ");
in
stdenv.mkDerivation (finalAttrs: {
  __structuredAttrs = true; # better serialization; enables spaces in cmakeFlags

  pname = "openroad";
  version = lib.lists.last (lib.sort (a: b: lib.strings.stringLength a > lib.strings.stringLength b) [
    rev
    rev-date
  ]);

  src = fetchGitHubSnapshot {
    owner = "The-OpenROAD-Project";
    repo = "OpenROAD";
    inherit rev;
    hash = sha256;
  };

  cmakeFlags = (cmakeFlagsCommon false) ++ [
    (lib.cmakeBool "ENABLE_TESTS" enableTesting)
    (lib.cmakeBool "USE_SYSTEM_ABC" true)
    (lib.cmakeBool "USE_SYSTEM_OPENSTA" true)
    (lib.cmakeFeature "OPENSTA_INCLUDE_DIR" "${opensta.dev}/include")
    (lib.cmakeFeature "OPENSTA_HOME" "${opensta.dev}")
    (lib.cmakeFeature "ABC_LIBRARY" "${openroad-abc}/lib/libabc.a")
  ];

  postPatch = ''
    substituteInPlace cmake/GetGitRevisionDescription.cmake \
      --replace-fail "GITDIR-NOTFOUND" "${rev}"
    patchShebangs ./etc
    
    substituteInPlace src/drt/CMakeLists.txt \
      --replace-fail "find_package(VTune)" ""

    sed -i 's@cmake -B@cmake ${join_flags finalAttrs.cmakeFlags} -B@' ./etc/Env.sh
    echo "#!/bin/bash" > ./openroad.build_env_info
    echo "cat << EOF" >> ./openroad.build_env_info
    bash ./etc/Env.sh | tee -a ./openroad.build_env_info > /dev/stderr
    echo "EOF" >> ./openroad.build_env_info
    chmod +x ./openroad.build_env_info
  '';

  qt5Libs = with libsForQt5.qt5; [
    qtbase
    qtcharts
    qtsvg
    qtdeclarative
  ];

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
  ]
  ++ finalAttrs.qt5Libs;

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
    tclint
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
