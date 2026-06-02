"""Main level editor state class that orchestrates all modules."""

import json
from pathlib import Path

import pygame as pg

from tile import (
    BlockTile,
    ShortBlockTile,
    ShortSpikeTile,
    SolidBlockTile,
    YellowOrbTile,
    YellowPadTile,
    NormalSpikeTile,
    EndTriggerTile,
    ShipPortalTile
)

from render_utils import RenderUtils
from .coordinate_system import CoordinateSystem
from .block_manager import BlockManager
from .input_handler import InputHandler
from .file_manager import FileManager
from renderer import EditorRenderer
from .music_manager import MusicManager


class LevelEditorState:
    """Main state class for the level editor."""

    SCREEN_W = 1280
    SCREEN_H = 720

    MIN_ZOOM = 0.125
    MAX_ZOOM = 4.0
    ZOOM_FACTOR = 1.1

    palette = [
        "block",
        "block_short",
        "block_solid",
        "spike_norm",
        "spike_short",
        "orb_y",
        "pad_y",
        "portal_ship",
        "end_trig"
    ]

    tile_classes = {
        "block": BlockTile,
        "block_short": ShortBlockTile,
        "block_solid": SolidBlockTile,
        "spike_norm": NormalSpikeTile,
        "spike_short": ShortSpikeTile,
        "orb_y": YellowOrbTile,
        "pad_y": YellowPadTile,
        "portal_ship": ShipPortalTile,
        "end_trig": EndTriggerTile
    }

    def __init__(self, level_path=None):
        self.default_level_path = Path("levels") / "Fantasy" / "level.json"

        if level_path is None:
            level_path = Path("levels") / "Fantasy" / "level.json"
            level_path.parent.mkdir(parents=True, exist_ok=True)
            level_path.touch(exist_ok=True)

        elif isinstance(level_path, str):
            level_path = Path(level_path)

        self.level_path = level_path

    def enter(self, manager):
        """Initialize the state when entering."""
        self.manager = manager
        self.font = pg.font.SysFont(None, 24)
        self.font_big = pg.font.SysFont(None, 36)
        self.tile_size = 64
        self.toolbar_height = 48
        self.palette_height = 84

        game_h = self.SCREEN_H - self.toolbar_height - self.palette_height
        self.ground_y = self.toolbar_height + (game_h // self.tile_size) * self.tile_size

        self.start_x = 100
        self.grid_origin_x = self.start_x - self.tile_size // 2

        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0

        self.editor_mode = "build"  # "build" or "edit"
        self.selected_block_index = None
        self.selected_block_indices = set()

        self.selected_tile = "block"
        self.hover_grid = None
        self.message = ""
        self.message_timer = 0.0
        self.metadata = {"difficulty": 1}
        self.blocks = []

        self.swipe_mode = False
        self.last_swipe_grid = None

        self.edit_dragging = False
        self.edit_drag_last_grid = None
        self.selection_dragging = False
        self.selection_rect_start = None
        self.selection_rect_current = None

        # Initialize manager modules first (before building icons)
        self.coords = CoordinateSystem(self)
        self.blocks_mgr = BlockManager(self)
        self.input_handler = InputHandler(self)
        self.file_mgr = FileManager(self)
        self.renderer = EditorRenderer()
        self.music_mgr = MusicManager(self)

        self.load_level()
        self.palette_icons = self._build_palette_icons()

    def _build_palette_icons(self):
        """Build palette icons for each tile type."""
        icons = {}
        size = 52
        for tile_type, tile_class in self.tile_classes.items():
            surf = pg.Surface((size, size), pg.SRCALPHA)
            try:
                tile = tile_class((0, 0, size, size), None)
                RenderUtils._render_tile_compatible(tile, surf, 0.0, 0.0, zoom=1.0)
            except Exception:
                pg.draw.rect(surf, (100, 100, 100), (0, 0, size, size), border_radius=4)
            icons[tile_type] = surf
        return icons

    def load_level(self):
        """Load level from disk."""
        if not self.level_path.exists():
            self.blocks = []
            self.metadata = {"difficulty": 1}
            self.selected_block_index = None
            self.selected_block_indices.clear()
            return

        try:
            with open(self.level_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            self.blocks = []
            self.metadata = {"difficulty": 1}
            self.selected_block_index = None
            self.selected_block_indices.clear()
            return

        if isinstance(data, dict):
            raw_blocks = list(data.get("blocks") or data.get("tiles") or data.get("objects") or [])
            self.metadata = {key: value for key, value in data.items() if key not in ("blocks", "tiles", "objects")}
            normalized_blocks = []
            for block in raw_blocks:
                normalized = self.blocks_mgr.normalize_block(block)
                if normalized is not None:
                    normalized_blocks.append(normalized)
            self.blocks = normalized_blocks
        elif isinstance(data, list):
            normalized_blocks = []
            for block in data:
                normalized = self.blocks_mgr.normalize_block(block)
                if normalized is not None:
                    normalized_blocks.append(normalized)
            self.blocks = normalized_blocks
            self.metadata = {"difficulty": 1}
        else:
            self.blocks = []
            self.metadata = {"difficulty": 1}

        self.selected_block_index = None
        self.selected_block_indices.clear()

    def handle_event(self, event):
        """Handle pygame events."""
        self.input_handler.handle_event(event)

    def update(self, dt):
        """Update state."""
        self.music_mgr.update()
        
        keys = pg.key.get_pressed()

        pan_speed = 700 * dt
        if self.editor_mode != "edit" or not self.has_selection():
            if keys[pg.K_a]:
                self.camera_x -= pan_speed
            if keys[pg.K_d]:
                self.camera_x += pan_speed
            if keys[pg.K_w] and not (pg.KMOD_CTRL & pg.key.get_mods()):
                self.camera_y -= pan_speed
            if keys[pg.K_s]:
                if not (pg.KMOD_CTRL & pg.key.get_mods() | pg.KMOD_ALT & pg.key.get_mods()):
                    self.camera_y += pan_speed
            if keys[pg.K_1] and (pg.KMOD_CTRL & pg.key.get_mods()):
                self.editor_mode = "build"
            if keys[pg.K_2] and (pg.KMOD_CTRL & pg.key.get_mods()):
                self.editor_mode = "edit"

        if self.message_timer > 0:
            self.message_timer = max(0.0, self.message_timer - dt)

    def render(self, surface):
        """Render the level editor."""
        self.renderer.render(surface)

    def has_selection(self):
        """Check if blocks are selected."""
        return bool(self.selected_block_indices) or self.selected_block_index is not None

    def get_selected_indices(self):
        """Get indices of all selected blocks."""
        if self.selected_block_indices:
            return sorted(i for i in self.selected_block_indices if 0 <= i < len(self.blocks))
        if self.selected_block_index is not None and 0 <= self.selected_block_index < len(self.blocks):
            return [self.selected_block_index]
        return []

    def set_editor_mode(self, mode):
        """Set the editor mode (build or edit)."""
        if mode not in ("build", "edit"):
            return

        self.editor_mode = mode
        self.last_swipe_grid = None
        self.edit_dragging = False
        self.edit_drag_last_grid = None
        self.selection_dragging = False
        self.selection_rect_start = None
        self.selection_rect_current = None
        if mode == "edit":
            self.swipe_mode = False

    def palette_tile_at_pos(self, pos):
        """Get the palette tile type at a screen position."""
        for index, tile_type in enumerate(self.palette):
            if self.palette_rect(index).collidepoint(pos):
                return tile_type
        return None

    def palette_rect(self, index):
        """Get the screen rect for a palette item."""
        btn_w, btn_h = 70, 72
        gap = 14
        total = len(self.palette) * (btn_w + gap) - gap
        start_x = (self.SCREEN_W - total) // 2
        y = (self.SCREEN_H - self.palette_height) + (self.palette_height - btn_h) // 2
        return pg.Rect(start_x + index * (btn_w + gap), y, btn_w, btn_h)

    # Button rects for toolbar and UI
    def playtest_button_rect(self):
        w, h = 64, 32
        x = self.SCREEN_W - w - 16
        y = (self.toolbar_height - h) // 2
        return pg.Rect(x, y, w, h)

    def open_button_rect(self):
        w, h = 64, 32
        x = self.SCREEN_W - w * 2 - 32
        y = (self.toolbar_height - h) // 2
        return pg.Rect(x, y, w, h)

    def new_button_rect(self):
        w, h = 64, 32
        x = self.SCREEN_W - w * 3 - 48
        y = (self.toolbar_height - h) // 2
        return pg.Rect(x, y, w, h)

    def level_options_button_rect(self):
        w, h = 132, 32
        x = self.SCREEN_W - w * 3 + 12
        y = (self.toolbar_height - h) // 2
        return pg.Rect(x, y, w, h)

    def delete_level_button_rect(self):
        w, h = 132, 32
        x = self.SCREEN_W - w * 4
        y = (self.toolbar_height - h) // 2
        return pg.Rect(x, y, w, h)

    def build_button_rect(self):
        return pg.Rect(10, self.toolbar_height + 28, 96, 40)

    def edit_button_rect(self):
        return pg.Rect(10, self.toolbar_height + 76, 96, 40)

    def swipe_button_rect(self):
        w, h = 64, 64
        x = self.SCREEN_W - w - 16
        y = self.SCREEN_H - self.palette_height + (self.palette_height - h) // 2
        return pg.Rect(x, y, w, h)

    def music_button_rect(self):
        """Get the screen rect for the music toggle button in toolbar."""
        w, h = 64, 32
        x = 16
        y = (self.toolbar_height - h) // 2
        return pg.Rect(x, y, w, h)
