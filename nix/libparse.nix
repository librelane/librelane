# Copyright (c) 2025 LibreLane Contributors
# SPDX-License-Identifier: MIT
{
  lib,
  buildPythonPackage,
  pybind11,
  pytestCheckHook,
  setuptools,
  fetchPypi,
  version ? "0.56.0",
  sha256 ? "sha256-diJCTDGODfwlOn7oQdKk/f2fvO/QfXuVg0e7/C7N2iw=",
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

  pythonImportsCheck = ["libparse"];

  doCheck = false;
}
