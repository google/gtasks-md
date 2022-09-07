{ pkgs ? import <nixpkgs> {} }:

let
  python-pandoc      = with pkgs.python3Packages; buildPythonPackage rec {
    pname                 = "pandoc";
    propagatedBuildInputs = [ plumbum ply ];
    src                   = fetchPypi {
      inherit pname version;
      sha256 = "sha256-0GPuJS8nYQEPFs86FJEq2SRRh8JMVvSxrZaW4QT+bh4=";
    };
    version               = "2.2";
  };
  pythonWithPackages = pkgs.python3.withPackages (p: with p; [
    google-api-python-client
    google-auth-httplib2
    google-auth-oauthlib
    python-pandoc
    xdg
  ]);
in pkgs.mkShell {
  buildInputs = with pkgs; [ black pandoc pythonWithPackages ];
  shellHook   = ''
    PYTHONPATH=${pythonWithPackages}/${pythonWithPackages.sitePackages}
  '';
}

