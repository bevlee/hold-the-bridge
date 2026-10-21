// Headless sim harness. Load in the page console:
//   await new Promise(r => { const s = document.createElement('script'); s.src = 'tools/sim.js?' + Date.now(); s.onload = r; document.head.append(s); });
//   sim.fingerprint('classic', sim.pilots.classic, 60000, 7)
(() => {
  const g = window.__game;
  const errors = [];
  window.addEventListener('error', e => errors.push(String(e.message)));

  function seeded(seed, fn) {
    const real = Math.random;
    let s = seed >>> 0;
    Math.random = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
    try { return fn(); } finally { Math.random = real; }
  }
  function run(modeKey, pilot, steps, seed) {
    const go = () => {
      g.start(modeKey);
      for (let i = 0; i < steps && !g.G.over; i += 2) { pilot && pilot(g); g.step(2); }
      return g.G;
    };
    return seed === undefined ? go() : seeded(seed, go);
  }
  // Compare fingerprints only from a freshly loaded page: burst particles decay in the render loop, not in step(),
  // and the lanes roll caps its flakes on their count, so earlier headless runs shift the random stream.
  function fingerprint(modeKey, pilot, steps, seed = 7) {
    run(modeKey, pilot, steps, seed);
    return [modeKey, Math.round(g.G.dist * 1000), g.G.kills, g.units.length, g.enemies.length, g.barrels.length, g.gates.length,
      g.G.bosses, g.bullets.length, g.G.over, g.stats.weapon, g.stats.multi].join(',');
  }

  // x-intervals a crowd should keep out of in the next few metres, per hazard kind
  const ZONES = {
    tyre: h => [h.x - 1.2, h.x + 1.2],
    spikes: h => [h.x0, h.x1],
    saw: h => [h.lo - 1, h.hi + 1],
    laser: h => (h.cyc > 0.5 ? [h.side < 0 ? -5 : 0, h.side < 0 ? 0 : 5] : null),
    rock: h => (h.fall >= 0 && !h.landed ? [h.x - 1.6, h.x + 1.6] : null),
    explosive: h => [h.x - 1.6, h.x + 1.6],
    bolt: h => [h.x - 0.8, h.x + 0.8],
    squad: h => (h.count >= g.units.length + g.G.reserve - 2 ? [h.x0 - 0.3, h.x1 + 0.3] : null),
  };
  function avoid(g, t, near = -8) {
    let w = 0;
    for (const u of g.units) w = Math.max(w, Math.abs(u.x - g.G.crowdX));
    const bad = [];
    for (const h of g.hazards) {
      const zone = ZONES[h.kind] && h.z > near && h.z < 4 && ZONES[h.kind](h);
      if (zone) bad.push(zone);
    }
    for (const b of g.barrels) if (b.z > -9 && b.z < 4) bad.push([b.x - (b.R || 2.42) - 0.2, b.x + (b.R || 2.42) + 0.2]);
    if (!bad.length) return t;
    const lim = Math.max(0, 4.65 - w);
    let best = t, bd = Infinity;
    for (let c = -lim; c <= lim + 1e-9; c += 0.25) {
      const clash = bad.reduce((n, [a, b]) => n + Math.max(0, Math.min(c + w, b) - Math.max(c - w, a)), 0);
      const score = clash * 100 + Math.abs(c - t);
      if (score < bd) { bd = score; best = c; }
    }
    return best;
  }
  const gateValue = x => (x.op === 'x' ? [0.25, 1 / 3, 0.5, 1, 2, 3, 4, 5][x.value] * 30 - 30 : x.value);
  const pilots = {
    lanes(g) {
      const n = g.units.length; if (!n) return;
      let maxOff = -9, minOff = 9;
      for (const u of g.units) { const o = u.x - g.G.crowdX; if (o > maxOff) maxOff = o; if (o < minOff) minOff = o; }
      const horde = g.enemies.filter(e => !e.armored), front = horde.reduce((m, e) => Math.max(m, e.z), -99), roll = g.barrels.find(b => b.roll), pk = g.pickups.find(p => p.z > -18), boss = g.enemies.find(e => e.armored);
      const rollDanger = roll && roll.z > -3 - roll.R - 1, safeMin = rollDanger ? (-1.45 - minOff) : -99, farm = 2.02 - maxOff, allLeft = -1.85 - maxOff, rollETA = roll ? (-3 - roll.z) / 1.1 : 1e9;
      const W = [1, 0.8, 2.2, 1.6][g.stats.weapon], RT = [1, 1.8, 0.7, 1.6][g.stats.weapon], dps = n * 0.444 * RT * g.stats.multi * g.stats.dmg * W * 0.15, canBreak = roll && dps * Math.min(rollETA, 28 + roll.z + 30) > roll.hits * 1.3;
      const slam = g.enemies.find(e => e.slam); let t;
      if (slam) t = (slam.slam.x0 + slam.slam.x1) / 2 > g.G.crowdX ? g.G.crowdX - 3 : g.G.crowdX + 3; else if (pk) t = pk.x - (pk.x < 0 ? minOff : maxOff) * 0.8;
      else if (front > -7) { const cl = horde.filter(e => e.z > -8); t = cl.length ? cl.reduce((a, e) => a + e.x, 0) / cl.length : 0; t = Math.max(-1, Math.min(t, farm)); }
      else if (boss && g.G.breaker && boss.z > -30) t = boss.x; else if (roll && roll.z > -28 && !rollDanger && n >= 10 && canBreak) t = Math.max(allLeft, -10 / 3); else t = farm;
      g.G.target = Math.max(safeMin, t);
    },
    // refills the crew, chases the nearest enemy, sidesteps barrels and takes the better door of each gate row
    classic(g) {
      if (g.units.length < 20) g.addUnits(20);
      const e = g.enemies.filter(e => e.z > -24).sort((a, b) => b.z - a.z)[0];
      const b = g.barrels.find(b => !b.impossible && b.z > -30 && b.z < -8) || g.gates.find(x => !x.done && x.value > 0 && x.z > -30 && x.op === '+');
      let t = e ? e.x : b ? (b.x ?? (b.x0 + b.x1) / 2) : 0;
      const near = g.barrels.filter(b => b.z > -9 && b.z < 4);
      if (near.length === 1) t = near[0].x < 0 ? 2.6 : -2.6;
      const row = g.gates.filter(x => !x.done && x.z > -10 && x.z < 1);
      if (row.length) {
        const best = row.reduce((a, x) => (gateValue(x) > gateValue(a) ? x : a));
        g.G.target = gateValue(best) > 0 ? best.cx : (row.length === 1 ? -Math.sign(row[0].cx || 1) * 2.6 : 0);
        return;  // a bad door costs more than any hazard
      }
      g.G.target = avoid(g, t);
    },
  };
  window.sim = { g, errors, seeded, run, fingerprint, pilots, gateValue, avoid };
})();
