// Sound for 선충 잡기 (2026-11-05, user: "뭔가 맹숭했는데 효과음과 배경 음악을 넣어보자"). Everything is synthesized
// with the Web Audio API (no sound files, nothing to license). The browser only allows sound after a tap or key, so
// Sound.unlock() is called from the start button. Sound.setOn(false) mutes everything.
(function (root) {
  let ac = null, master = null, bgmBus = null, sfxBus = null, on = true, noiseBuf = null, silentEl = null;
  const LOUD = 1.0;
  let bgmTimer = null, step = 0, nextT = 0, bpm = 132;

  function unlock() {
    if (!ac) {
      const AC = root.AudioContext || root.webkitAudioContext; if (!AC) return;
      ac = new AC();
      // louder than the first version (its peak was only ~0.07); a compressor keeps the sum from clipping
      const comp = ac.createDynamicsCompressor(); comp.threshold.value = -12; comp.ratio.value = 4; comp.connect(ac.destination);
      master = ac.createGain(); master.gain.value = on ? LOUD : 0; master.connect(comp);
      bgmBus = ac.createGain(); bgmBus.gain.value = 0.55; bgmBus.connect(master);
      sfxBus = ac.createGain(); sfxBus.gain.value = 1.0; sfxBus.connect(master);
      noiseBuf = ac.createBuffer(1, ac.sampleRate * 0.5, ac.sampleRate);
      const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ac.state === "suspended") ac.resume();
    // iPhone: Web Audio stays silent while the ring/silent switch is on silent, unless a media element is playing.
    // A looping, silent <audio> started in the same tap puts the page in "playback" mode, so the game is heard.
    if (!silentEl) {
      silentEl = document.createElement("audio");
      silentEl.setAttribute("playsinline", ""); silentEl.loop = true; silentEl.src = silentWav();
      silentEl.play().catch(() => {});
    }
  }
  function silentWav() {                                       // 0.5 s of silence, 8 kHz mono 8-bit
    const n = 4000, buf = new Uint8Array(44 + n), v = new DataView(buf.buffer), w = (o, str) => [...str].forEach((c, i) => buf[o + i] = c.charCodeAt(0));
    w(0, "RIFF"); v.setUint32(4, 36 + n, true); w(8, "WAVEfmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, 8000, true); v.setUint32(28, 8000, true); v.setUint16(32, 1, true); v.setUint16(34, 8, true); w(36, "data"); v.setUint32(40, n, true);
    buf.fill(128, 44);
    let bin = ""; for (const b of buf) bin += String.fromCharCode(b);
    return "data:audio/wav;base64," + btoa(bin);
  }
  const hz = n => 440 * Math.pow(2, (n - 69) / 12);           // MIDI note -> Hz

  // one note: oscillator type, start/end frequency (slide), volume envelope (fast attack, exponential release)
  function tone(bus, f0, dur, { type = "square", vol = 0.2, f1 = null, at = 0 } = {}) {
    if (!ac) return;
    const t = ac.currentTime + at, o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(f0, t);
    if (f1) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(bus); o.start(t); o.stop(t + dur + 0.02);
  }
  function noise(bus, dur, { vol = 0.3, at = 0, hp = 800 } = {}) {
    if (!ac) return;
    const t = ac.currentTime + at, s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
    s.buffer = noiseBuf; f.type = "highpass"; f.frequency.value = hp;
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(bus); s.start(t); s.stop(t + dur + 0.02);
  }

  let lastSpit = 0;
  const SPIT = {
    fast:   { f0: 1500, f1: 500, dur: 0.06, vol: 0.28 },
    normal: { f0: 1000, f1: 300, dur: 0.09, vol: 0.3 },
    big:    { f0: 260,  f1: 70,  dur: 0.2,  vol: 0.45 },
    many:   { f0: 1100, f1: 350, dur: 0.07, vol: 0.26, twice: true },
  };
  const sfx = {
    catch() { [72, 76, 79, 84].forEach((n, i) => tone(sfxBus, hz(n), 0.09, { vol: 0.22, at: i * 0.05 })); },
    // a worm spits: the first version (a soft 0.12-volume triangle) was not noticed (user, 2026-11-05: "선충이 포탄을
    // 쏠때 효과음이 있으면 좋겠어"), so it is louder now and sounds like its shell: fast = high and short, big = a low
    // thump, many shells = a double pew. At most one every 0.09 s.
    spit(kind) {
      if (!ac || ac.currentTime - lastSpit < 0.09) return; lastSpit = ac.currentTime;
      const k = SPIT[kind] || SPIT.normal;
      tone(sfxBus, k.f0, k.dur, { type: "square", vol: k.vol, f1: k.f1 });
      noise(sfxBus, 0.03, { vol: 0.12, hp: 2500 });
      if (k.twice) tone(sfxBus, k.f0 * 1.2, k.dur, { type: "square", vol: k.vol * 0.8, f1: k.f1 * 1.2, at: 0.06 });
    },
    hit() { noise(sfxBus, 0.25, { vol: 0.5, hp: 300 }); tone(sfxBus, 220, 0.35, { type: "sawtooth", vol: 0.25, f1: 55 }); },
    warp() { tone(sfxBus, 260, 0.28, { type: "sine", vol: 0.25, f1: 1400 }); tone(sfxBus, 520, 0.28, { type: "sine", vol: 0.1, f1: 2100, at: 0.04 }); },
    clear() {
      [[72, 0], [76, 0.12], [79, 0.24], [84, 0.36]].forEach(([n, at]) => tone(sfxBus, hz(n), 0.16, { vol: 0.2, at }));
      [72, 76, 79].forEach(n => tone(sfxBus, hz(n), 0.6, { type: "triangle", vol: 0.12, at: 0.5 }));
    },
    over() { [[67, 0], [64, 0.18], [60, 0.36], [55, 0.54]].forEach(([n, at]) => tone(sfxBus, hz(n), 0.22, { type: "triangle", vol: 0.22, at })); },
  };

  // background loop: Am - F - C - G, 8 eighth notes per chord; square bass, triangle arpeggio, noise hats.
  // Faster each round (setTempo).
  const CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]];
  const ARP = [0, 1, 2, 1, 0, 2, 1, 2], LEAD_ON = [1, 0, 1, 1, 0, 1, 1, 0];
  function scheduleStep(t, s) {
    const c = CHORDS[Math.floor(s / 8) % 4], k = s % 8, eighth = 60 / bpm / 2;
    const at = t - ac.currentTime;
    tone(bgmBus, hz(c[0] - 24 + (k % 4 === 2 ? 7 : 0)), eighth * 0.9, { vol: 0.28, at });          // bass: root, fifth
    if (LEAD_ON[k]) tone(bgmBus, hz(c[ARP[k]] + 12), eighth * 0.8, { type: "triangle", vol: 0.16, at });
    if (k % 2 === 1) noise(bgmBus, 0.04, { vol: 0.12, at, hp: 6000 });                             // off-beat hat
    if (k === 0) noise(bgmBus, 0.08, { vol: 0.18, at, hp: 120 });                                   // a soft kick
  }
  function bgmStart() {
    if (!ac || bgmTimer) return;
    step = 0; nextT = ac.currentTime + 0.05;
    bgmTimer = setInterval(() => {                              // look-ahead scheduler
      while (nextT < ac.currentTime + 0.12) { scheduleStep(nextT, step); step = (step + 1) % 32; nextT += 60 / bpm / 2; }
    }, 25);
  }
  function bgmStop() { clearInterval(bgmTimer); bgmTimer = null; }
  function setTempo(round) { bpm = Math.min(180, 126 + 6 * (round - 1)); }
  function setOn(v) { on = v; if (master) master.gain.value = on ? LOUD : 0; }

  root.Sound = { unlock, sfx, bgmStart, bgmStop, setTempo, setOn, get on() { return on; } };
})(window);
