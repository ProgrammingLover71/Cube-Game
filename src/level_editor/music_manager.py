"""Music management for the level editor."""

from pathlib import Path
import pygame as pg


class MusicManager:
    """Handles music playback in the level editor."""

    def __init__(self, state):
        self.state = state
        self.music_loaded = False
        self.is_playing = False
        self.song_path = None
        self.music_duration = 0.0  # Duration in seconds
        self.play_start_time = 0.0  # Time (in seconds) when music started playing
        self.play_start_music_pos = 0.0  # Music position (in seconds) when started

    def find_level_song(self):
        """Find the song for the current level."""
        if not self.state.level_path:
            return None

        level_file = Path(self.state.level_path)
        default_song = level_file.parent / "song.mp3"
        if default_song.exists():
            return default_song

        return None

    def load_music(self):
        """Load the level song."""
        self.music_loaded = False
        self.song_path = self.find_level_song()

        if self.song_path is None:
            return False

        try:
            if not pg.mixer.get_init():
                pg.mixer.init(44100, -16, 2, 512)
            pg.mixer.music.load(str(self.song_path))
            self.music_duration = pg.mixer.Sound(str(self.song_path)).get_length()
            self.music_loaded = True
            return True
        except pg.error:
            self.music_loaded = False
            return False

    def calculate_music_position(self):
        """Calculate the music position based on camera position and level bounds."""
        if not self.state.blocks or self.music_duration <= 0:
            return 0.0

        # Find level bounds (min/max x positions)
        min_x = min((block[1] for block in self.state.blocks if len(block) > 1), default=0)
        max_x = max((block[1] for block in self.state.blocks if len(block) > 1), default=100)

        level_width = max_x - min_x if max_x > min_x else 100
        
        # Calculate position in level (0 to 1) based on camera
        # Center of camera view in world coordinates
        camera_center_x = self.state.camera_x + self.state.SCREEN_W / (2 * self.state.zoom)
        level_position = (camera_center_x - min_x) / level_width
        level_position = max(0.0, min(1.0, level_position))  # Clamp to 0-1

        # Map to music position
        music_position = level_position * self.music_duration
        return music_position

    def play(self):
        """Start playing the music from the position based on camera."""
        if not self.music_loaded:
            if not self.load_music():
                return False

        try:
            if pg.mixer.music.get_busy():
                pg.mixer.music.stop()
            
            # Calculate the position based on camera
            music_pos = self.calculate_music_position()
            self.play_start_music_pos = music_pos
            self.play_start_time = pg.time.get_ticks() / 1000.0  # Current time in seconds
            
            # Try to set position before playing
            try:
                pg.mixer.music.set_pos(music_pos)
            except (pg.error, AttributeError):
                # If set_pos fails, we'll just play from start
                self.play_start_music_pos = 0.0
            
            pg.mixer.music.play()
            self.is_playing = True
            return True
        except pg.error:
            return False

    def get_current_position(self):
        """Get the current music playback position in seconds."""
        if not self.is_playing:
            return 0.0

        # Calculate position based on elapsed time since we started playing
        current_time = pg.time.get_ticks() / 1000.0
        elapsed = current_time - self.play_start_time
        position = self.play_start_music_pos + elapsed

        # Make sure we don't go past the duration
        if position > self.music_duration:
            self.is_playing = False
            return self.music_duration

        return position

    def stop(self):
        """Stop the music."""
        try:
            if pg.mixer.get_init():
                pg.mixer.music.stop()
            self.is_playing = False
            return True
        except pg.error:
            return False

    def toggle(self):
        """Toggle music playback."""
        if self.is_playing:
            return self.stop()
        else:
            return self.play()

    def update(self):
        """Update music state (check if still playing)."""
        if self.is_playing:
            try:
                if not pg.mixer.music.get_busy():
                    self.is_playing = False
            except pg.error:
                self.is_playing = False

    def cleanup(self):
        """Stop music and clean up resources."""
        self.stop()
