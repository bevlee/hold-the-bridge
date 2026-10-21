# Anime bridge kit

Original low-poly models created in Blender for Hold the Bridge. Teal-haired chibi crew with a sci-fi rifle, coral oni drones, gold-horned samurai boss, energy capsule, supply case, and illuminated bridge pylon. Navy, ivory, mint, coral and gold palette.

- `anime-kit.blend`: editable source with named model parts, materials, lighting and contact-sheet camera.
- `*.glb`: six standalone static models with embedded materials, exported at game scale. Blender uses Z-up; glTF handles its standard coordinate conversion.
- `models.js`: game-ready Y-up geometry, facing −Z, with linear vertex colors and eight baked walk frames for each character. The game shares geometry and uses a single toon material per actor, without texture downloads or a GLTF loader.
- `lineup.png`: rendered contact sheet.
- `manifest.json`: geometry counts.

The GLBs contain the neutral static pose. Walk frames are in `models.js`; these are baked geometry frames rather than skeletal animations. The Blender file arranges the assets for the contact sheet; the generator exports each model at its original game scale before arranging the sheet.

Regenerate from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b -t 4 --python tools/build_anime_assets.py
node tools/check_anime_assets.cjs
```

Both modes use the character kit, energy cells and lanterns. Bridge run also uses the supply cases. Gate numbers, health labels, projectiles and tyre hazards retain their existing readable shapes. Collisions, rewards and difficulty follow the existing game logic.
