{ pkgs ? import <nixpkgs> {} }:

pkgs.stdenvNoCC.mkDerivation {
  pname = "bashdrop";
  version = "0.1.0";

  src = ./.;

  nativeBuildInputs = [ pkgs.python3 ];

  installPhase = ''
    runHook preInstall
    install -Dm755 bashdrop              $out/bin/bashdrop
    install -Dm755 bashdrop-server.py    $out/bin/bashdrop-server.py
    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "One-shot file transfer using only bash and raw TCP";
    license = licenses.mit;
    mainProgram = "bashdrop";
    platforms = platforms.linux ++ platforms.darwin;
  };
}
