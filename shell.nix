{ pkgs ? import <nixpkgs> {} }:

let
  python-pandoc      = with pkgs.python3Packages; buildPythonPackage rec {
    pname                 = "pandoc";
    propagatedBuildInputs = [ plumbum ply ];
    src                   = fetchPypi {
      inherit pname version;
      sha256 = "sha256-53LCxthxFGiUV5go268e/VOOtk/H5x1KazoRoYuu+Q0=";
    };
    version               = "2.3";
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

