// Behaviour checks per feature, run after tools/sim.js: checks.hazards() returns the measured numbers.
(() => {
  const g = window.__game;
  const steps = (n, each) => { for (let i = 0; i < n && !g.G.over; i++) { each && each(); g.step(1); } };
  const hold = () => { if (g.units.length < 30) g.addUnits(30 - g.units.length); };
  const calm = () => { g.G.nextAt = 1e9; };  // no director rows during an isolated check
  const noFire = () => { for (const u of g.units) u.cd = 1e9; };
  function fresh(modeKey = 'classic', crew = 30) {
    g.start(modeKey); calm();
    g.addUnits(crew - 1);
    steps(60);
  }
  const lost = (fn) => { const n0 = g.units.length; fn(); return n0 - g.units.length; };

  const hazards = () => {
    const r = {};
    fresh(); g.G.target = 2.5; steps(60);
    g.spawnHazard('spikes', 0, 5, -8);
    r.spikesSameSide = lost(() => steps(300, noFire));
    fresh(); g.G.target = -2.5; steps(60);
    g.spawnHazard('spikes', 0, 5, -8);
    r.spikesOtherSide = lost(() => steps(300, noFire));

    fresh(); g.G.target = 0; steps(60);
    g.spawnHazard('saw', -8, 0);
    r.sawOnCrowd = lost(() => steps(300, noFire));

    fresh(); g.G.target = 2.5; steps(60);
    let h = g.spawnHazard('laser', -0.5); h.side = 1; h.cyc = 0;
    r.laserOnCrowdHalf = lost(() => steps(Math.round(2.4 * 120), () => { h.z = -0.5; noFire(); }));
    fresh(); g.G.target = -2.5; steps(60);
    h = g.spawnHazard('laser', -0.5); h.side = 1; h.cyc = 0;
    r.laserOtherHalf = lost(() => steps(Math.round(2.4 * 120), () => { h.z = -0.5; noFire(); }));
    fresh(); g.G.target = -2.5; steps(60);
    h = g.spawnHazard('laser', -12); h.side = 1; h.cyc = 0;
    for (let i = 0; i < 6; i++) g.spawnEnemy(2.5 + (i % 3 - 1), -12, 50);
    steps(Math.round(2.4 * 120), () => { h.z = -12; for (const e of g.enemies) e.z = -12; noFire(); });
    r.laserEnemiesLeft = g.enemies.length;

    fresh(); g.G.target = 0; steps(60);
    let tFire = null; h = g.spawnHazard('rock', 0);
    r.rockCrewKilled = lost(() => steps(300, () => { noFire(); if (h.landed && tFire === null) tFire = h.z; }));
    let leak = 0;
    for (let i = 0; i < 240 && !h.gone; i++) { g.step(1); for (const b of g.bullets) if (h.landed && Math.abs(b.x - h.x) < 0.4 && b.z < h.z - 1.2) leak++; }
    r.rockLanded = tFire !== null; r.rockBulletsPast = leak;

    fresh(); g.G.target = 0; steps(60);
    h = g.spawnHazard('explosive', 0, -14);
    for (let i = 0; i < 8; i++) g.spawnEnemy(-2 + i * 0.6, -16, 40);
    for (const e of g.enemies) e.walk = 0;
    const e0 = g.enemies.length; let shotAt = null;
    steps(600, () => { for (const e of g.enemies) e.z = Math.min(e.z, -16 + 0.0); if (h.gone && shotAt === null) shotAt = g.units.length; });
    r.explosiveShotGone = h.gone; r.explosiveEnemiesKilled = e0 - g.enemies.length; r.explosiveCrewAtBlast = shotAt;
    fresh(); g.G.target = 0; steps(60);
    h = g.spawnHazard('explosive', 0, -6);
    r.explosiveTouchCrewLost = lost(() => steps(400, noFire));

    fresh(); g.G.target = 2; steps(60);
    h = g.spawnHazard('turret', -1, -20);
    let bolts = 0; const seen = new Set();
    r.turretCrewLost = lost(() => steps(1200, () => { h.z = -20; noFire(); for (const o of g.hazards) if (o.kind === 'bolt' && !seen.has(o)) { seen.add(o); bolts++; } }));
    r.turretBolts = bolts;
    fresh(); g.G.target = -4; steps(60);
    h = g.spawnHazard('turret', -1, -14); const hp0 = h.hits;
    steps(1500, () => { if (!h.gone) h.z = -14; });
    r.turretHp0 = hp0; r.turretDestroyed = h.gone;

    fresh(); g.G.target = 0; steps(60);
    g.hazardRow('lava');
    let lava = g.hazards.find(o => o.kind === 'lava');
    r.lavaCrewLost = lost(() => steps(2400, () => { noFire(); for (const b of g.barrels) b.z = -40; }));
    r.lavaFrontAfterCreep = +lava.front.toFixed(2);
    fresh(); g.G.target = 0; steps(60);
    g.hazardRow('lava');
    lava = g.hazards.find(o => o.kind === 'lava');
    const pushes = []; let last = lava.front;
    steps(4000, () => {
      const dam = g.barrels.find(b => b.tag);
      g.G.target = dam && dam.z < -10 ? dam.x : (dam ? -dam.x : 0);
      if (lava.front > last + 0.5) pushes.push(+(lava.front - last).toFixed(2));
      last = lava.front;
    });
    r.lavaDamPushes = pushes; r.lavaGone = lava.gone;
    fresh(); g.G.target = 2.5; steps(60);
    const s0 = g.G.dist; steps(120); const base = g.G.dist - s0;
    g.spawnHazard('speed', 0, 5, -3);
    steps(120); const s1 = g.G.dist; steps(120); const boosted = g.G.dist - s1;
    r.speedRatio = +(boosted / base).toFixed(2); r.boostT = +g.G.boostT.toFixed(2);
    r.errors = window.sim ? window.sim.errors.length : 'n/a';
    return r;
  };
  const FACT = [0.25, 1 / 3, 0.5, 1, 2, 3, 4, 5];
  const through = (n, d) => Math.max(0, d.op === 'x' ? Math.round(n * FACT[d.value]) : n + d.value);
  function bestFrom(n, rows) {
    let best = 0;
    for (let m = 0; m < 1 << rows.length; m++) { let v = n; for (let i = 0; i < rows.length && v > 0; i++) v = through(v, rows[i][(m >> i) & 1]); best = Math.max(best, v); }
    return best;
  }
  // style: 'best' plans ahead over the remaining rows, 'face' takes whichever door shows the bigger number
  const gauntletPilot = style => g => {
    const G = g.G, open = g.gates.filter(x => !x.done);
    const rows = [...new Set(open.map(x => x.rowId))].sort((a, b) => a - b);
    const near = rows.length && open.filter(x => x.rowId === rows[0]);
    if (near && near[0].z > -22) {
      const idx = G.row - rows.length, n = G.reserve + g.units.length;
      const face = d => (d.op === 'x' ? (FACT[d.value] >= 1 ? FACT[d.value] : -1 / FACT[d.value]) : d.value);
      const score = d => (style === 'face' ? face(d) : bestFrom(through(n, d), G.plan.rows.slice(idx + 1)));
      const pick = near.reduce((a, x) => (score(x) > score(a) ? x : a));
      G.target = pick.z > -5 ? pick.cx : window.sim.avoid(g, pick.cx);
    } else G.target = window.sim.avoid(g, G.target);
  };
  function gauntlet() {
    const r = { plans: [] };
    for (let L = 1; L <= 12; L++) {
      localStorage.setItem('htb.gauntlet.level', L);
      g.start('gauntlet');
      const P = g.G.plan, traps = P.rows.filter(([a, b]) => a.op === 'x' && a.value === 2 && b.value < 0).length;
      r.plans.push(`L${L} goal ${g.G.goal} best ${P.best} (${(P.best / g.G.goal * 100).toFixed(0)}%) face ${P.face} traps ${traps}`);
    }
    const play = (L, style) => {
      localStorage.setItem('htb.gauntlet.level', L);
      g.start('gauntlet');
      steps(30000, () => gauntletPilot(style)(g));
      return { L, style, over: g.G.over, why: g.G.endWhy, crew: g.G.reserve + g.units.length, goal: g.G.goal, title: document.getElementById('endTitle').textContent,
        reason: document.getElementById('endReason').textContent, again: document.getElementById('againBtn').textContent, big: document.getElementById('againBtn').classList.contains('big'),
        nextLevel: localStorage.getItem('htb.gauntlet.level'), secs: +(g.G.time / 2).toFixed(1) };
    };
    r.runs = [play(1, 'best'), play(1, 'face'), play(5, 'best'), play(5, 'face'), play(10, 'best'), play(10, 'face')];
    r.errors = window.sim.errors.length;
    return r;
  }
  window.checks = { steps, fresh, lost, hold, calm, noFire, hazards, gauntlet, gauntletPilot };
})();
