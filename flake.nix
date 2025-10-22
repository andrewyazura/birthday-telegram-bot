{
  description = "birthday telegram bot";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, pyproject-nix, uv2nix, pyproject-build-systems, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
      overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

      python = pkgs.python310;
      pythonBase =
        pkgs.callPackage pyproject-nix.build.packages { inherit python; };

      pythonSet = pythonBase.overrideScope (pkgs.lib.composeManyExtensions [
        pyproject-build-systems.overlays.wheel
        overlay
        (final: prev: {
          peewee = prev.peewee.overrideAttrs (old: {
            nativeBuildInputs = (old.nativeBuildInputs or [ ])
              ++ [ final.setuptools final.wheel ];
          });
        })
      ]);
    in {
      devShells.${system}.default = let
        editableOverlay =
          workspace.mkEditablePyprojectOverlay { root = "$REPO_ROOT"; };
        editablePythonSet = pythonSet.overrideScope editableOverlay;

        virtualenv = editablePythonSet.mkVirtualEnv "birthday-bot-dev-env"
          workspace.deps.all;
      in pkgs.mkShell {
        packages = [ virtualenv pkgs.uv ];

        env = {
          UV_NO_SYNC = "1";
          UV_PYTHON = editablePythonSet.python.interpreter;
          UV_PYTHON_DOWNLOADS = "never";
        };

        shellHook = ''
          unset PYTHONPATH
          export REPO_ROOT=$(git rev-parse --show-toplevel)
        '';
      };

      packages.${system} = let
        inherit (pkgs.callPackage pyproject-nix.build.util { }) mkApplication;
      in {
        default = mkApplication {
          venv =
            pythonSet.mkVirtualEnv "birthday-bot-env" workspace.deps.default;
          package = pythonSet."birthday-telegram-bot";
        };
      };

      nixosModules.birthday-bot = { config, pkgs, lib, ... }:
        let cfg = config.services.birthday-bot;
        in {
          options.services.birthday-bot = {
            enable = lib.mkEnableOption "Enable birthday telegram bot";
          };

          config = lib.mkIf config.services.birthday-bot.enable {
            users.users.birthday-bot = {
              description = "birthday telegram bot user";
              isSystemUser = true;
              group = "birthday-bot";
            };

            systemd.services.birthday-telegram-bot = {
              description = "birthday telegram bot service";
              after = [ "network.target" ];
              wants = [ "network-online.target" ];
              wantedBy = [ "multi-user.target" ];

              serviceConfig = {
                User = "birthday-bot";
                Group = "birthday-bot";

                ExecStart =
                  "${pkgs.${system}.birthday-bot-env}/bin/python -m main";

                Type = "simple";
                Restart = "on-failure";
              };
            };
          };
        };
    };
}
