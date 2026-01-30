{
  description = "GermanPronun Minimal - A minimal German pronunciation trainer";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages.default = pkgs.python311Packages.buildPythonApplication {
          pname = "aussprachetrainer";
          version = "0.1.0";
          src = ./.;
          pyproject = true;

          nativeBuildInputs = [
            pkgs.python311Packages.setuptools
          ];

          propagatedBuildInputs = with pkgs.python311Packages; [
            tkinter
            pyttsx3
            gtts
            customtkinter
            numpy
            sounddevice
            speechrecognition
          ];

          makeWrapperArgs = [
            "--prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.espeak-ng pkgs.mpg123 pkgs.portaudio ]}"
            "--prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [ pkgs.espeak-ng pkgs.portaudio ]}"
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
            espeak-ng
            mpg123 # For playing audio from gTTS
            portaudio
          ];

          shellHook = ''
            export PYTHONPATH=$PYTHONPATH:$(pwd)/src
            export LD_LIBRARY_PATH=${pkgs.espeak-ng}/lib:$LD_LIBRARY_PATH
            echo "GermanPronun Minimal dev environment loaded."
          '';
        };
      }
    );
}
