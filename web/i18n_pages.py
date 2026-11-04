"""Make the English pages (docs/index.html, docs/lab.html, the main ones) from the Korean sources (docs/index.ko.html,
docs/lab.ko.html). Every pair must match exactly once, so a changed Korean page fails loudly instead of leaving
Korean text behind. Run after editing a Korean page:  python3 web/i18n_pages.py"""
import os, re, sys

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

COMMON = [
    ('<html lang="ko">', '<html lang="en">'),
]

GAME = [
    ('<title>꼬마선충 슈퍼탱크</title>', '<title>Worm Arcade · Super Tank</title>'),
    ('<h1>꼬마선충 슈퍼탱크</h1><nav class="links"><a href="lab.ko.html">꼬마선충 연구소</a><a href="https://github.com/hoksi/worm-arcade" target="_blank" rel="noopener">GitHub</a><a class="lang" href="index.html" hreflang="en">English</a></nav>',
     '<h1>Worm Arcade: Super Tank</h1><nav class="links"><a href="lab.html">Worm Lab</a><a href="https://github.com/hoksi/worm-arcade" target="_blank" rel="noopener">GitHub</a><a class="lang" href="index.ko.html" hreflang="ko">한국어</a></nav>'),
    ('<p class="lead">진짜 꼬마선충(<i>C. elegans</i>)의 신경 배선도가 1981년 아케이드 게임 Super Tank를 플레이해요. 배선은 그대로 두고, 뉴런마다 몇 가지 값만 진화로 학습시켰어요.</p>',
     '<p class="lead">The real wiring diagram of the worm <i>C. elegans</i> plays the 1981 arcade game Super Tank. The wiring is unchanged; evolution trained only a few values per neuron.</p>'),
    ('<p>롬 파일이 없으면 녹화 영상을, 롬을 선택하면 브라우저에서 실시간 플레이를 보여 줘요. <a href="lab.ko.html">꼬마선충 연구소</a>에서는 먹이와 포식자를 놓고 움직임을 관찰할 수 있어요.</p>',
     '<p>Without the ROM file you see a recording; choose the ROM and it plays live in your browser. In the <a href="lab.html">Worm Lab</a> you can put out food and predators and watch how it moves.</p>'),
    ('<span class="label">모델</span>', '<span class="label">Model</span>'),
    ('<span class="label">지금 행동</span><span class="big" id="verdict">기다리는 중</span>',
     '<span class="label">Now</span><span class="big" id="verdict">waiting</span>'),
    ('<div class="label">켜진 감각</div>', '<div class="label">Active senses</div>'),
    ('<button id="restart" hidden>새 게임</button>', '<button id="restart" hidden>New game</button>'),
    ('<div class="pad" id="pad" hidden aria-label="2P 조종">', '<div class="pad" id="pad" hidden aria-label="Player 2 controls">'),
    ('data-k="p2up" aria-label="위">', 'data-k="p2up" aria-label="Up">'),
    ('data-k="p2left" aria-label="왼쪽">', 'data-k="p2left" aria-label="Left">'),
    ('data-k="p2right" aria-label="오른쪽">', 'data-k="p2right" aria-label="Right">'),
    ('data-k="p2down" aria-label="아래">', 'data-k="p2down" aria-label="Down">'),
    ('<button class="firebtn" data-k="p2fire">발사</button>', '<button class="firebtn" data-k="p2fire">FIRE</button>'),
    ('log("2인용 시작: 꼬마선충 1P, 사람 2P")', 'log("two players: the worm is player 1, you are player 2")'),
    ('on ? "꼬마선충 혼자 하기" : "꼬마선충과 함께 게임하기"', 'on ? "Worm alone" : "Play with the worm"'),
    ('<button id="coop" hidden>꼬마선충과 함께 게임하기</button>', '<button id="coop" hidden>Play with the worm</button>'),
    ('<p class="cap" id="coopHelp" hidden>당신은 하늘색 2P예요. <b>W·A·S·D</b>로 움직이고 <b>J</b>로 쏴요. 휴대폰은 게임 화면 아래 버튼을 쓰세요. 노란 1P는 계속 꼬마선충이 조종해요.</p>',
     '<p class="cap" id="coopHelp" hidden>You are sky-blue player 2: move with <b>W A S D</b>, fire with <b>J</b>. On a phone use the buttons under the game. Yellow player 1 is still the worm.</p>'),
    ('on ? "실시간 · 꼬마선충(1P)과 함께 하는 중" : "실시간 · 꼬마선충이 지금 플레이 중"', 'on ? "LIVE · playing together with the worm (player 1)" : "LIVE · the worm is playing now"'),
    ('<div class="label">기록</div>', '<div class="label">Log</div>'),
    ('롬은 이 페이지에 들어 있지 않아요. 롬 이미지는 Video Games GmbH 창업자 Reinhard Stompe가 비상업적 용도로 무료 공개한 것으로, 직접 내려받아 쓰세요(', 'The ROM is not included in this page. The ROM images were made available for free, non-commercial use by Reinhard Stompe, founder of Video Games GmbH; please download them yourself ('),
    ('). 이 페이지는 비상업적 개인 실험이며, 권리자가 원하지 않으면 바로 내리겠습니다.</p>', '). This is a non-commercial personal experiment; it will be taken down at the rights holder\'s request.</p>'),
    ('<p>에뮬레이터: ', '<p>Emulator: '),
    ('(GPL-2.0+), Emscripten으로 Super Tank 드라이버만 빌드. 바꾼 곳: src/osd/sdl/sdlprefix.h의 <code>struct _IO_FILE {};</code> 한 줄을 막음(최신 Emscripten과 충돌), 링크에 <code>-s EXCEPTION_CATCHING_ALLOWED</code> 목록 추가.</p>',
     '(GPL-2.0+), built with Emscripten with only the Super Tank driver. Changes: commented out <code>struct _IO_FILE {};</code> in src/osd/sdl/sdlprefix.h (clashes with newer Emscripten) and added the <code>-s EXCEPTION_CATCHING_ALLOWED</code> list at link time.</p>'),
    ('<p>배선도: OpenWorm c302 <code>herm_full_edgelist.csv</code> (Cook 외 2019, MIT). 꼬마선충 뇌와 화면 해석 코드: <code>brain.js</code>, <code>play.js</code>. 소스 코드: <a href="https://github.com/hoksi/worm-arcade" target="_blank" rel="noopener">github.com/hoksi/worm-arcade</a> (MIT).</p>',
     '<p>Connectome: OpenWorm c302 <code>herm_full_edgelist.csv</code> (Cook et al. 2019, MIT). Worm brain and screen reader: <code>brain.js</code>, <code>play.js</code>. Source: <a href="https://github.com/hoksi/worm-arcade" target="_blank" rel="noopener">github.com/hoksi/worm-arcade</a> (MIT).</p>'),
    ('const KO = { smell_up: "냄새 진해짐", smell_down: "냄새 약해짐", pred_front: "앞에 적", pred_back: "뒤에 적", pred_L: "왼쪽 적",\n  pred_R: "오른쪽 적", touch_front: "앞 촉각", touch_back: "뒤 촉각", touch_L: "왼쪽 촉각", touch_R: "오른쪽 촉각", nose: "코에 벽",\n  mouth_food: "입 앞 먹이", mouth_noxious: "정면의 적 (I2)" };',
     'const KO = { smell_up: "odour rising", smell_down: "odour falling", pred_front: "enemy ahead", pred_back: "enemy behind", pred_L: "enemy left",\n  pred_R: "enemy right", touch_front: "touch front", touch_back: "touch back", touch_L: "touch left", touch_R: "touch right", nose: "nose on wall",\n  mouth_food: "food at mouth", mouth_noxious: "enemy straight ahead (I2)" };'),
    ('log("동전 넣고 시작")', 'log("coin in, start")'),
    ('log(`모델: ${NAME[run] || run} (${params[run].gen}세대)`)', 'log(`model: ${NAME[run] || run} (generation ${params[run].gen})`)'),
    ('"탱크 없음 (폭발·다시 등장·게임 끝)"', '"no tank (explosion, respawn or game over)"'),
    ('0: "가만히"', '0: "stay"'),
    ('<span class="fire">발사!</span>', '<span class="fire">fire!</span>'),
    ('`걸음 ${steps} · 발사 ${fires} · 적 ${o.enemies.length - p2.length}${p2.length ? " · 2P 감지" : ""} · 포탄 ${o.shells.length} · 켜진 뉴런 ',
     '`steps ${steps} · shots ${fires} · enemies ${o.enemies.length - p2.length}${p2.length ? " · player 2 seen" : ""} · shells ${o.shells.length} · active neurons '),
    ('log("MAME 멈춤: " + e)', 'log("MAME stopped: " + e)'),
    ('log("MAME 준비")', 'log("MAME ready")'),
    ('<p><b>직접 돌려 보기</b> — mamedev.org에서 Super Tank 롬(supertnk.zip)을 내려받은 뒤 선택해 주세요.</p>',
     '<p><b>Run it yourself</b> — download the Super Tank ROM (supertnk.zip) from mamedev.org, then choose it.</p>'),
    ('>롬 내려받기 (mamedev.org)</a><label class="filebtn">롬 파일 선택<input', '>Get the ROM (mamedev.org)</a><label class="filebtn">Choose ROM file<input'),
    ('<p class="cap">파일은 이 브라우저 안에서만 쓰이고 어디에도 올라가지 않아요. 다음에 오면 다시 넣지 않아도 되게 이 브라우저에만 저장해 둬요.</p>',
     '<p class="cap">The file is used only inside this browser and is never uploaded. It is kept in this browser so you do not need to choose it again next time.</p>'),
    ('"Super Tank 롬(supertnk.zip)이 아닌 것 같아요."', '"This does not look like the Super Tank ROM (supertnk.zip)."'),
    ('log("롬 확인, MAME 시작")', 'log("ROM found, starting MAME")'),
    ('setStatus("live", "실시간 · 꼬마선충이 지금 플레이 중")', 'setStatus("live", "LIVE · the worm is playing now")'),
    ('setStatus("", "▶ 녹화 영상 · 꼬마선충이 실제로 플레이한 한 판 (4,150점)")', 'setStatus("", "▶ Recording · one game the worm really played (4,150 points)")'),
    ('setStatus("wait", "게임 켜는 중…")', 'setStatus("wait", "Starting the game…")'),
    ('<span class="label">상태</span><span class="badge wait" id="status">불러오는 중…</span>', '<span class="label">Status</span><span class="badge wait" id="status">loading…</span>'),
    ('<button id="forgetRom" hidden>저장된 롬 지우기</button>', '<button id="forgetRom" hidden>Forget saved ROM</button>'),
    ('alert("저장된 롬을 지웠어요. 페이지를 새로 불러올게요.")', 'alert("The saved ROM is removed. The page will reload.")'),
]

LAB = [
    ('BRAIN_NAME = { naive: "회색" }', 'BRAIN_NAME = { naive: "grey" }'),
    ('<title>꼬마선충 연구소</title>', '<title>Worm Lab</title>'),
    ('<h1>꼬마선충 연구소</h1><nav class="links"><a href="index.ko.html">오락실로 가기</a><a href="https://github.com/hoksi/worm-arcade" target="_blank" rel="noopener">GitHub</a><a class="lang" href="lab.html" hreflang="en">English</a></nav>', '<h1>Worm Lab</h1><nav class="links"><a href="index.html">To the arcade</a><a href="https://github.com/hoksi/worm-arcade" target="_blank" rel="noopener">GitHub</a><a class="lang" href="lab.ko.html" hreflang="ko">한국어</a></nav>'),
    ('aria-label="꼬마선충이 움직이는 판"', 'aria-label="Arena where the worm moves"'),
    ('<div class="label">놀이터</div>', '<div class="label">Playground</div>'),
    ('<button class="btn" id="foodBtn">먹이 뿌리기</button>', '<button class="btn" id="foodBtn">Scatter food</button>'),
    ('<button class="btn" id="predBtn">포식자 풀기 (최대 2)</button>', '<button class="btn" id="predBtn">Release predator (up to 2)</button>'),
    ('<div class="label">두 번째 꼬마선충</div>', '<div class="label">Second worm</div>'),
    ('aria-label="비교할 꼬마선충"><option value="">없음</option>', 'aria-label="Worm to compare"><option value="">none</option>'),
    ('<button class="btn ghost" id="predOff">포식자 치우기</button>', '<button class="btn ghost" id="predOff">Remove predator</button>'),
    ('<button class="btn ghost" id="clearEnv">모두 치우기</button>', '<button class="btn ghost" id="clearEnv">Clear all</button>'),
    ('<p class="note">판을 누르면 그 자리에 먹이가 생겨요. 포식자에게 부딪히거나 포탄에 맞으면 맞은 쪽 몸에 아픔(강한 촉각)이 들어가고, 꼬마선충은 잠깐 깜빡이며 무적이 되고, 포식자는 꼬마선충에게서 떨어진 다른 자리로 물러나요. 꼬마선충은 죽지 않아요.</p>',
     '<p class="note">Tap the arena to drop food there. If the predator bumps into the worm or its shell hits, the worm feels pain (strong touch) on that side, blinks invulnerable for a moment, and the predator moves to another spot away from the worm. The worm never dies.</p>'),
    ('<div class="label" id="sensesLabel">지금 켜진 감각</div>', '<div class="label" id="sensesLabel">Active senses</div>'),
    ('env: "놀이터: 감각은 꼬마선충이 있는 자리에서 실제 게임과 같은 방식으로 계산돼요. 왼쪽의 감각 표시와 뇌 지도는 첫 번째 꼬마선충이에요."',
     'env: "Playground: the senses are computed from where each worm is, the same way as in the game. The sense chips and the brain map show the first worm."'),
    ('direct: "직접 자극: 판 위의 꼬마선충은 뇌가 고른 행동대로 움직여요. 감각은 왼쪽에서 켠 그대로 들어가고, 판 위의 위치와는 상관없어요."',
     'direct: "Direct stimulus: the worm moves the way its brain decides. The senses are the ones you switched on, whatever its position in the arena."'),
    ('"회색 꼬마선충. 학습 전이라 모든 값이 기본이에요. 배선도만으로 어떻게 움직이는지 볼 수 있어요."',
     '"The grey worm. Untrained, every value at its default: the wiring diagram on its own."'),
    (': 먹은 먹이 ${wm.eaten} · 맞힌 포식자 ${wm.kills} · 잡힐 뻔 ${wm.caught}`', ': food eaten ${wm.eaten} · predators hit ${wm.kills} · near-catches ${wm.caught}`'),
    ('`<br>남은 먹이 ${env.foods.length} · 포식자 ${env.preds.length}`', '`<br>food left ${env.foods.length} · predators ${env.preds.length}`'),
    ('<button class="btn" id="heavenBtn">천국 먹이판 (76개)</button>', '<button class="btn" id="heavenBtn">Heaven food board (76)</button>'),
    ('`<br>천국 먹이판: ${env.board.done === null ? `${env.board.t}걸음째` : `${env.board.done}걸음에 다 먹음`}`', '`<br>heaven board: ${env.board.done === null ? `step ${env.board.t}` : `all eaten in ${env.board.done} steps`}`'),
    ('<p class="lead">진짜 꼬마선충 배선도(뉴런과 근육 448개)에 진화로 찾은 값을 얹은 모델들이에요. 놀이터에 먹이를 주거나 포식자를 풀면 꼬마선충이 감각으로 느끼고 스스로 움직여요.</p>\n    <p>두 마리를 나란히 풀어 비교할 수 있고, 아래 뇌 지도에서 뉴런을 누르면 그 뉴런을 끌 수 있어요.</p>',
     '<p class="lead">Models: the real <i>C. elegans</i> wiring diagram (448 neurons and muscles) with values found by evolution. Give food or release a predator in the playground and the worm feels it through its senses and moves on its own.</p>\n    <p>Release two worms side by side to compare them, and tap a neuron on the brain map below to silence it.</p>'),
    ('aria-label="감각과 설정"', 'aria-label="Senses and settings"'),
    ('<div class="label">첫 번째 꼬마선충</div>', '<div class="label">First worm</div>'),
    ('aria-label="모델 고르기"', 'aria-label="Choose a model"'),
    ('<button class="btn" id="play">일시정지</button>', '<button class="btn" id="play">Pause</button>'),
    ('<button class="btn ghost" id="reset">처음부터</button>', '<button class="btn ghost" id="reset">Reset</button>'),
    ('<button class="btn ghost" id="clearSil">끈 뉴런 되살리기</button>', '<button class="btn ghost" id="clearSil">Restore neurons</button>'),
    ('<span class="label">지금 행동</span>', '<span class="label">Now</span>'),
    ('aria-label="최근 쏘기 신호와 문턱"', 'aria-label="Recent spitting signal and its threshold"'),
    ('></i>켜진 정도</span>', '></i>activity</span>'),
    ('></i>지금 감각이 들어가는 뉴런</span>', '></i>neurons receiving a sense now</span>'),
    ('></i>행동을 읽는 운동 뉴런</span>', '></i>motor neurons read for actions</span>'),
    ('></i>끈 뉴런</span>', '></i>silenced</span>'),
    ('aria-label="뉴런 지도"', 'aria-label="Neuron map"'),
    ('>뉴런을 누르면 이름과 값이 보이고, 한 번 더 누르면 꺼져요.</div>', '>Tap a neuron to see its name and value; tap again to silence it.</div>'),
    ('<a href="index.ko.html">← 꼬마선충이 슈퍼탱크를 플레이하는 페이지</a><br>배선도: OpenWorm c302 <code>herm_full_edgelist.csv</code> (Cook 외 2019, 암수한몸, MIT 라이선스). 진화 값: 각 모델 설명에 적힌 곳(포식자가 있는 놀이터나 천국)에서 학습한 실험마다 가장 잘한 개체. 학습 때처럼 걸음의 10%는 직전 행동이 한 번 더 나와요. 계산은 서버의 파이썬 뇌와 같은 식이고, 같은 입력에서 뉴런 값 차이는 0.000001 이하예요. 이 페이지는 전부 브라우저 안에서 돌아요. 소스 코드: <a href="https://github.com/hoksi/worm-arcade" target="_blank" rel="noopener">github.com/hoksi/worm-arcade</a> (MIT).',
     '<a href="index.html">← Watch the worm play Super Tank</a><br>Connectome: OpenWorm c302 <code>herm_full_edgelist.csv</code> (Cook et al. 2019, hermaphrodite, MIT). Evolved values: the best individual of each run, trained where its description says (the predator playground or heaven). As in training, on 10% of steps the last action is repeated. The maths is the same as the Python brain; on the same input the neuron values differ by less than 0.000001. Everything runs in your browser. Source: <a href="https://github.com/hoksi/worm-arcade" target="_blank" rel="noopener">github.com/hoksi/worm-arcade</a> (MIT).'),
    ('["먹이", [["smell_up", "냄새 진해짐"], ["smell_down", "냄새 약해짐"], ["mouth_food", "바로 앞에 먹이"]]]',
     '["Food", [["smell_up", "odour rising"], ["smell_down", "odour falling"], ["mouth_food", "food at mouth"]]]'),
    ('["적 탱크", [["pred_front", "앞"], ["pred_back", "뒤"], ["pred_L", "왼쪽"], ["pred_R", "오른쪽"], ["mouth_noxious", "정면의 적 (입 I2)"]]]',
     '["Enemy tank", [["pred_front", "ahead"], ["pred_back", "behind"], ["pred_L", "left"], ["pred_R", "right"], ["mouth_noxious", "straight ahead (mouth I2)"]]]'),
    ('["포탄·벽 (촉각)", [["touch_front", "앞"], ["touch_back", "뒤"], ["touch_L", "왼쪽"], ["touch_R", "오른쪽"], ["nose", "코끝에 벽"]]]',
     '["Shells and walls (touch)", [["touch_front", "front"], ["touch_back", "back"], ["touch_L", "left"], ["touch_R", "right"], ["nose", "nose on wall"]]]'),
    ('const MOVE_KO = { forward: "앞", back: "뒤", stay: "멈춤" };', 'const MOVE_KO = { forward: "fwd", back: "back", stay: "stop" };'),
    ('new Option("회색 · 학습 전 (모든 값 기본)", "naive")', 'new Option("Grey · untrained (all defaults)", "naive")'),
    ('["감각 뉴런", n =>', '["Sensory neurons", n =>'),
    ('["사이 뉴런·머리 운동 뉴런", n =>', '["Interneurons and head motor neurons", n =>'),
    ('["몸 운동 뉴런 (앞으로 VB·DB / 뒤로 VA·DA)", n =>', '["Body motor neurons (forward VB·DB / backward VA·DA)", n =>'),
    ('["인두 (먹기·뱉기)", n =>', '["Pharynx (eating, spitting)", n =>'),
    ('["근육과 기타", n =>', '["Muscles and other", n =>'),
    ('"운동:" + k', '"motor:" + k'),
    ('`<b>${nm}</b> 켜짐 ${v.toFixed(3)} · 보내는 세기 ${out.toFixed(2)}${out < 0 ? " (억제)" : ""}`',
     '`<b>${nm}</b> activity ${v.toFixed(3)} · output ${out.toFixed(2)}${out < 0 ? " (inhibitory)" : ""}`'),
    ('` · 역할 ${role.join(", ")}`', '` · role ${role.join(", ")}`'),
    ('` · <span style="color:var(--alert)">꺼짐</span> (한 번 더 누르면 되살림)` : " · 한 번 더 누르면 끔"',
     '` · <span style="color:var(--alert)">silenced</span> (tap again to restore)` : " · tap again to silence"'),
    ('[["move", "이동 (앞 − 뒤)"], ["turn", "회전 (왼 − 오)"], ["spit", "쏘기 (M1·pm3)"]]',
     '[["move", "move (forward − back)"], ["turn", "turn (left − right)"], ["spit", "spit (M1·pm3)"]]'),
    ('`${value.toFixed(3)} / 문턱 ${th.toFixed(3)}`', '`${value.toFixed(3)} / threshold ${th.toFixed(3)}`'),
    ('ctx.fillText("쏘기 문턱", 4, Y(th) - 4); ctx.fillText("최근 100걸음 쏘기 신호", 4, h - 2);',
     'ctx.fillText("spit threshold", 4, Y(th) - 4); ctx.fillText("spitting signal, last 100 steps", 4, h - 2);'),
    ('d.turn === "left" ? "왼쪽" : "오른쪽"', 'd.turn === "left" ? "left" : "right"'),
    ('<span class="fire">발사</span>', '<span class="fire">fire</span>'),
    ('`${stepNo}걸음`', '`step ${stepNo}`'),
    ('running ? "일시정지" : "계속"', 'running ? "Pause" : "Resume"'),
]


def make(src, dst, pairs):
    s = open(os.path.join(DOCS, src), encoding="utf-8").read()
    for a, b in COMMON + pairs:
        n = s.count(a)
        if n != 1:
            sys.exit(f"{src}: expected one match, found {n}: {a[:70]!r}")
        s = s.replace(a, b)
    left = [m.group(0) for m in re.finditer(r"[가-힣][^<>\"`]{0,30}", s) if m.group(0) not in ("한국어",)]
    if left:
        sys.exit(f"{dst}: Korean text left: {left[:5]}")
    open(os.path.join(DOCS, dst), "w", encoding="utf-8").write(s)
    print(dst, "ok")


if __name__ == "__main__":
    make("index.ko.html", "index.html", GAME)
    make("lab.ko.html", "lab.html", LAB)
