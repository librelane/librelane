# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2024 UmbraLogic Technologies LLC
{
  lib,
  clangStdenv,
  fetchFromGitHub,
  swig,
  pkg-config,
  cmake,
  gnumake,
  flex,
  bison,
  tcl,
  tclreadline,
  cudd,
  zlib,
  eigen,
  rev ? "9c9b5659d6a7ecbe02ea1204aa89079a77db1d3e",
  rev-date ? "2025-12-02",
  sha256 ? "sha256-VjIK6puJ9/9yevjRHx7bxyCmFjoH6cW6U3cze052nmo=",
}:
clangStdenv.mkDerivation (finalAttrs: {
  name = "opensta";
  version = rev-date;

  outputs = [
    "out"
    "dev"
  ];

  src = fetchFromGitHub {
    owner = "The-OpenROAD-Project";
    repo = "OpenSTA";
    inherit rev;
    inherit sha256;
  };
  
  postPatch = ''
    # utter bazel nonsense
    rm -f BUILD
  '';

  cmakeFlags = [
    "-DTCL_LIBRARY=${tcl}/lib/libtcl${clangStdenv.hostPlatform.extensions.sharedLibrary}"
    "-DTCL_HEADER=${tcl}/include/tcl.h"
  ];

  buildInputs = [
    cudd
    tclreadline
    eigen
    tcl
    zlib
  ];

  # Files needed by OpenROAD when building with external OpenSTA
  installPhase = ''
    runHook preInstall
    cd ../build
    cmake --install . --prefix $out
    mkdir -p $dev
    mv $out/lib $dev/lib
    for file in $(find ${finalAttrs.src} | grep -v examples | grep -E "(\.tcl|\.i)\$"); do
      relative_dir=$(dirname $(realpath --relative-to=${finalAttrs.src} $file))
      true_dir=$dev/$relative_dir
      mkdir -p $true_dir
      cp $file $true_dir
    done
    for file in $(find ${finalAttrs.src} | grep -v examples | grep -E "(\.hh)\$"); do
      relative_dir=$(dirname $(realpath --relative-to=${finalAttrs.src} $file))
      true_dir=$dev/include/$relative_dir
      mkdir -p $true_dir
      cp $file $true_dir
    done
    find $out
    find $dev
    runHook postInstall
  '';

  nativeBuildInputs = [
    swig
    pkg-config
    cmake
    gnumake
    flex
    bison
  ];

  meta = {
    description = "Gate-level static timing verifier";
    homepage = "https://parallaxsw.com";
    mainProgram = "sta";
    license = lib.licenses.gpl3Plus;
    platforms = with lib.platforms; linux ++ darwin;
  };
})
