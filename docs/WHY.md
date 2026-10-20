# Why sprite sheets?

Sprite sheets and texture atlases are a standard workflow for frame-based 2D game
animation. A game displays a rectangle from one shared texture and changes that
rectangle each animation frame. This tool turns a video into that game asset:
sampled frames, a packed PNG grid, ordered metadata, and engine import files.

- **Efficient rendering.** Sprites that share a texture can be batched, reducing
  texture switches and draw calls when the engine's material and render settings allow it.
- **Shared assets.** Many character instances can reuse the same texture and frame
  data rather than each storing its own copy of the animation images.
- **Direct animation control.** Choose FPS, pause, reverse, select poses, and connect
  frames to game logic through your engine's sprite animation system.
- **Fewer files to manage.** Load a sheet and its metadata instead of dozens of
  individual image files, with a consistent layout for agents and game engines.
- **Manageable memory budgets.** Choose frame count, cell resolution, and page size
  for the target device. Lower resolution and fewer frames reduce decoded texture
  memory; suitable engine texture compression can reduce it further.

Packing alone does **not** guarantee lower memory use than the same separate frames.
For example, this 1536×768 RGBA8 sheet is about **4.5 MiB** of pixel data before
GPU compression, mipmaps, or extra CPU copies—the same pixel budget as 72 separate
128×128 RGBA8 frames. Empty cells and oversized pages waste memory, and an MP4's
compressed file size is not a GPU memory measurement. See Unity's
[atlas rendering explanation](https://docs.unity3d.com/2022.3/Documentation/Manual/sprite-atlas.html)
and Phaser's [texture and frame model](https://docs.phaser.io/phaser/concepts/textures).
