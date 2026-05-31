import os
from pathlib import Path

import pygame as pg

from .level import LevelMixin
from .player import PlayerMixin
from .rendering import RenderingMixin


class GameState(PlayerMixin, LevelMixin, RenderingMixin):
    def __init__(self, level_path=None, playtest_mode=False):
        self.level_path = level_path
        self.playtest_mode = playtest_mode

    def enter(self, manager):
        self.manager = manager
        self.font = pg.font.SysFont(None, 28)
        self.level_song_path = None
        self.music_loaded = False
        self.level_started = False
        self.level_sync_started = False
        self.level_sync_started_at = 0.0
        self.level_start_delay = 0.0
        self.level_time = 0.0
        self.is_dead = False
        self.death_timer = 0.0
        self.death_duration = 1.0
        self.death_pos = None
        self.attempts = 1

        self.setup_player()
        self.setup_world()
        self.snap_player_start_to_ground()
        self.load_initial_level()

    def setup_player(self):
        self.player_size = pg.Vector2(64, 64)
        self.pos = pg.Vector2(100, 300)
        self.start_x = int(self.pos.x)
        self.start_pos = self.pos.copy()

        self.vel = pg.Vector2(330, 0)
        self.speed = 450
        self.jump_impulse = -1080
        self.gravity = 3600
        self.on_ground = False

        self.coyote_time = 0.15
        self.coyote_timer = 0.0
        self.jump_cooldown = 0.12
        self.jump_cooldown_timer = 0.0
        
        # Ship mode state
        self.is_ship_mode = False
        self.ship_vertical_accel = self.gravity  # Acceleration when pressing UP

    def setup_world(self):
        self.tile_size = int(self.player_size.x)
        self.blocks = []
        self.grid_origin_x = self.start_x - (self.tile_size // 2)
        self.camera_x = 0
        self.camera_y = 0

        self.ground_y = (600 // self.tile_size) * self.tile_size
        self.platforms = [
            pg.Rect(self.start_x - 2000, self.ground_y, 50000, 1600),
        ]

    def snap_player_start_to_ground(self):
        self.start_pos.y = self.ground_y - self.player_size.y / 2
        self.pos = self.start_pos.copy()

    def load_initial_level(self):
        level_path = self.level_path or self.find_default_level()
        if level_path and os.path.exists(level_path):
            self.level_path = level_path
            self.load_level(level_path)
            self.level_song_path = self.find_level_song(level_path)
            self.level_start_delay = float(getattr(self, "level_metadata", {}).get("startDelay", 0.0))
            self.preload_level_music()
            self.begin_level_sync()
        else:
            self.build_blocks()

    def start_level_run_if_ready(self):
        if self.level_started:
            return True

        if not self.level_sync_started:
            self.begin_level_sync()

        if getattr(self.manager, "is_transitioning", False):
            return False

        if self.music_loaded and self.level_sync_elapsed() < self.level_start_delay:
            return False

        self.level_time = 0.0
        self.level_started = True
        self.start_level_music()
        return True

    def begin_level_sync(self):
        self.reset_player_for_level_start()
        self.level_time = 0.0
        self.level_started = False
        self.level_sync_started = True
        self.level_sync_started_at = pg.time.get_ticks() / 1000.0
        self.is_dead = False
        self.death_timer = 0.0
        self.death_pos = None

    def restart_level_run(self):
        self.begin_level_sync()
        self.attempts += 1

    def level_sync_elapsed(self):
        return pg.time.get_ticks() / 1000.0 - self.level_sync_started_at

    def reset_player_for_level_start(self):
        self.pos = self.start_pos.copy()
        self.vel = pg.Vector2(self.speed, 0)
        self.on_ground = False
        self.coyote_timer = 0.0
        self.jump_cooldown_timer = 0.0
        self.camera_x = 0
        self.camera_y = 0
        self.mode = "cube"

    def die(self):
        if self.is_dead:
            return

        self.is_dead = True
        self.death_timer = 0.0
        self.death_pos = self.pos.copy()
        self.vel = pg.Vector2(0, 0)
        self.stop_level_music()

    def start_level_music(self):
        if not self.music_loaded:
            return

        try:
            pg.mixer.music.play()
        except pg.error:
            pass

    def stop_level_music(self):
        try:
            if pg.mixer.get_init():
                pg.mixer.music.stop()
        except pg.error:
            pass

    def preload_level_music(self):
        self.music_loaded = False
        if self.level_song_path is None:
            return

        try:
            if not pg.mixer.get_init():
                pg.mixer.init(44100, -16, 2, 512)
            pg.mixer.music.load(str(self.level_song_path))
            self.music_loaded = True
        except pg.error:
            self.music_loaded = False

    def find_level_song(self, level_path):
        level_file = Path(level_path)
        default_song = level_file.parent / "song.mp3"
        if default_song.exists():
            return default_song

        return None

    def exit(self):
        self.stop_level_music()
