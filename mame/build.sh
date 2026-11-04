#!/bin/bash
# Build MAME 0.285 for the browser (WebAssembly) with only the Super Tank driver.
# 브라우저용 MAME 0.285 빌드 (Super Tank 드라이버만).
#
# Needs: git, python3, make, and the Emscripten SDK (tested with emcc 6.0.13). No root.
#   git clone https://github.com/emscripten-core/emsdk.git && ./emsdk/emsdk install latest && ./emsdk/emsdk activate latest
#   ./build.sh /path/to/emsdk
# Output: mame-src/supertnk.js + supertnk.wasm (copy them to ../docs/mame/).
set -e
EMSDK=${1:?usage: build.sh /path/to/emsdk}
HERE=$(cd "$(dirname "$0")" && pwd)
[ -d "$HERE/mame-src" ] || git clone --depth 1 --branch mame0285 https://github.com/mamedev/mame.git "$HERE/mame-src"
cd "$HERE/mame-src"
# 1) newer Emscripten libc already defines struct _IO_FILE; MAME's own empty definition then clashes
git apply --check "$HERE/sdlprefix.patch" 2>/dev/null && git apply "$HERE/sdlprefix.patch"
source "$EMSDK/emsdk_env.sh" >/dev/null
# 2) MAME passes EXCEPTION_CATCHING_ALLOWED only when compiling; newer Emscripten also needs it when linking,
#    otherwise every C++ exception (MAME throws some during a normal start) aborts the program
CATCH="['_ZN15running_machine17start_all_devicesEv','_ZN12cli_frontend7executeEiPPc','_ZN8chd_file11open_commonEb','_ZN8chd_file13read_metadataEjjRNSt3__212basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEE','_ZN8chd_file13read_metadataEjjRNSt3__26vectorIhNS0_9allocatorIhEEEE','_ZNK19netlist_mame_device19base_validity_checkER16validity_checker']"
export LDFLAGS="-s EXCEPTION_CATCHING_ALLOWED=\"$CATCH\""
emmake make SUBTARGET=supertnk SOURCES=src/mame/videogames/supertnk.cpp WEBASSEMBLY=1 NOWERROR=1 -j"$(nproc)"
ls -la supertnk.js supertnk.wasm
