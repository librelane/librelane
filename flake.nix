# SPDX-License-Identifier: MIT
# Copyright (c) 2025 LibreLane Contributors
# Copyright (c) 2023-2025 UmbraLogic Technologies LLC
{
  description = "open-source infrastructure for implementing chip design flows";

  inputs = {
    nix-eda.url = "github:fossi-foundation/nix-eda/6.0.1";
    ciel.url = "github:fossi-foundation/ciel";
    devshell.url = "github:numtide/devshell";
    flake-compat.url = "https://flakehub.com/f/edolstra/flake-compat/1.tar.gz";
  };

  inputs.ciel.inputs.nix-eda.follows = "nix-eda";
  inputs.devshell.inputs.nixpkgs.follows = "nix-eda/nixpkgs";

  outputs =
    {
      self,
      nix-eda,
      ciel,
      devshell,
      ...
    }:
    let
      nixpkgs = nix-eda.inputs.nixpkgs;
      lib = nixpkgs.lib;
    in
    {
      # Common
      overlays = {
        default = lib.composeManyExtensions [
          (ciel.overlays.default)
          (
            pkgs': pkgs:
            let
              callPackage = lib.callPackageWith pkgs';
            in
            {
              or-tools_9_14 = callPackage ./nix/or-tools_9_14.nix {
                inherit (pkgs'.darwin) DarwinTools;
              };
              colab-env = callPackage ./nix/colab-env.nix { };
              opensta = callPackage ./nix/opensta.nix { };
              openroad-abc = callPackage ./nix/openroad-abc.nix { };
              openroad = callPackage ./nix/openroad.nix {
                llvmPackages = pkgs'.llvmPackages_18;
              };
              lemon-graph = pkgs.lemon-graph.overrideAttrs (finalAttrs: previousAttrs: {
                patches = previousAttrs.patches ++ [
                  ./nix/patches/lemon-graph/update_cxx20.patch
                ];
              });
            }
          )
          (nix-eda.composePythonOverlay (
            pkgs': pkgs: pypkgs': pypkgs:
            let
              callPythonPackage = lib.callPackageWith (pkgs' // pypkgs');
            in
            {
              libparse = callPythonPackage ./nix/libparse.nix { };

              # warning with every single click invocation
              cloup = pypkgs.cloup.overridePythonAttrs {
                postPatch = ''
                  substituteInPlace cloup/_util.py \
                    --replace-fail \
                      "tuple(click.__version__.split('.'))" \
                      "tuple('${pypkgs'.click.version}'.split('.'))"
                '';
              };

              # customize mdformat to match style guide
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
              sphinx-tippy = callPythonPackage ./nix/sphinx-tippy.nix { };
              sphinx-subfigure = callPythonPackage ./nix/sphinx-subfigure.nix { };
              yamlcore = callPythonPackage ./nix/yamlcore.nix { };
              py-mon = callPythonPackage ./nix/py-mon.nix { };

              # ---
              librelane = callPythonPackage ./default.nix {
                flake = self;
              };
            }
          ))
          (
            pkgs': pkgs:
            let
              callPackage = lib.callPackageWith pkgs';
            in
            {
              createLibreLaneShell = import ./nix/create-shell.nix;
            }
            // lib.optionalAttrs pkgs.stdenv.isLinux {
              librelane-docker = callPackage ./nix/docker.nix {
                createDockerImage = nix-eda.createDockerImage;
                librelane = pkgs'.python3.pkgs.librelane;
              };
            }
          )
        ];
      };

      # Helper functions

      # Formatters
      formatter = nix-eda.formatter;

      # Packages
      legacyPackages = nix-eda.forAllSystems (
        system:
        import nix-eda.inputs.nixpkgs {
          inherit system;
          overlays = [
            devshell.overlays.default
            nix-eda.overlays.default
            self.overlays.default
          ];
        }
      );

      packages = nix-eda.forAllSystems (
        system:
        let
          pkgs = self.legacyPackages."${system}";
        in
        {
          inherit (pkgs)
            colab-env
            opensta
            openroad-abc
            openroad
            ;
          inherit (pkgs.python3.pkgs) librelane;
          default = pkgs.python3.pkgs.librelane;
        }
        // lib.optionalAttrs pkgs.stdenv.isLinux {
          inherit (pkgs) librelane-docker;
        }
      );

      # Development Shells
      devShells = nix-eda.forAllSystems (
        system:
        let
          pkgs = self.legacyPackages."${system}";
          callPackage = lib.callPackageWith pkgs;
        in
        {
          # These devShells are rather unorthodox for Nix devShells in that they
          # include the package itself. For a proper devShell, try .#dev.
          default = callPackage (pkgs.createLibreLaneShell {
          }) { };
          notebook = callPackage (pkgs.createLibreLaneShell {
            extra-packages = with pkgs; [
              jupyter
            ];
          }) { };
          # Normal devShells
          dev = callPackage (pkgs.createLibreLaneShell {
            extra-packages = with pkgs; [
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
              types-lxml
              pipx
            ];
            include-librelane = false;
          }) { };
          docs = callPackage (pkgs.createLibreLaneShell {
            extra-packages = with pkgs; [
              alejandra
              imagemagick
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
              py-mon
            ];
            include-librelane = false;
          }) { };
        }
      );
    };
}
