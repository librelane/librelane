# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023 UmbraLogic Technologies LLC
{
  lib,
  fetchurl,
  buildPythonPackage,
  sphinx,
  flit,
  version ? "0.2.4",
  sha256 ? "sha256-LFW8PwoVwftQ8JINvv5ndfsmOhYrX3TgbCGfp/ywINM=",
}:
buildPythonPackage {
  name = "sphinx-subfigure";
  inherit version;
  format = "pyproject";

  src = fetchurl {
    url = "https://github.com/sphinx-extensions2/sphinx-subfigure/archive/refs/tags/v${version}.tar.gz";
    inherit sha256;
  };

  propagatedBuildInputs = [
    sphinx
  ];

  buildInputs = [
    flit
  ];

  meta = with lib; {
    description = "A sphinx extension to create figures with multiple images";
    homepage = "https://github.com/sphinx-extensions2/sphinx-subfigure";
    license = licenses.mit;
    platforms = platforms.linux ++ platforms.darwin;
  };
}
