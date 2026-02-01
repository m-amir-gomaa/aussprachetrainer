{
  description = "Aussprachetrainer";

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

          nativeBuildInputs = [ 
            pkgs.python311Packages.setuptools 
            pkgs.python311Packages.pybind11
            pkgs.gcc
            pkgs.cmake
            pkgs.pkg-config
          ];

          propagatedBuildInputs = with pkgs.python311Packages; [
            tkinter
            pyttsx3
            gtts
            customtkinter
            numpy
            speechrecognition
            pocketsphinx
            phunspell
            rapidfuzz
            pillow
            onnxruntime
            soundfile
            sounddevice
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
                pkgs.sox
                pkgs.piper-tts
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
          
          # Disable automatic CMake configuration as we handle it manually
          dontUseCmakeConfigure = true;
          
          postInstall = ''
            gcc -shared -o $out/lib/python3.11/site-packages/aussprachetrainer/lib/text_engine.so $src/src/aussprachetrainer/lib/text_engine.c -fPIC
            
            # Build Zep Wrapper manually (avoiding CMake auto-hook issues)
            # Find pybind11 includes
            PYBIND11_INC=$(python3 -c "import pybind11; print(pybind11.get_include())")
            PYTHON_INC=$(python3 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())")
            
            g++ -O3 -Wall -shared -std=c++11 -fPIC \
                -I$PYBIND11_INC -I$PYTHON_INC \
                $src/src/aussprachetrainer/lib/zep_wrapper.cpp \
                -o $out/lib/python3.11/site-packages/aussprachetrainer/zep_vim.so
          '';

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
              python311Packages.phunspell
              python311Packages.rapidfuzz
              python311Packages.pillow
              python311Packages.onnxruntime
              python311Packages.soundfile
              python311Packages.pybind11
              espeak-ng
              mpg123
              portaudio
              pocketsphinx
              piper-tts
              gcc
              gnumake
              cmake
              pkg-config
            ];

            shellHook = ''
              export PYTHONPATH=$PYTHONPATH:$(pwd)/src
              export LD_LIBRARY_PATH=${pkgs.espeak-ng}/lib:${pkgs.portaudio}/lib:${pkgs.piper-tts}/lib:$LD_LIBRARY_PATH
              echo "Aussprachetrainer dev environment loaded."
            '';
        };
      });
}
