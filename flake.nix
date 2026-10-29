{
  description = "NixOS packaging of the official Google Antigravity Hub binary with automated daily updates";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
      antigravity-hub = pkgs.callPackage ./package.nix { };
    in
    {
      packages.${system} = {
        default = antigravity-hub;
        antigravity-hub = antigravity-hub;
      };

      formatter.${system} = pkgs.nixfmt;

      checks.${system} = {
        updater =
          pkgs.runCommand "updater-tests"
            {
              nativeBuildInputs = [
                pkgs.python3
                pkgs.ruff
              ];
            }
            ''
              cp -r ${self} source
              chmod -R u+w source
              cd source
              ruff format --check scripts tests
              ruff check scripts tests
              python3 -m unittest discover -s tests -v
              touch $out
            '';

        desktop =
          pkgs.runCommand "desktop-integration"
            {
              nativeBuildInputs = [
                pkgs.python3
                pkgs.desktop-file-utils
              ];
            }
            ''
              python3 ${./scripts/check-desktop.py} ${antigravity-hub}
              touch $out
            '';
      };

      apps.${system}.default = {
        type = "app";
        program = "${antigravity-hub}/bin/antigravity-hub";
        meta.description = "Google Antigravity 2.0 agentic AI coding command center";
      };

      overlays.default = final: prev: {
        antigravity-hub = final.callPackage ./package.nix { };
      };
    };
}
