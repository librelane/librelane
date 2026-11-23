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
  stdenv,
  lib,
  buildPythonPackage,
  fetchFromGitHub,
  isPyPy,
  pythonOlder,

  # build-system
  hatchling,
  hatch-fancy-pypi-readme,

  # dependencies
  anyio,
  certifi,
  httpcore2,
  idna,

  # optional dependencies
  backports-zstd,
  brotli,
  brotlicffi,
  click,
  h2,
  pygments,
  rich,
  socksio,
  wsproto,

  # tests
  chardet,
  pytestCheckHook,
  pytest-trio,
  starlette,
  trustme,
  uvicorn,
  websockets,

  # reverse deps
  httpx2,
}:

buildPythonPackage (finalAttrs: {
  pname = "httpx2";
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
    pushd src/httpx2
    echo 'VERSION = "${finalAttrs.version}"' > VERSION
    substituteInPlace httpx2/_urls.py \
        --replace-fail ", display=True" ""
    substituteInPlace ./pyproject.toml \
        --replace-fail "source = \"uv-dynamic-versioning\"" "path = \"VERSION\"" \
        --replace-fail ", \"uv-dynamic-versioning>=0.14.1\"" "" \
        --replace-fail "tool.hatch.metadata.hooks.uv-dynamic-versioning" "tool.WHO_ASKED"
  '';


  build-system = [
    hatchling
    hatch-fancy-pypi-readme
  ];

  dependencies = [
    anyio
    certifi
    httpcore2
    idna
  ];

  optional-dependencies = {
    brotli = if isPyPy then [ brotlicffi ] else [ brotli ];
    cli = [
      click
      pygments
      rich
    ];
    http2 = [ h2 ];
    socks = [ socksio ];
    ws = [ wsproto ];
    zstd = lib.optionals (pythonOlder "3.14") [ backports-zstd ];
  };

  pythonImportsCheck = [
    "httpx2"
  ];

  preCheck = ''
    popd
  '';

  nativeCheckInputs = [
    chardet
    pytestCheckHook
    pytest-trio
    (starlette.overridePythonAttrs { doCheck = false; })
    trustme
    uvicorn
    websockets
  ]
  ++ lib.concatAttrValues finalAttrs.passthru.optional-dependencies;

  pytestFlags = [ "tests/httpx2" ];

  disabledTests = [
    # network access
    "test_async_proxy_close"
    "test_sync_proxy_close"
    "test_h2_timeout_during_request"
    # uvicorn access logging mismatch
    "test_logging_request"
    "test_logging_redirect_chain"
    # chardet shenanigans (Windows-1252 == WINDOWS-1252 cmp)
    "test_client_decode_text_using_autodetect"
    "test_client_decode_text_using_explicit_encoding"
    "test_response_decode_text_using_autodetect"
    # require newer version of idna
    "test_url_malformed_idna_label_after_ascii_label"
    "test_url_mixed_valid_and_malformed_idna_labels"
  ]
  ++ lib.optionals stdenv.hostPlatform.isDarwin [
    # TODO?
    "test_keepalive_ping"
  ];

  passthru.tests = {
    inherit httpx2;
  };

  __darwinAllowLocalNetworking = true;

  meta = {
    description = "A next generation HTTP client for Python";
    homepage = "https://github.com/pydantic/httpx2";
    changelog = "https://github.com/pydantic/httpx2/blob/${finalAttrs.src.tag}/src/httpx2/CHANGELOG.md";
    license = lib.licenses.bsd3;
  };
})
