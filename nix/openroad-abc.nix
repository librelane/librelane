# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2024 UmbraLogic Technologies LLC
{
  lib,
  abc-verifier,
  fetchFromGitHub,
  bzip2,
  zlib,
  abc-namespace-name ? "abc",
  rev ? "d527cfab4ad731b767ea0a2be2021d920d3afece",
  rev-date ? "2026-06-16",
  sha256 ? "sha256-LKB+O64nXPN3sR76JzQ6oO8IS5M4AnNdgCSCLe0o7rw=",
}:
abc-verifier.overrideAttrs (
  finalAttrs: previousAttrs: {
    pname = "openroad-abc";
    version = rev-date;

    src = fetchFromGitHub {
      owner = "The-OpenROAD-Project";
      repo = "abc";
      inherit rev;
      inherit sha256;
    };

    patchPhase = ''
      runHook prePatch
      # use system zlib/bzip2
      substituteInPlace Makefile \
        --replace-fail "src/misc/bzlib" "" \
        --replace-fail "src/misc/zlib" ""
      cat <<HD > src/misc/zlib/zlib.h
        #include "misc/util/abc_global.h"
        #include <zlib.h>
      HD
      cat <<HD > src/misc/bzlib/bzlib.h
        #include "misc/util/abc_global.h"
        #include <bzlib.h>
      HD
      sed -Ei '1i LIBS += -lz -lbz2' Makefile
      # utter bazel nonsense
      rm -f BUILD
      runHook postPatch
    '';

    cmakeFlags = [
      "-DREADLINE_FOUND=FALSE"
      "-DABC_USE_SYSTEM_ZLIB:BOOL=ON"
      "-DABC_USE_NAMESPACE=${abc-namespace-name}"
      "-DABC_SKIP_TESTS:BOOL=ON"
      "-DABC_USE_STDINT_H:BOOL=ON"
    ];

    buildInputs = [ bzip2 zlib ];

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

      sed -Ei "/#\s*ifdef ABC_NAMESPACE/i#define ABC_NAMESPACE ${abc-namespace-name}\n" $out/include/misc/util/abc_namespaces.h
    '';

    meta = {
      description = "A tool for squential logic synthesis and formal verification (OpenROAD's Fork)";
      homepage = "https://people.eecs.berkeley.edu/~alanmi/abc";
      license = lib.licenses.mit;
      mainProgram = "abc";
      platforms = with lib.platforms; linux ++ darwin;
    };
  }
)
