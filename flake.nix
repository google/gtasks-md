{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url     = "github:NixOS/nixpkgs/release-23.11";
  };

  outputs = { self, flake-utils, nixpkgs }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs           = (import nixpkgs) { inherit system; };
        python-pandoc  = with pkgs.python3Packages; buildPythonPackage rec {
          pname                 = "pandoc";
          propagatedBuildInputs = [ plumbum ply ];
          src                   = fetchPypi {
            inherit pname version;
            sha256 = "sha256-LfsXvAVGkHbJfB20wIqFIKP3awhuJuMtAf5OQIryroc=";
          };
          version               = "2.4b0";
        };
        pythonWithPkgs = pkgs.python3.withPackages(p: with p; [
          google-api-python-client
          google-auth-httplib2
          google-auth-oauthlib
          python-pandoc
          xdg
        ]);
      in {
        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [ pandoc pyright pythonWithPkgs ruff-lsp ];
          shellHook   = ''
            PYTHONPATH=${pythonWithPkgs}/${pythonWithPkgs.sitePackages}
          '';
        };
      }
    );
}
