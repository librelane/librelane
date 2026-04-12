# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2024 UmbraLogic Technologies LLC
{
  lib,
  abc-verifier,
  fetchFromGitHub,
  zlib,
  abc-namespace-name ? "abc",
  rev ? "17cadca080b33edc5a13c8e6e8e8092f8c350b25",
  rev-date ? "2026-03-01",
  sha256 ? "sha256-MZc9YqqpmAJ56ODG19XEo3/NFM+WVOhLz2EboZfQO8Q=",
}:
abc-verifier.overrideAttrs (
  finalAttrs: previousAttrs: {
    name = "openroad-abc";
    version = rev-date;

    src = fetchFromGitHub {
      owner = "The-OpenROAD-Project";
      repo = "abc";
      inherit rev;
      inherit sha256;
    };

    patches = [
      ./patches/openroad-abc/zlib.patch
    ];

    postPatch = ''
      # utter bazel nonsense
      rm -f BUILD
    '';

    cmakeFlags = [
      "-DREADLINE_FOUND=FALSE"
      "-DUSE_SYSTEM_ZLIB:BOOL=ON"
      "-DABC_USE_NAMESPACE=${abc-namespace-name}"
      "-DABC_SKIP_TESTS:BOOL=ON"
      "-DABC_USE_STDINT_H:BOOL=ON"
    ];

    buildInputs = [ zlib ];

    installPhase = ''
      mkdir -p $out/bin
      mv abc $out/bin

      mkdir -p $out/lib
      mv libabc.a $out/lib

      mkdir -p $out/include
      for header in $(find  ../src | grep "\\.h$" | sed "s@../src/@@"); do
      header_tgt=$out/include/$header
      header_dir=$(dirname $header_tgt)
      mkdir -p $header_dir
      cp ../src/$header $header_tgt
      done

      sed -Ei "/#\s*ifdef ABC_NAMESPACE/i#define ABC_NAMESPACE abc\n" $out/include/misc/util/abc_namespaces.h
    '';

    meta = with lib; {
      description = "A tool for squential logic synthesis and formal verification (OpenROAD's Fork)";
      homepage = "https://people.eecs.berkeley.edu/~alanmi/abc";
      license = licenses.mit;
      mainProgram = "abc";
      platforms = platforms.unix;
    };
  }
)
