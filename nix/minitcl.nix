# Copyright (c) 2026 LibreLane Contributors
# SPDX-License-Identifier: MIT
{
  lib,
  buildPythonPackage,
  zlib,
  pybind11,
  pybind11-stubgen,
  pytestCheckHook,
  setuptools,
  fetchPypi,
  version ? "9.1.0",
  sha256 ? "sha256-PZ50Gy+U3YeERVGbwTlJnhZtbVuOj0V3cnGe6GFCZaI=",
}:
buildPythonPackage {
  pname = "minitcl";
  inherit version;

  pyproject = true;
  build-system = [ setuptools ];

  src = fetchPypi {
    pname = "minitcl";
    inherit version;
    inherit sha256;
  };

  buildInputs = [
    zlib
    pybind11
    pybind11-stubgen
  ];

  pythonImportsCheck = [ "minitcl" ];

  doCheck = true;
}
