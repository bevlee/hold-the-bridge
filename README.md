# Hold the Bridge

A browser game in the style of the "shoot the gates" mobile ads, built with three.js. Stick-figure crews fire automatically while you steer them across a walled bridge.

**Play:** https://bevlee.github.io/hold-the-bridge/

## Modes

- **Bridge run:** endless. Shoot gates to raise them (+N, ×, ÷), crack barrels and weapon crates for upgrades, dodge rolling tyres, and beat a boss after every third upgrade row. The run ends if an enemy crosses the red line or your crew is wiped out.
- **Three lanes:** a walled three-column level. A dense horde comes down the middle, +1 gates run down the right, and toilet rolls on the left hide upgrades under big health pools. Every third roll calls an armored boss that only a Boss Breaker can hurt. Beat three bosses to win.

## Controls

Drag anywhere, or hold ← → / A D.

## Development

It's a single `index.html` with no build step. Serve the folder with any static server, for example:

```bash
python3 -m http.server 8765
```

Add `?speed=4` to the URL to fast-forward the simulation while tuning.
