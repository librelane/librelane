# Copyright (c) 2025 LibreLane Contributors
# SPDX-License-Identifier: MIT
{
  buildPythonPackage,
  fetchPypi,
  colorama,
  watchdog,
}:
buildPythonPackage rec {
  pname = "py-mon";
  version = "2.1.0";
  format = "wheel";

  src = fetchPypi {
    pname = "py_mon";
    inherit version format;
    sha256 = "sha256-QZOaMd5TBSgTs36W5fcf8jt72EwZsjYyUM3c3M/9bLQ=";
    dist = "py3";
    python = "py3";
  };

  dependencies = [
    colorama
    watchdog
  ];
}
