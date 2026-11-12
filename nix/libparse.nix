# Copyright (c) 2025 LibreLane Contributors
# SPDX-License-Identifier: MIT
{
  lib,
  buildPythonPackage,
  pybind11,
  pytestCheckHook,
  setuptools,
  fetchPypi,
  version ? "0.70.0",
  sha256 ? "sha256-QdeH1noxqaFZ12sV+A+XntLzVzqIR9/B5h4uZUiEGE0=",
}:
buildPythonPackage {
  pname = "libparse";
  inherit version;

  pyproject = true;
  build-system = [ setuptools ];

  src = fetchPypi {
    pname = "lln_libparse";
    inherit version;
    inherit sha256;
  };

  buildInputs = [
    pybind11
  ];

  pythonImportsCheck = [ "libparse" ];

  doCheck = false;
}
