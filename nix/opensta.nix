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
  rev ? "254d0905827ba6129e07f53b682c6ea6de417d3d",
  rev-date ? "2025-10-27",
  sha256 ? "sha256-aLvEw81J4ZVEMYIcgsbdS9x+PedPGreh8+ccdX4i1ms=",
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
