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
          ps: (project.renderers.withPackages { python = pkgs.python3; } ps) ++ [ ps.mypy ]
        );
      in
      {
        formatter = pkgs.nixfmt;

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            ruff
          ];
        };

        checks = {
          package = self.packages.${system}.default;

          tests = pkgs.runCommand "tests" { buildInputs = [ pythonEnv ]; } ''
            cd ${self}
            python -m unittest discover -s tests
            touch $out
          '';

          ruff = pkgs.runCommand "ruff" { buildInputs = [ pkgs.ruff ]; } ''
            ruff check --no-cache ${self}
            touch $out
          '';

          mypy = pkgs.runCommand "mypy" { buildInputs = [ pythonEnv ]; } ''
            cd ${self}
            MYPY_CACHE_DIR="$TMPDIR/mypy-cache" mypy gtasks_md tests
            touch $out
          '';

          nixfmt = pkgs.runCommand "nixfmt" { buildInputs = [ pkgs.nixfmt ]; } ''
            find ${self} -name '*.nix' -exec nixfmt --check {} +
            touch $out
          '';
        };

        packages = rec {
          default = gtasks-md;

          gtasks-md =
            let
              attrs = project.renderers.buildPythonPackage { python = pkgs.python3; };
            in
            pkgs.python3.pkgs.buildPythonApplication (attrs // { pythonImportsCheck = [ "gtasks_md" ]; });
        };
      }
    );
}
