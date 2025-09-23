# Copyright 2025 LibreLane Contributors
#
# Adapted from OpenLane
#
# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
{
  description = "open-source infrastructure for implementing chip design flows";

  inputs = {
    nix-eda.url = "github:fossi-foundation/nix-eda/5.3.0";
    ciel.url = "github:fossi-foundation/ciel";
    devshell.url = "github:numtide/devshell";
    flake-compat.url = "https://flakehub.com/f/edolstra/flake-compat/1.tar.gz";
  };

  inputs.ciel.inputs.nix-eda.follows = "nix-eda";
  inputs.devshell.inputs.nixpkgs.follows = "nix-eda/nixpkgs";

  outputs = {
    self,
    nix-eda,
    ciel,
    devshell,
    ...
  }: let
    nixpkgs = nix-eda.inputs.nixpkgs;
    lib = nixpkgs.lib;
  in {
    # Common
    overlays = {
      default = lib.composeManyExtensions [
        (import ./nix/overlay.nix)
        (nix-eda.flakesToOverlay [ciel])
        (
          pkgs': pkgs: let
            callPackage = lib.callPackageWith pkgs';
          in {
            or-tools_9_14 = callPackage ./nix/or-tools_9_14.nix {
              inherit (pkgs'.darwin) DarwinTools;
              stdenv =
                if pkgs'.system == "x86_64-darwin"
                then (pkgs'.overrideSDK pkgs'.stdenv "11.0")
                else pkgs'.stdenv;
            };
            colab-env = callPackage ./nix/colab-env.nix {};
            opensta = callPackage ./nix/opensta.nix {};
            openroad-abc = callPackage ./nix/openroad-abc.nix {};
            openroad = callPackage ./nix/openroad.nix {
              llvmPackages = pkgs'.llvmPackages_18;
            };
          }
        )
        (
          nix-eda.composePythonOverlay (pkgs': pkgs: pypkgs': pypkgs: let
            callPythonPackage = lib.callPackageWith (pkgs' // pypkgs');
          in {
            libparse = callPythonPackage ./nix/libparse.nix {};
            mdformat = pypkgs.mdformat.overridePythonAttrs {
              version = "0.7.18";
              src = pypkgs'.fetchPypi {
                pname = "mdformat";
                version = "0.7.18";
                hash = "sha256-QsuovFprsS1QvffB5HDB+Deoq4zoFXHU5TueYgUfbk8=";
              };

              patches = [
                ./nix/patches/mdformat/donns_tweaks.patch
              ];

              doCheck = false;
            };
            ciel = pkgs.ciel.overrideAttrs (attrs': attrs: {
              buildInputs = attrs.buildInputs ++ [pypkgs'.pythonRelaxDepsHook];
              pythonRelaxDeps = ["rich"];
            });
            sphinx-tippy = callPythonPackage ./nix/sphinx-tippy.nix {};
            sphinx-subfigure = callPythonPackage ./nix/sphinx-subfigure.nix {};
            yamlcore = callPythonPackage ./nix/yamlcore.nix {};

            # ---
            librelane = callPythonPackage ./default.nix {
              flake = self;
            };
          })
        )
        (pkgs': pkgs: let
          callPackage = lib.callPackageWith pkgs';
        in
          {}
          // lib.optionalAttrs pkgs.stdenv.isLinux {
            librelane-docker = callPackage ./nix/docker.nix {
              createDockerImage = nix-eda.createDockerImage;
              librelane = pkgs'.python3.pkgs.librelane;
            };
          })
      ];
    };

    # Helper functions
    createOpenLaneShell = import ./nix/create-shell.nix;

    # Packages
    legacyPackages = nix-eda.forAllSystems (
      system:
        import nix-eda.inputs.nixpkgs {
          inherit system;
          overlays = [devshell.overlays.default nix-eda.overlays.default self.overlays.default];
        }
    );

    packages = nix-eda.forAllSystems (
      system: let
        pkgs = self.legacyPackages."${system}";
      in
        {
          inherit (pkgs) colab-env opensta openroad-abc openroad;
          inherit (pkgs.python3.pkgs) librelane;
          default = pkgs.python3.pkgs.librelane;
        }
        // lib.optionalAttrs pkgs.stdenv.isLinux {
          inherit (pkgs) librelane-docker;
        }
    );

    # dev
    devShells = nix-eda.forAllSystems (
      system: let
        pkgs = self.legacyPackages."${system}";
        callPackage = lib.callPackageWith pkgs;
      in {
        # These devShells are rather unorthodox for Nix devShells in that they
        # include the package itself. For a proper devShell, try .#dev.
        default =
          callPackage (self.createOpenLaneShell {
            }) {};
        notebook = callPackage (self.createOpenLaneShell {
          extra-packages = with pkgs; [
            jupyter
          ];
        }) {};
        # Normal devShells
        dev = callPackage (self.createOpenLaneShell {
          extra-packages = with pkgs; [
            jdupes
            alejandra
          ];
          extra-python-packages = with pkgs.python3.pkgs; [
            pyfakefs
            pytest
            pytest-xdist
            pytest-cov
            pillow
            mdformat
            black
            ipython
            tokenize-rt
            flake8
            mypy
            types-deprecated
            types-pyyaml
            types-psutil
            lxml-stubs
            pipx
          ];
          include-librelane = false;
        }) {};
        docs = callPackage (self.createOpenLaneShell {
          extra-packages = with pkgs; [
            jdupes
            alejandra
            imagemagick
            nodejs.pkgs.nodemon
          ];
          extra-python-packages = with pkgs.python3.pkgs; [
            pyfakefs
            pytest
            pytest-xdist
            pillow
            mdformat
            furo
            docutils
            sphinx
            sphinx-autobuild
            sphinx-autodoc-typehints
            sphinx-design
            myst-parser
            docstring-parser
            sphinx-copybutton
            sphinxcontrib-spelling
            sphinxcontrib-bibtex
            sphinx-tippy
            sphinx-subfigure
          ];
          include-librelane = false;
        }) {};
      }
    );
  };
}
