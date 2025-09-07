{
  description = "bashdrop: one-shot file transfer using only bash + raw TCP";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        drv  = pkgs.callPackage ./default.nix { };
      in
      {
        packages.default = drv;

        apps.default = {
          type = "app";
          program = "${drv}/bin/bashdrop";
        };

        formatter = pkgs.nixpkgs-fmt;
      });
}
