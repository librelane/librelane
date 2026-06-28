# Copyright (c) 2025 LibreLane Contributors
# SPDX-License-Identifier: MIT
{
  buildPythonPackage,
  fetchFromGitHub,
  setuptools,
  pyyaml,
  packaging,
  gdstk,
  rich,
}:
buildPythonPackage rec {
  pname = "gdsfill";
  version = "0.1.5-post1";

  pyproject = true;
  build-system = [ setuptools ];

  src = fetchFromGitHub {
    owner = "aesc-silicon";
    repo = "gdsfill";
    rev = "135d482";
    sha256 = "sha256-cfrjDQUp57m3ix6kktgaLbx6PPvZMGkA7QxLDzEu0Qc=";
  };

  dependencies = [
    pyyaml
    packaging
    gdstk
    rich
  ];
}
