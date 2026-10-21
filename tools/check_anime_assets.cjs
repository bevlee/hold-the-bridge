// Inspect the exported files themselves; no Blender or browser dependency.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.join(__dirname, '../assets/anime');
const context = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, 'models.js'), 'utf8'), context);
const models = context.window.ANIME_MODELS;
for (const name of ['crew', 'enemy', 'boss', 'capsule', 'crate', 'pylon']) {
  const m = models[name];
  assert(m, `Missing ${name}`);
  const vertices = m.position.length / 3;
  assert.equal(m.normal.length, m.position.length);
  assert.equal(m.color.length, m.position.length);
  assert.equal(m.index.length % 3, 0);
  assert(m.index.every(i => Number.isInteger(i) && i >= 0 && i < vertices));
  for (const values of [m.position, m.normal, m.color, ...(m.frames || [])]) {
    assert.equal(values.length, m.position.length, `${name} frame topology changed`);
    assert(values.every(Number.isFinite), `${name} has non-finite geometry`);
  }
  assert(m.color.every(c => c >= 0 && c <= 1));
  if (['crew', 'enemy', 'boss'].includes(name)) {
    assert.equal(m.frames.length, 8);
    assert(m.frames[2].some((v, i) => v !== m.frames[0][i]), `${name} walk is static`);
    assert(Math.max(...m.position.filter((_, i) => i % 3 === 1)) < 1.5);
  }
  // Winding must be reversed when converting Blender Z-up to game Y-up.
  for (let i = 0; i < m.index.length; i += 3) {
    const [a, b, c] = m.index.slice(i, i + 3).map(n => n * 3);
    const u = m.position.slice(b, b + 3).map((v, k) => v - m.position[a + k]);
    const v = m.position.slice(c, c + 3).map((v, k) => v - m.position[a + k]);
    const cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]];
    assert(cross.reduce((n, v, k) => n + v * m.normal[a + k], 0) >= -1e-5, `${name} inverted triangle`);
  }
  const glb = fs.readFileSync(path.join(root, `${name}.glb`));
  assert.equal(glb.readUInt32LE(0), 0x46546c67);
  assert.equal(glb.readUInt32LE(4), 2);
  assert.equal(glb.readUInt32LE(8), glb.length);
  const gltf = JSON.parse(glb.subarray(20, 20 + glb.readUInt32LE(12)).toString());
  assert(gltf.meshes.length > 0);
  console.log(`${name}: ${vertices} vertices, ${m.index.length / 3} triangles, ${m.frames?.length || 0} walk frames; GLB valid`);
}
