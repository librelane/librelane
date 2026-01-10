# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2024 UmbraLogic Technologies LLC
{
  lib,
  fetchurl,
  buildPythonPackage,
  fetchPypi,
  pyyaml,
  setuptools,
  version ? "0.0.2",
  sha256 ? "sha256-iy65VBy+Fq+XsSy9w2+rkqjG9Y/ImL1oZR6Vnn2Okm8=",
}: let
  self = buildPythonPackage {
    pname = "yamlcore";
    inherit version;
    format = "pyproject";

    src = fetchPypi {
      inherit (self) pname version;
      inherit sha256;
    };

    nativeBuildInputs = [
      setuptools
    ];

    meta = with lib; {
      description = "YAML 1.2 Core Schema Support for PyYAML";
      homepage = "https://github.com/perlpunk/pyyaml-core";
      license = licenses.mit;
      inherit (pyyaml.meta) platforms;
    };
  };
in
  self
