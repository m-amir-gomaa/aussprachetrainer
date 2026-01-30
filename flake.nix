{
  description = "Aussprachetrainer";

  nixConfig = {
    extra-substituters = [ "https://m-amir-gomaa.cachix.org" ];
    extra-trusted-public-keys = [
      "m-amir-gomaa.cachix.org-1:qbhA4LjeP5gCWsvhqeWOuBWsggC51IJB2gNfdQ6pxrM="
    ];
  };
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in {
        packages.default = pkgs.python311Packages.buildPythonApplication {
          pname = "aussprachetrainer";
          version = "0.1.0";
          src = ./.;
          pyproject = true;

          nativeBuildInputs = [ pkgs.python311Packages.setuptools ];

          propagatedBuildInputs = with pkgs.python311Packages; [
            tkinter
            pyttsx3
            gtts
            customtkinter
            numpy
            speechrecognition
            pocketsphinx
          ];

          makeWrapperArgs = [
            "--prefix PATH : ${
              pkgs.lib.makeBinPath [
                pkgs.espeak-ng
                pkgs.mpg123
                pkgs.portaudio
                pkgs.alsa-utils
                pkgs.pulseaudio
                pkgs.sox
              ]
            }"
            "--prefix LD_LIBRARY_PATH : ${
              pkgs.lib.makeLibraryPath [
                pkgs.espeak-ng
                pkgs.portaudio
                pkgs.libpulseaudio
              ]
            }"
          ];

          # Skip tests since it's a GUI app
          doCheck = false;
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/aussprachetrainer";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python311
            python311Packages.tkinter
            python311Packages.pyttsx3
            python311Packages.gtts
            python311Packages.customtkinter
            python311Packages.numpy
            python311Packages.sounddevice
            python311Packages.speechrecognition
            python311Packages.pocketsphinx
            espeak-ng
            mpg123 # For playing audio from gTTS
            portaudio
            pocketsphinx
          ];

          shellHook = ''
            export PYTHONPATH=$PYTHONPATH:$(pwd)/src
            export LD_LIBRARY_PATH=${pkgs.espeak-ng}/lib:$LD_LIBRARY_PATH
            echo "Aussprachetrainer dev environment loaded."
          '';
        };
      });
}
