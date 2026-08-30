{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
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
        pythonEnv = pkgs.python3.withPackages (
          project.renderers.withPackages {
            python = pkgs.python3;
          }
        );
      in
      {
        formatter = pkgs.nixfmt;

        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            ruff
          ];
        };

        checks = {
          tests =
            pkgs.runCommand "tests" { buildInputs = [ pythonEnv ]; } ''
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
              attrs = project.renderers.buildPythonPackage { python = pkgs.python3; };
            in
            pkgs.python3.pkgs.buildPythonApplication attrs;
        };
      }
    );
}
