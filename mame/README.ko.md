# 브라우저용 MAME 빌드하기

[English](README.md)

이 폴더는 게임 페이지가 쓰는 MAME 0.285 WebAssembly 파일(`docs/mame/supertnk.js`, `supertnk.wasm`)을 만들어요. 슈퍼탱크 드라이버 하나만 넣어서 빌드가 작고 빨라요.

에뮬레이터를 직접 다시 만들고 싶을 때만 필요해요. 저장소에는 이미 빌드한 파일이 들어 있어요.

## 준비물

| | |
| --- | --- |
| 운영체제 | 리눅스 또는 macOS (우분투 x86-64에서 확인). 윈도우는 WSL을 쓰세요. |
| 도구 | `git`, `python3`, `make`, 그리고 컴퓨터용 C 컴파일러(`gcc`나 `clang`). MAME가 빌드 도구(GENie)를 먼저 직접 만들기 때문이에요. |
| Emscripten | Emscripten SDK(emsdk). `emcc` 6.0.13으로 확인했어요. |
| 디스크 | 약 4GB: emsdk 2GB, MAME 소스 1.2GB, 빌드 파일 0.3GB |

관리자 권한(sudo)은 필요 없어요.

## 순서

### 1. Emscripten 설치

```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
cd ..
```

### 2. 빌드

```bash
mame/build.sh /path/to/emsdk
```

스크립트가 하는 일:

1. MAME `mame0285` 태그를 `mame/mame-src`에 내려받아요(최신 기록만, 약 1.2GB).
2. `sdlprefix.patch`를 적용해요.
3. `src/mame/videogames/supertnk.cpp` 하나만 넣어 빌드하고, 예외 처리 목록을 링크 단계에도 넣어요.
4. `mame/mame-src/supertnk.js`와 `supertnk.wasm`의 크기를 보여 줘요.

### 3. 결과물 쓰기

```bash
cp mame/mame-src/supertnk.js mame/mame-src/supertnk.wasm docs/mame/
cd docs && python3 -m http.server 8000     # http://localhost:8000 열기
```

페이지는 HTTP로 열어야 해요. `index.html`을 파일로 바로 열면 `.wasm`을 불러오지 못해요. 롬은 들어 있지 않으니, mamedev.org에서 받은 `supertnk.zip`을 페이지에서 선택하세요.

## 바꾼 두 곳과 이유

MAME 0.285를 [공식 문서](https://docs.mamedev.org/initialsetup/compilingmame.html)대로 최신 Emscripten으로 빌드하면 두 군데서 막혀요.

**1. 컴파일 오류: `redefinition of '_IO_FILE'`**
`src/osd/sdl/sdlprefix.h`가 Emscripten용으로 빈 `struct _IO_FILE {};`를 선언해요. 예전 Emscripten 라이브러리에는 이 정의가 없었기 때문이에요. 지금 Emscripten은 직접 정의하고 있어서 둘이 부딪혀요. `sdlprefix.patch`가 그 한 줄을 막아요.

**2. 게임이 시작하자마자 멈춤: `Aborted(undefined)`, 스택에 `__cxa_throw`**
MAME는 평소 시작 과정에서도 C++ 예외를 몇 번 던지고 받아요. MAME 빌드 설정은 `-s EXCEPTION_CATCHING_ALLOWED=[...]`를 컴파일할 때만 넘겨요. 지금 Emscripten은 링크할 때도 이 설정이 있어야 해요. 없으면 예외를 받을 수 없는 런타임을 골라서, 첫 예외에서 프로그램이 통째로 멈춰요. `build.sh`는 같은 목록을 `LDFLAGS`로 넘겨요.

두 번째 수정 없이 이미 빌드했다면, 다시 컴파일할 필요 없이 링크만 다시 하면 돼요.

```bash
cd mame/mame-src
rm -f supertnk.html supertnk.js supertnk.wasm      # 실제 링크 대상은 supertnk.html
LDFLAGS='-s EXCEPTION_CATCHING_ALLOWED="[...build.sh와 같은 목록...]"' \
  emmake make SUBTARGET=supertnk SOURCES=src/mame/videogames/supertnk.cpp WEBASSEMBLY=1 NOWERROR=1
```

## 페이지가 쓰는 실행 옵션

게임 페이지는 MAME를 이렇게 실행해요.

```
supertnk -rompath /roms -sound none -skip_gameinfo -norotate -video soft -window -nomax -nokeepaspect -resolution 256x256
```

`-norotate`와 `-resolution 256x256`을 쓰면 캔버스가 게임의 원래 256×256 화면과 픽셀 하나까지 같아져요. 그래서 꼬마선충의 화면 해석기(`web/play.js`)가 데스크톱에서와 똑같은 그림을 봐요. 사람에게는 페이지가 회전한 사본을 보여 줘요.

## 문제가 생기면

| 증상 | 해결 |
| --- | --- |
| `emmake: command not found` | `source /path/to/emsdk/emsdk_env.sh`를 실행하거나, `build.sh`에 emsdk 경로를 넘기세요 |
| `redefinition of '_IO_FILE'` | 패치가 적용되지 않았어요: `git -C mame/mame-src apply ../sdlprefix.patch` |
| "runtime ready" 직후 `Aborted(undefined)` | 위의 `LDFLAGS` 줄로 링크를 다시 하세요 |
| `LDFLAGS`를 바꿨는데 make가 할 일이 없다고 함 | 실제 링크 대상인 `supertnk.html`을 지우고 다시 make 하세요 |
| 빈 화면, `.wasm` 404나 MIME 타입 오류 | HTTP로 여세요. 서버가 `application/wasm`으로 보내야 해요(파이썬 `http.server`는 그렇게 해요) |
