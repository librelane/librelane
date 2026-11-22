# Copyright (c) 2025 LibreLane Contributors
# SPDX-License-Identifier: MIT
{
  lib,
  buildPythonPackage,
  poetry-core,
  fetchPypi,
  httpx2,
  click,
  pyyaml,
  rich,
  pcpp,
  zstd,
  zstandard,
  version ? "3.3.0",
  sha256 ? "sha256-Qp2GnTAoyPhPrlSWyN3Gn1/DwNt8e2yrXIeSCsiVulg=",
}:
buildPythonPackage {
  pname = "ciel";
  inherit version;

  pyproject = true;
  build-system = [ poetry-core ];

  src = fetchPypi {
    pname = "ciel";
    inherit version;
    inherit sha256;
  };
  
  buildInputs = [
    zstd
  ];

  dependencies = [
    httpx2
    click
    pyyaml
    pcpp
    rich
    zstandard
  ];

  pythonImportsCheck = [ "ciel" ];
}
