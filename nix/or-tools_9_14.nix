# Copyright 2024 Efabless Corporation
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
###############################################################################
# ---
# Original license follows:
#
# Copyright (c) 2003-2024 Eelco Dolstra and the Nixpkgs/NixOS contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
{
  abseil-cpp,
  bzip2,
  cbc,
  cmake,
  DarwinTools, # sw_vers
  eigen,
  ensureNewerSourcesForZipFilesHook,
  fetchFromGitHub,
  glpk,
  lib,
  pkg-config,
  protobuf,
  re2,
  stdenv,
  swig,
  unzip,
  zlib,
  highs,
}:
# can't use clang on linux: https://github.com/abseil/abseil-cpp/issues/1747
stdenv.mkDerivation (finalAttrs: {
  pname = "or-tools";
  version = "9.14";

  src = fetchFromGitHub {
    owner = "google";
    repo = "or-tools";
    rev = "v${finalAttrs.version}";
    hash = "sha256-FxKe3uY4L33mavwC2aanji3fY9dPqpkwVqi6PNjovSA=";
  };

  cmakeFlags =
    [
      "-DBUILD_DEPS:BOOL=OFF"
      "-DBUILD_SAMPLES:BOOL=OFF"
      "-DBUILD_EXAMPLES:BOOL=OFF"
      "-DCMAKE_INSTALL_BINDIR=bin"
      "-DCMAKE_INSTALL_INCLUDEDIR=include"
      "-DCMAKE_INSTALL_LIBDIR=lib"
      "-DUSE_GLPK=ON"
      "-DUSE_SCIP=OFF"
      "-DPROTOC_PRG=${protobuf}/bin/protoc"
    ]
    ++ lib.optionals stdenv.hostPlatform.isDarwin ["-DCMAKE_MACOSX_RPATH=OFF"];

  strictDeps = true;

  nativeBuildInputs =
    [
      cmake
      ensureNewerSourcesForZipFilesHook
      pkg-config
      swig
      unzip
    ]
    ++ lib.optionals stdenv.hostPlatform.isDarwin [
      DarwinTools
    ];

  buildInputs = [
    abseil-cpp
    bzip2
    cbc
    eigen
    glpk
    zlib
  ];

  propagatedBuildInputs = [
    abseil-cpp
    protobuf
    re2
    highs
  ];

  env.NIX_CFLAGS_COMPILE = toString [
    # fatal error: 'python/google/protobuf/proto_api.h' file not found
    "-I${protobuf.src}"
  ];

  # some tests fail on linux and hang on darwin
  doCheck = false;

  preCheck = ''
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH''${LD_LIBRARY_PATH:+:}$PWD/lib
  '';

  # This extra configure step prevents the installer from littering
  # $out/bin with sample programs that only really function as tests,
  # and disables the upstream installation of a zipped Python egg that
  # can’t be imported with our Python setup.
  installPhase = ''
    cmake . -DBUILD_EXAMPLES=OFF -DBUILD_PYTHON=OFF -DBUILD_SAMPLES=OFF
    cmake --install .
  '';

  outputs = ["out"];

  meta = {
    homepage = "https://github.com/google/or-tools";
    license = lib.licenses.asl20;
    description = ''
      Google's software suite for combinatorial optimization.
    '';
    mainProgram = "fzn-ortools";
    platforms = lib.platforms.linux ++ lib.platforms.darwin;
  };
})
