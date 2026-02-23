{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/release-25.11";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      flake-utils,
      nixpkgs,
      pyproject-nix,
    }:
    let
      project = pyproject-nix.lib.project.loadPyproject { projectRoot = ./.; };
    in
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = (import nixpkgs) { inherit system; };
        python = pkgs.python3.override {
          packageOverrides = final: prev: {
            pandoc = prev.buildPythonPackage rec {
              pname = "pandoc";
              version = "2.4";
              pyproject = true;
              build-system = [ prev.setuptools ];
              propagatedBuildInputs = with prev; [
                plumbum
                ply
              ];
              src = prev.fetchPypi {
                inherit pname version;
                sha256 = "sha256-7NH4y7f0GAxrXbShenwadN9RmZX18Ybvgc5yqcvQ3Zo=";
              };
            };
          };
        };
      in
      {
        formatter = pkgs.nixfmt;

        devShell =
          let
            pythonEnv = python.withPackages (
              project.renderers.withPackages {
                inherit python;
              }
            );
          in
          pkgs.mkShell {
            buildInputs = with pkgs; [
              pandoc
              pythonEnv
              ruff
            ];
          };

        checks = {
          tests =
            let
              pythonEnv = python.withPackages (
                project.renderers.withPackages {
                  inherit python;
                }
              );
            in
            pkgs.runCommand "tests" { buildInputs = [ pythonEnv pkgs.pandoc ]; } ''
              cd ${self}
              python -m unittest discover -s tests
              touch $out
            '';

          ruff = pkgs.runCommand "ruff" { buildInputs = [ pkgs.ruff ]; } ''
            ruff check --no-cache ${self}
            touch $out
          '';
        };

        packages = rec {
          default = gtasks-md;

          gtasks-md =
            let
              attrs = project.renderers.buildPythonPackage { inherit python; };
            in
            python.pkgs.buildPythonApplication (
              attrs
              // {
                makeWrapperArgs = [
                  "--prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.pandoc ]}"
                ];
              }
            );
        };
      }
    );
}
