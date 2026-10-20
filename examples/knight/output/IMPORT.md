# Phaser import

Copy the PNG sheets, atlas JSON files, and phaser.mjs into your game's public asset folder.
Import preloadVideoSprites and createVideoAnimation from phaser.mjs in your scene module.
Call preloadVideoSprites(this, 'assets/character', 'character') from preload().
Call createVideoAnimation(this, 'character-run', 'character') from create().
Create a sprite using texture 'character_p0' and frame 'frame_000000', then play 'character-run'.

The helper loads every page, preserves exported frame order, and uses the conversion's FPS.
Its repeat argument defaults to -1 (loop forever); set 0 for one playback.
ES module syntax and the loading/animation calls are tested. Verify playback in your Phaser version.
