# SPDX-License-Identifier: MIT
# FROM: https://raw.githubusercontent.com/NixOS/nixpkgs/cd7b1a25c803cca507e19ceb4cade0616b4ae7b9/pkgs/development/python-modules/httpx2/default.nix
# TO BE REMOVED WHEN WE UPDATE TO NIXOS 26.11
# Copyright (c) 2003-2023 Eelco Dolstra and the Nixpkgs/NixOS contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
{
  lib,
  stdenv,
  buildPythonPackage,
  fetchFromGitHub,

  # build-system
  hatchling,
  hatch-fancy-pypi-readme,

  # dependencies
  h11,
  truststore,

  # optional dependencies
  h2,
  socksio,
  trio,
  anyio,

  # tests
  pytestCheckHook,
  pytest-httpbin,
  pytest-trio,

  # reverse deps
  httpx2,
}:

buildPythonPackage (finalAttrs: {
  pname = "httpcore2";
  version = "2.13.1";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "pydantic";
    repo = "httpx2";
    tag = "v${finalAttrs.version}";
    hash = "sha256-XgjFiSwc4xCyPJcTB/Exh838fUOKsT0JRrha7s70C50=";
  };

  # HACK: just remove uv-dynamic-versioning to save my own sanity
  postPatch = ''
    pushd src/httpcore2
    echo 'VERSION = "${finalAttrs.version}"' > VERSION
    substituteInPlace ./pyproject.toml \
        --replace-fail "source = \"uv-dynamic-versioning\"" "path = \"VERSION\""
    sed -i "/uv-dynamic-versioning/d" ./pyproject.toml
  '';

  build-system = [
    hatchling
    hatch-fancy-pypi-readme
  ];

  dependencies = [
    h11
    truststore
  ];

  optional-dependencies = {
    asyncio = [ anyio ];
    http2 = [ h2 ];
    socks = [ socksio ];
    trio = [ trio ];
  };

  pythonImportsCheck = [
    "httpcore2"
  ];

  preCheck = ''
    popd
  '';

  nativeCheckInputs = [
    pytestCheckHook
    pytest-httpbin
    pytest-trio
  ]
  ++ lib.concatAttrValues finalAttrs.passthru.optional-dependencies;

  pytestFlags = [ "tests/httpcore2" ];

  # Skip tests does not pass: 10ms cancellation-timing test
  disabledTests = lib.optionals stdenv.hostPlatform.isRiscV64 [
    "test_h2_timeout_during_request"
    "test_h2_timeout_during_response"
  ];

  passthru.tests = {
    inherit httpx2;
  };

  __darwinAllowLocalNetworking = true;

  meta = {
    description = "A next generation HTTP client for Python";
    homepage = "https://github.com/pydantic/httpx2";
    changelog = "https://github.com/pydantic/httpx2/blob/${finalAttrs.src.tag}/src/httpcore2/CHANGELOG.md";
    license = lib.licenses.bsd3;
  };
})
