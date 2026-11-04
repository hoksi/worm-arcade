# Building MAME for the browser

[한국어](README.ko.md)

This folder builds the MAME 0.285 WebAssembly files used by the game page (`docs/mame/supertnk.js` and `supertnk.wasm`). Only the Super Tank driver is compiled, so the build is small and quick.

You only need this if you want to rebuild the emulator. The repository already contains the built files.

## What you need

| | |
| --- | --- |
| OS | Linux or macOS (tested on Ubuntu, x86-64). On Windows, use WSL. |
| Tools | `git`, `python3`, `make`, and a host C compiler (`gcc` or `clang`): MAME first builds its own project generator (GENie) natively |
| Emscripten | the Emscripten SDK (emsdk); tested with `emcc` 6.0.13 |
| Disk | about 4 GB: emsdk 2 GB, MAME source 1.2 GB, build files 0.3 GB |

No administrator rights are needed.

## Steps

### 1. Install Emscripten

```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
cd ..
```

### 2. Build

```bash
mame/build.sh /path/to/emsdk
```

The script:

1. clones MAME at the `mame0285` tag into `mame/mame-src` (shallow clone, about 1.2 GB);
2. applies `sdlprefix.patch`;
3. builds with only `src/mame/videogames/supertnk.cpp`, with the exception-handling list added at link time;
4. prints the size of `mame/mame-src/supertnk.js` and `supertnk.wasm`.

### 3. Use the result

```bash
cp mame/mame-src/supertnk.js mame/mame-src/supertnk.wasm docs/mame/
cd docs && python3 -m http.server 8000     # open http://localhost:8000
```

The page must be served over HTTP; opening `index.html` as a file does not load the `.wasm`. The ROM is not included: choose the `supertnk.zip` you downloaded from mamedev.org on the page.

## The two changes, and why

Building MAME 0.285 as documented ([Compiling MAME → Emscripten](https://docs.mamedev.org/initialsetup/compilingmame.html)) with a current Emscripten fails in two places.

**1. Compile error: `redefinition of '_IO_FILE'`.**
`src/osd/sdl/sdlprefix.h` declares an empty `struct _IO_FILE {};` for Emscripten, because older Emscripten libc left it opaque. Current Emscripten libc defines it, so the two clash. `sdlprefix.patch` comments out that one line.

**2. The game aborts right after start: `Aborted(undefined)` with `__cxa_throw` in the stack.**
MAME throws and catches a few C++ exceptions during a normal start. Its build passes `-s EXCEPTION_CATCHING_ALLOWED=[...]` only when compiling. Current Emscripten also needs it when linking; without it the linker picks a runtime that cannot catch exceptions, and the first throw ends the program. `build.sh` passes the same list in `LDFLAGS`.

If you already built without the second fix, you only need to relink, not recompile:

```bash
cd mame/mame-src
rm -f supertnk.html supertnk.js supertnk.wasm      # the link target is supertnk.html
LDFLAGS='-s EXCEPTION_CATCHING_ALLOWED="[...same list as in build.sh...]"' \
  emmake make SUBTARGET=supertnk SOURCES=src/mame/videogames/supertnk.cpp WEBASSEMBLY=1 NOWERROR=1
```

## Options the page uses

The game page starts MAME with:

```
supertnk -rompath /roms -sound none -skip_gameinfo -norotate -video soft -window -nomax -nokeepaspect -resolution 256x256
```

`-norotate` and `-resolution 256x256` make the canvas exactly the game's raw 256×256 screen, pixel for pixel, so the worm's screen reader (`web/play.js`) sees the same picture as on the desktop. The page then shows a rotated copy for people.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `emmake: command not found` | run `source /path/to/emsdk/emsdk_env.sh`, or pass the emsdk path to `build.sh` |
| `redefinition of '_IO_FILE'` | the patch was not applied: `git -C mame/mame-src apply ../sdlprefix.patch` |
| `Aborted(undefined)` right after "runtime ready" | relink with the `LDFLAGS` line above |
| Make says nothing to do after changing `LDFLAGS` | delete `supertnk.html` (the real link target) and run make again |
| Blank page, `.wasm` 404 or wrong MIME type | serve over HTTP; the server must send `application/wasm` (Python's `http.server` does) |
