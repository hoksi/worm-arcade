# 꼬마선충 오락실

[English](README.md)

**▶ 바로 보기: https://hoksi.github.io/worm-arcade/**

예쁜꼬마선충(*C. elegans*)이 1981년 아케이드 게임 **Super Tank**를 플레이합니다. 진짜 꼬마선충의 신경 배선도를 그대로 옮기고, 뉴런마다 신호 세기 같은 몇 가지 값만 진화를 통해 학습시켰어요.

게임 페이지는 롬 파일이 없으면 꼬마선충이 실제로 플레이한 영상을 보여 줘요. Super Tank 롬 파일(supertnk.zip, [mamedev.org](https://www.mamedev.org/roms/supertnk/)에서 무료로 받을 수 있어요)을 페이지에서 선택하면 설치 없이 브라우저에서 직접 돌아가요. 롬은 이 저장소에 들어 있지 않아요.

- [게임](https://hoksi.github.io/worm-arcade/index.ko.html) — 꼬마선충이 실제 게임(MAME)을 플레이해요. 영상, 또는 롬을 넣고 직접.
- [꼬마선충 연구소](https://hoksi.github.io/worm-arcade/lab.ko.html) — 먹이와 포식자를 놓고 꼬마선충이 어떻게 움직이는지 보고, 두 마리를 나란히 비교하고, 뉴런을 꺼 볼 수 있어요.

## 어떻게 움직이나

```
게임 화면 → 감각 → 꼬마선충 뇌 (뉴런·근육 448개) → 운동 뉴런 → 버튼
```

1. **화면 읽기** — 노랑은 내 탱크, 빨강은 적과 포탄, 초록은 지뢰(먹이)예요. `web/play.js`
2. **감각** — 게임 정보를 13가지 감각으로 바꿔 감각 뉴런에 넣어요. 먹이 냄새가 진해짐·약해짐, 앞·뒤·왼·오른쪽의 적, 몸에 닿는 포탄과 옆의 벽, 코끝의 벽, 입 앞의 먹이, 정면의 적이에요.
3. **뇌** — OpenWorm의 배선도(Cook 외 2019)예요. 각 뉴런은 "켜진 정도" 숫자 하나로 계산하고, 진화는 뉴런마다 보내는 세기와 기본값, 행동 문턱 세 개만 정해요. 연결은 하나도 바꾸지 않아요. `web/brain.js`
4. **행동** — 앞으로 가는 뉴런(AVB, VB, DB)과 뒤로 가는 뉴런(AVA, VA, DA)의 차이로 전진·후진, 머리를 등쪽·배쪽으로 구부리는 뉴런으로 회전, 인두의 '뱉기' 뉴런(M1, pm3)으로 발사해요.

학습은 실제 게임을 본뜬 파이썬 놀이터에서 해요. 실제 게임보다 40배쯤 빨라서 500세대를 돌릴 수 있어요. 점수는 실제 게임에서 따로 재요.

게임과 꼬마선충을 잇는 방식은 두 가지예요. 자율 연결은 게임과 뉴런 사이의 연결까지 진화가 정해요.

| | 지정 연결 | 자율 연결 |
| --- | --- | --- |
| 게임 → 감각 | 사람이 고른 뉴런 (적 → ASH) | 진화가 고름 |
| 운동 뉴런 → 버튼 | 사람이 고른 뉴런 (AVA → 후진) | 진화가 고름 |

## 결과 일부

실제 게임 12판 평균, 적 한 대 200점:

| 모델 | 실제 게임 | 정면의 적에게 쏘는 비율 / 그 밖의 때 |
| --- | --- | --- |
| 초록 (자율 연결, 발사 규칙 없음) | 2,788 | 70% / 3% |
| 파랑 (지정 연결, 발사 규칙 없음) | 2,225 | 69% / 3% |
| 아무 버튼이나 | 약 1,771 | — |

"정면에 적이 있을 때만 쏜다"는 규칙을 빼도, 두 꼬마선충 모두 스스로 정면의 적에게 쏘는 법을 찾았어요. 지정 연결은 입 안의 감각 뉴런 I2에서 뱉기 뉴런 M1로 가는 원래 배선을 썼고, 자율 연결은 적의 방향 감각과 포탄 촉각을 함께 썼어요.

점수는 운에 따라 크게 차이가 납니다. 같은 방법으로 두 번 학습시킨 꼬마선충도 실제 게임 평균이 2,321점과 1,875점으로 450점쯤 차이가 났어요. 그래서 위 표의 점수 차이만으로 어느 쪽이 더 낫다고 말하기는 어려워요.

## 직접 해 보기

```bash
# 페이지
cd docs && python3 -m http.server 8000      # http://localhost:8000 (롬은 페이지에서 선택)

# JS가 파이썬과 같은지 검사
cd web && node brain.test.cjs && node play.test.cjs && node free.test.cjs

# 놀이터에서 진화시키기 (Python 3, numpy, scipy)
cd worm && python3 pg_evolve.py --sym --predator --kill-pts 200 --player free_freefire --out my_worm --steps 1500 --gens 500
python3 exp_report.py my_worm                # 놀이터 12판
python3 aim_combo.py my_worm                 # 어떤 감각으로 조준하나
# 학습하면 worm/run/my_worm/best.web.json(브라우저용 모델)도 함께 저장돼요.
# 페이지에 올리려면 docs/models/my_worm.json으로 복사하고, docs/models/index.json에 이름·설명·색을 한 줄 추가하세요.
python3 ../web/i18n_pages.py                 # 한국어 페이지를 고친 뒤 영어 페이지 다시 만들기

# 실제 게임 점수 재기 (Lua가 들어 있는 데스크톱 MAME 필요, roms/에 supertnk.zip을 직접 넣기)
cd arcade && python3 score_real.py out.json my_worm

# MAME를 브라우저용으로 빌드
mame/build.sh /path/to/emsdk
```

- `worm/` — 뇌, 감각, 놀이터(포식자 1~2마리), 진화 학습, 분석
- `web/` — 브라우저 뇌와 화면 해석, 파이썬 대비 테스트
- `arcade/` — 실제 게임 연결: MAME 안에서 도는 Lua 브리지, 화면·RAM을 읽는 환경, 실제 게임 12판 점수 재기
- `mame/` — MAME 0.285 WebAssembly 빌드 스크립트와 패치 ([빌드 가이드](mame/README.ko.md))
- `docs/` — GitHub Pages

## 출처와 라이선스

- 우리 코드(`worm/`, `web/`, `docs/*.html`, `docs/*.js`): MIT — [LICENSE](LICENSE)
- **Super Tank** © 1981 Video Games GmbH. 롬 이미지는 Video Games GmbH 창업자 Reinhard Stompe가 비상업적 용도로 무료 공개한 것입니다: https://www.mamedev.org/roms/supertnk/ . mamedev.org는 롬을 자기 사이트에서만 배포하도록 허락받았기 때문에, 이 저장소와 페이지에는 롬을 넣지 않았어요. 페이지에서 선택한 롬은 그 브라우저 안에서만 쓰여요. 이 저장소는 비상업적 개인 실험이며, 권리자가 원하지 않으면 바로 내리겠습니다.
- **MAME** 0.285 (`docs/mame/supertnk.js`, `.wasm`): GPL-2.0 이상, 소스 https://github.com/mamedev/mame/tree/mame0285 , 우리가 바꾼 곳은 [`mame/`](mame/)에 있어요.
- **배선도**: OpenWorm c302 `herm_full_edgelist.csv` (Cook 외 2019, *Nature* 571), MIT — https://github.com/openworm/c302
