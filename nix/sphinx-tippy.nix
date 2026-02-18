# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023 UmbraLogic Technologies LLC
{
  lib,
  fetchurl,
  buildPythonPackage,
  sphinx,
  beautifulsoup4,
  jinja2,
  requests,
  flit,
  version ? "0.4.1",
  sha256 ? "sha256-nENglralwhDIJnPJp092mZqXXl+hB5rnJYqFM050H3k=",
}:
buildPythonPackage {
  name = "sphinx-tippy";
  inherit version;
  format = "pyproject";

  src = fetchurl {
    url = "https://github.com/sphinx-extensions2/sphinx-tippy/archive/refs/tags/v${version}.tar.gz";
    inherit sha256;
  };

  propagatedBuildInputs = [
    sphinx
    beautifulsoup4
    jinja2
    requests
  ];

  buildInputs = [
    flit
  ];

  meta = with lib; {
    description = "Get rich tool tips in your sphinx documentation!";
    homepage = "https://github.com/sphinx-extensions2/sphinx-tippy";
    license = licenses.mit;
    platforms = platforms.linux ++ platforms.darwin;
  };
}
