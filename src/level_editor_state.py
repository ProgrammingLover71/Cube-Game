import json
import math
from os import mkdir
from pathlib import Path

import pygame as pg

from game_state.tile import (
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


class LevelEditorState:
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

        self.load_level()
        self.palette_icons = self._build_palette_icons()

    def _build_palette_icons(self):
        icons = {}
        size = 52
        for tile_type, tile_class in self.tile_classes.items():
            surf = pg.Surface((size, size), pg.SRCALPHA)
            try:
                tile = tile_class((0, 0, size, size), None)
                self._render_tile_compatible(tile, surf, 0.0, 0.0, 1.0)
            except Exception:
                pg.draw.rect(surf, (100, 100, 100), (0, 0, size, size), border_radius=4)
            icons[tile_type] = surf
        return icons

    def load_level(self):
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
                normalized = self.normalize_block(block)
                if normalized is not None:
                    normalized_blocks.append(normalized)
            self.blocks = normalized_blocks
        elif isinstance(data, list):
            normalized_blocks = []
            for block in data:
                normalized = self.normalize_block(block)
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
        if event.type == pg.KEYDOWN:
            self.handle_keydown(event.key)
        
        if event.type == pg.KEYUP:
            self.handle_keyup(event.key)

        elif event.type == pg.MOUSEMOTION:
            self.hover_grid = self.screen_to_grid(event.pos)
            self.handle_swipe_motion(event)
            self.handle_edit_drag_motion(event)
            self.handle_selection_drag(event)

        elif event.type == pg.MOUSEBUTTONDOWN:
            self.handle_mouse_down(event)

        elif event.type == pg.MOUSEBUTTONUP:
            if event.button in (1, 3):
                self.last_swipe_grid = None
            if event.button == 1:
                if self.selection_dragging:
                    self.finish_box_selection()
                self.edit_dragging = False
                self.edit_drag_last_grid = None

        elif event.type == pg.MOUSEWHEEL:
            mods = pg.key.get_mods()

            if mods & pg.KMOD_CTRL:
                self.zoom_at(pg.mouse.get_pos(), event.y)
            elif mods & pg.KMOD_SHIFT:
                self.camera_x -= event.y * self.tile_size
            else:
                self.camera_y -= event.y * self.tile_size

    ############################################################################################################
    ## KEY SHIT OVER HERE :)
    ############################################################################################################

    def update(self, dt):
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


    def handle_keyup(self, key):
        mods = pg.key.get_mods()

        if key == pg.K_s and (mods & pg.KMOD_ALT):
            # We released Alt+S, so toggle Swipe mode
            if self.editor_mode == "build":
                self.swipe_mode = not self.swipe_mode
                self.last_swipe_grid = None


    def handle_keydown(self, key):
        mods = pg.key.get_mods()

        if self.editor_mode == "edit" and self.has_selection():
            if self.handle_edit_keydown(key, mods):
                return

        if key in (pg.K_ESCAPE, pg.K_BACKSPACE):
            from menu_state import MenuState
            self.manager.change(MenuState())
        elif key == pg.K_s:
            if mods & pg.KMOD_CTRL:
                self.save_level()
        elif key == pg.K_RETURN:
            self.start_playtest()
        elif key == pg.K_o:
            if mods & pg.KMOD_LSHIFT:
                self.open_options()
            else:
                self.open_level()
        elif key == pg.K_n:
            if mods & pg.KMOD_CTRL:
                self.new_level()
        elif key == pg.K_LEFT:
            self.camera_x -= self.tile_size
        elif key == pg.K_RIGHT:
            self.camera_x += self.tile_size
        elif key == pg.K_UP:
            self.camera_y -= self.tile_size
        elif key == pg.K_DOWN:
            self.camera_y += self.tile_size
        elif key in (pg.K_EQUALS, pg.K_KP_PLUS):
            self.zoom_at(pg.mouse.get_pos(), 1)
        elif key in (pg.K_MINUS, pg.K_KP_MINUS):
            self.zoom_at(pg.mouse.get_pos(), -1)
        elif pg.K_1 <= key <= pg.K_6:
            self.selected_tile = self.palette[key - pg.K_1]


    def handle_edit_keydown(self, key, mods):
        if not self.has_selection():
            return False

        moved = False
        rotated = False
        step = 0.5 if (mods & pg.KMOD_SHIFT) else 1.0

        if key == pg.K_LEFT:
            self.move_selected_blocks(-step, 0.0)
            moved = True
        elif key == pg.K_RIGHT:
            self.move_selected_blocks(step, 0.0)
            moved = True
        elif key == pg.K_UP:
            self.move_selected_blocks(0.0, step)
            moved = True
        elif key == pg.K_DOWN:
            self.move_selected_blocks(0.0, -step)
            moved = True
        elif key == pg.K_q:
            self.rotate_selected_blocks(-90)
            rotated = True
        elif key == pg.K_e:
            self.rotate_selected_blocks(90)
            rotated = True
        elif key == pg.K_DELETE:
            self.delete_selected_blocks()
            return True

        return moved or rotated

    ############################################################################################################
    ##  MOUSE SHIT OVER HERE :)
    ############################################################################################################

    def handle_mouse_down(self, event):
        mouse_pos = event.pos

        if event.button == 1:
            if self.playtest_button_rect().collidepoint(mouse_pos):
                self.start_playtest()
                return

            if self.open_button_rect().collidepoint(mouse_pos):
                self.open_level()
                return
            
            if self.new_button_rect().collidepoint(mouse_pos):
                self.new_level()
                return

            if self.level_options_button_rect().collidepoint(mouse_pos):
                self.open_options()
                return
            
            if self.delete_level_button_rect().collidepoint(mouse_pos):
                self.delete_level()
                return

            if self.build_button_rect().collidepoint(mouse_pos):
                self.set_editor_mode("build")
                return

            if self.edit_button_rect().collidepoint(mouse_pos):
                self.set_editor_mode("edit")
                return

            if self.swipe_button_rect().collidepoint(mouse_pos):
                if self.editor_mode == "build":
                    self.swipe_mode = not self.swipe_mode
                    self.last_swipe_grid = None
                return

        palette_tile = self.palette_tile_at_pos(mouse_pos)
        if palette_tile:
            self.selected_tile = palette_tile
            return

        if self.editor_mode == "edit":
            if event.button == 1:
                hit = self.find_block_at_pos(mouse_pos)
                if hit is not None:
                    self.selected_block_index = hit
                    self.selected_block_indices = {hit}
                    self.edit_dragging = True
                    self.selection_dragging = False
                    self.selection_rect_start = None
                    self.selection_rect_current = None
                    self.edit_drag_last_grid = self.screen_to_grid(mouse_pos)
                else:
                    self.selected_block_index = None
                    self.selected_block_indices.clear()
                    self.edit_dragging = False
                    self.edit_drag_last_grid = None
                    self.selection_dragging = True
                    self.selection_rect_start = mouse_pos
                    self.selection_rect_current = mouse_pos
                return

            if event.button == 3:
                hit = self.find_block_at_pos(mouse_pos)
                if hit is not None:
                    self.delete_block(hit)
                return

        grid_pos = self.screen_to_grid(mouse_pos)
        if grid_pos is None:
            return

        if self.editor_mode != "build":
            return

        if event.button == 1:
            self.place_block(*grid_pos)
            if self.swipe_mode:
                self.last_swipe_grid = (*grid_pos, 1)
        elif event.button == 3:
            self.erase_block(*grid_pos)
            if self.swipe_mode:
                self.last_swipe_grid = (*grid_pos, 3)





    def handle_swipe_motion(self, event):
        if not self.swipe_mode or self.editor_mode != "build":
            return

        buttons = event.buttons
        left_held = buttons[0]
        right_held = buttons[2]

        if not left_held and not right_held:
            self.last_swipe_grid = None
            return

        grid_pos = self.screen_to_grid(event.pos)
        if grid_pos is None:
            self.last_swipe_grid = None
            return

        if left_held:
            tag = (*grid_pos, 1)
            if self.last_swipe_grid != tag:
                self.place_block(*grid_pos)
                self.last_swipe_grid = tag
        elif right_held:
            tag = (*grid_pos, 3)
            if self.last_swipe_grid != tag:
                self.erase_block(*grid_pos)
                self.last_swipe_grid = tag


    def handle_edit_drag_motion(self, event):
        if self.editor_mode != "edit":
            return

        if self.edit_dragging and self.has_selection():
            if not event.buttons or not event.buttons[0]:
                return

            grid_pos = self.screen_to_grid(event.pos)
            if grid_pos is None:
                return

            if self.edit_drag_last_grid is None:
                self.edit_drag_last_grid = grid_pos
                return

            if grid_pos == self.edit_drag_last_grid:
                return

            dx = grid_pos[0] - self.edit_drag_last_grid[0]
            dy = grid_pos[1] - self.edit_drag_last_grid[1]

            if dx or dy:
                self.move_selected_blocks(dx, dy)
                self.edit_drag_last_grid = grid_pos





    def handle_selection_drag(self, event):
        if not self.selection_dragging:
            return

        self.selection_rect_current = event.pos

    def finish_box_selection(self):
        self.selection_dragging = False

        if not self.selection_rect_start or not self.selection_rect_current:
            self.selection_rect_start = None
            self.selection_rect_current = None
            return

        x1, y1 = self.selection_rect_start
        x2, y2 = self.selection_rect_current

        selection_rect = pg.Rect(
            min(x1, x2),
            min(y1, y2),
            abs(x2 - x1),
            abs(y2 - y1),
        )

        self.selected_block_indices.clear()

        for i, block in enumerate(self.blocks):
            rect = self.block_rect(block)
            if rect is None:
                continue

            screen_rect = self.world_rect_to_screen(rect)
            if selection_rect.colliderect(screen_rect):
                self.selected_block_indices.add(i)

        self.selected_block_index = next(iter(self.selected_block_indices)) if self.selected_block_indices else None
        self.selection_rect_start = None
        self.selection_rect_current = None

    def has_selection(self):
        return bool(self.selected_block_indices) or self.selected_block_index is not None

    def get_selected_indices(self):
        if self.selected_block_indices:
            return sorted(i for i in self.selected_block_indices if 0 <= i < len(self.blocks))
        if self.selected_block_index is not None and 0 <= self.selected_block_index < len(self.blocks):
            return [self.selected_block_index]
        return []

    def set_editor_mode(self, mode):
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

    def normalize_rotation(self, rotation):
        try:
            return int(round(float(rotation))) % 360
        except Exception:
            return 0

    def normalize_block(self, block):
        if isinstance(block, list):
            if len(block) < 3:
                return None

            tile_type = block[0]
            grid_x = block[1]
            grid_y = block[2]
            color = None
            scale = 1
            rotation = 0

            tail = list(block[3:])

            if tail:
                first = tail[0]
                if self.is_scale_value(first):
                    scale = first
                    if len(tail) >= 2:
                        rotation = tail[1]
                else:
                    color = first
                    if len(tail) >= 2:
                        second = tail[1]
                        if self.is_scale_value(second):
                            scale = second
                            if len(tail) >= 3:
                                rotation = tail[2]
                        else:
                            rotation = second
                            if len(tail) >= 3 and self.is_scale_value(tail[2]):
                                scale = tail[2]

            return [tile_type, grid_x, grid_y, color, scale, self.normalize_rotation(rotation)]

        if isinstance(block, dict):
            return [
                block.get("type"),
                block.get("x"),
                block.get("y"),
                block.get("color"),
                block.get("scale", 1),
                self.normalize_rotation(block.get("rotation", 0)),
            ]

        return None

    def place_block(self, grid_x, grid_y):
        self.erase_block(grid_x, grid_y)
        self.blocks.append([self.selected_tile, grid_x, grid_y, None, 1, 0])

    def erase_block(self, grid_x, grid_y):
        removed_any = False
        new_blocks = []
        for i, block in enumerate(self.blocks):
            if self.block_grid_pos(block) != (grid_x, grid_y):
                new_blocks.append(block)
            else:
                removed_any = True
                if self.selected_block_index == i:
                    self.selected_block_index = None
                elif self.selected_block_index is not None and self.selected_block_index > i:
                    self.selected_block_index -= 1

                if i in self.selected_block_indices:
                    self.selected_block_indices.discard(i)

        self.blocks = new_blocks

        if removed_any:
            self.selected_block_indices = {
                (idx - 1 if idx > -1 else idx)
                for idx in self.selected_block_indices
                if 0 <= idx < len(self.blocks)
            }

            self.selected_block_indices = {
                idx for idx in self.selected_block_indices
                if 0 <= idx < len(self.blocks)
            }

            if self.selected_block_index is not None and self.selected_block_index >= len(self.blocks):
                self.selected_block_index = len(self.blocks) - 1 if self.blocks else None

    def delete_block(self, index):
        if not (0 <= index < len(self.blocks)):
            return

        del self.blocks[index]

        if self.selected_block_index == index:
            self.selected_block_index = None
        elif self.selected_block_index is not None and self.selected_block_index > index:
            self.selected_block_index -= 1

        if self.selected_block_indices:
            updated = set()
            for idx in self.selected_block_indices:
                if idx == index:
                    continue
                if idx > index:
                    updated.add(idx - 1)
                else:
                    updated.add(idx)
            self.selected_block_indices = updated

        if self.selected_block_index is not None and self.selected_block_index >= len(self.blocks):
            self.selected_block_index = len(self.blocks) - 1 if self.blocks else None

        if self.selected_block_index is None and self.selected_block_indices:
            self.selected_block_index = next(iter(sorted(self.selected_block_indices)))

    def delete_selected_blocks(self):
        indices = self.get_selected_indices()
        if not indices:
            return

        for index in sorted(indices, reverse=True):
            self.delete_block(index)

        self.selected_block_index = None
        self.selected_block_indices.clear()

    def move_selected_block(self, dx, dy):
        if self.selected_block_index is None or not (0 <= self.selected_block_index < len(self.blocks)):
            return

        block = self.blocks[self.selected_block_index]
        block[1] = round((float(block[1]) + float(dx)) * 2) / 2
        block[2] = round((float(block[2]) + float(dy)) * 2) / 2

    def move_selected_blocks(self, dx, dy):
        indices = self.get_selected_indices()
        if not indices:
            return

        for index in indices:
            if not (0 <= index < len(self.blocks)):
                continue
            block = self.blocks[index]
            block[1] = round((float(block[1]) + float(dx)) * 2) / 2
            block[2] = round((float(block[2]) + float(dy)) * 2) / 2

    def rotate_selected_block(self, delta_degrees):
        if self.selected_block_index is None or not (0 <= self.selected_block_index < len(self.blocks)):
            return

        block = self.blocks[self.selected_block_index]
        while len(block) < 6:
            block.append(0)

        block[5] = self.normalize_rotation(block[5] + delta_degrees)

    def rotate_selected_blocks(self, delta_degrees):
        indices = self.get_selected_indices()
        if not indices:
            return

        for index in indices:
            if not (0 <= index < len(self.blocks)):
                continue

            block = self.blocks[index]
            while len(block) < 6:
                block.append(0)

            block[5] = self.normalize_rotation(block[5] + delta_degrees)

    def find_block_at_pos(self, pos):
        world_x, world_y = self.screen_to_world(pos)

        for index in range(len(self.blocks) - 1, -1, -1):
            block = self.blocks[index]
            rect = self.block_rect(block)
            if rect and rect.collidepoint(world_x, world_y):
                return index

        return None

    def block_rect(self, block):
        normalized = self.normalize_block(block)
        if normalized is None:
            return None

        _, grid_x, grid_y, _, scale, _rotation = normalized
        rect = self.level_rect_from_grid(grid_x, grid_y, scale)
        if rect is None:
            return None

        return pg.Rect(rect)

    def block_grid_pos(self, block):
        normalized = self.normalize_block(block)
        if normalized is None:
            return None

        return normalized[1], normalized[2]

    def save_level(self):
        self.level_path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(self.metadata)

        normalized_blocks = []
        for block in self.blocks:
            normalized = self.normalize_block(block)
            if normalized is not None:
                normalized_blocks.append(normalized)

        data["blocks"] = normalized_blocks
        with open(self.level_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        self.message = f"Saved {self.level_path}"
        self.message_timer = 2.0

    def start_playtest(self):
        self.save_level()
        try:
            from game_state.game_state import GameState
            self.manager.change(GameState(self.level_path, True))
        except Exception as exc:
            self.message = f"Playtest failed: {exc}"
            self.message_timer = 3.0

    def open_level(self):
        self.save_level()
        from level_select_state import LevelSelectState
        self.manager.change(LevelSelectState(self.level_path.parent, True))
    
    def new_level(self):
        self.save_level()
        # Create a new level path with an incremented name
        base_name = "Unnamed Level"
        counter = 1
        while (self.level_path.parent / f"{base_name} {counter}.json").exists():
            counter += 1
        level_name = f"{base_name} {counter}"
        level_path = Path("levels") / level_name / "level.json"
        mkdir(level_path.parent)
        level_path.touch(exist_ok=True)
        from level_editor_state import LevelEditorState
        self.manager.change(LevelEditorState(level_path))
    
    def delete_level(self):
        import tkinter as tk
        from tkinter import messagebox

        level_name = self.level_path.parent.name or self.level_path.stem

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        confirmed = messagebox.askyesno(
            title="Delete Level",
            message=f'Are you sure you want to delete "{level_name}"? This action CANNOT be undone.',
            icon=messagebox.WARNING,
        )
        root.destroy()

        if not confirmed:
            return

        if self.level_path.exists():
            self.level_path.unlink()
            parent = self.level_path.parent
            if parent.exists() and parent.is_dir():
                try:
                    parent.rmdir()
                except OSError:
                    pass

        from level_editor_state import LevelEditorState
        self.manager.change(LevelEditorState(self.default_level_path))

    def open_options(self):
        self.save_level()
        from level_options_state import LevelOptionsState
        self.manager.change(LevelOptionsState(self))

    def render(self, surface):
        surface.fill((80, 160, 240))
        self.render_grid(surface)
        self.render_blocks(surface)
        self.render_ground(surface)
        self.render_toolbar(surface)
        self.render_mode_buttons(surface)
        self.render_palette(surface)
        if self.selection_dragging and self.selection_rect_start and self.selection_rect_current:
            self.render_selection_box(surface)

    def world_to_screen(self, x, y):
        return (
            int((x - self.camera_x) * self.zoom),
            int((y - self.camera_y) * self.zoom),
        )

    def screen_to_world(self, pos):
        x, y = pos
        return (
            self.camera_x + x / self.zoom,
            self.camera_y + y / self.zoom,
        )

    def screen_to_grid(self, pos):
        x, y = pos
        if y < self.toolbar_height or y >= self.SCREEN_H - self.palette_height:
            return None

        world_x, world_y = self.screen_to_world(pos)
        grid_x = int((world_x - self.grid_origin_x) / self.tile_size)
        grid_y = int((self.ground_y - world_y) / self.tile_size)
        return grid_x, grid_y

    def zoom_at(self, screen_pos, direction):
        if direction == 0:
            return

        before = self.screen_to_world(screen_pos)
        factor = self.ZOOM_FACTOR if direction > 0 else 1.0 / self.ZOOM_FACTOR
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))

        if abs(new_zoom - self.zoom) < 1e-9:
            return

        sx, sy = screen_pos
        self.zoom = new_zoom
        self.camera_x = before[0] - sx / self.zoom
        self.camera_y = before[1] - sy / self.zoom

    def render_grid(self, surface):
        width, height = surface.get_size()

        world_left = self.camera_x
        world_top = self.camera_y
        world_right = self.camera_x + width / self.zoom
        world_bottom = self.camera_y + height / self.zoom

        first_x = self.grid_origin_x + math.floor((world_left - self.grid_origin_x) / self.tile_size) * self.tile_size
        last_x = world_right + self.tile_size

        x = first_x
        while x <= last_x:
            sx, _ = self.world_to_screen(x, world_top)
            pg.draw.line(surface, (90, 170, 245), (sx, 0), (sx, height))
            x += self.tile_size

        first_y = self.ground_y - math.floor((self.ground_y - world_top) / self.tile_size) * self.tile_size
        last_y = world_bottom + self.tile_size

        y = first_y
        while y <= last_y:
            _, sy = self.world_to_screen(world_left, y)
            pg.draw.line(surface, (90, 170, 245), (0, sy), (width, sy))
            y += self.tile_size

        if self.hover_grid is not None:
            rect = self.grid_rect(*self.hover_grid)
            screen_rect = self.world_rect_to_screen(rect)
            pg.draw.rect(surface, (255, 255, 255), screen_rect, width=max(1, int(2 * self.zoom)))

    def render_blocks(self, surface):
        for index, block in enumerate(self.blocks):
            tile = self.tile_from_block(block)
            if tile:
                self.render_tile(surface, tile)

        if self.editor_mode == "edit":
            if self.selected_block_indices:
                self.render_selected_block_outlines(surface)
            elif self.selected_block_index is not None:
                self.render_selected_block_outline(surface)

    def render_tile(self, surface, tile):
        rotation = self.normalize_rotation(getattr(tile, "_editor_rotation", 0))

        if rotation % 360 == 0:
            self._render_tile_compatible(tile, surface, self.camera_x, self.camera_y, self.zoom)
            return

        rect = tile.rect
        temp_w = max(1, int(rect.w * self.zoom))
        temp_h = max(1, int(rect.h * self.zoom))
        temp = pg.Surface((temp_w, temp_h), pg.SRCALPHA)

        try:
            tile.render(temp, camera_x=rect.x, camera_y=rect.y, zoom=self.zoom)
        except TypeError:
            try:
                tile.render(temp, rect.x, rect.y, self.zoom)
            except TypeError:
                try:
                    tile.render(temp, rect.x, rect.y)
                except TypeError:
                    tile.render(temp)

        rotated = pg.transform.rotate(temp, -rotation)
        screen_center = self.world_to_screen(rect.centerx, rect.centery)
        blit_rect = rotated.get_rect(center=screen_center)
        surface.blit(rotated, blit_rect)

    def render_selected_block_outline(self, surface):
        if not (0 <= self.selected_block_index < len(self.blocks)):
            return

        block = self.blocks[self.selected_block_index]
        rect = self.block_rect(block)
        if rect is None:
            return

        screen_rect = self.world_rect_to_screen(rect)
        pg.draw.rect(surface, (255, 255, 0), screen_rect, width=max(1, int(3 * self.zoom)))

    def render_selected_block_outlines(self, surface):
        for index in self.get_selected_indices():
            if not (0 <= index < len(self.blocks)):
                continue

            rect = self.block_rect(self.blocks[index])
            if rect is None:
                continue

            screen_rect = self.world_rect_to_screen(rect)
            pg.draw.rect(surface, (255, 255, 0), screen_rect, width=max(1, int(3 * self.zoom)))

    def render_selection_box(self, surface):
        x1, y1 = self.selection_rect_start
        x2, y2 = self.selection_rect_current

        rect = pg.Rect(
            min(x1, x2),
            min(y1, y2),
            abs(x2 - x1),
            abs(y2 - y1),
        )

        pg.draw.rect(surface, (120, 180, 255), rect, 2)

    def render_ground(self, surface):
        ground_screen_y = int((self.ground_y - self.camera_y) * self.zoom)

        if ground_screen_y >= surface.get_height():
            return

        rect = pg.Rect(
            0,
            ground_screen_y,
            surface.get_width(),
            surface.get_height() - ground_screen_y,
        )
        pg.draw.rect(surface, (35, 95, 150), rect)

        line_y = ground_screen_y
        if line_y < surface.get_height():
            pg.draw.line(
                surface,
                (255, 255, 255),
                (0, line_y),
                (surface.get_width(), line_y),
                width=max(1, int(2 * self.zoom)),
            )

    def render_toolbar(self, surface):
        toolbar = pg.Rect(0, 0, surface.get_width(), self.toolbar_height)
        pg.draw.rect(surface, (25, 25, 25), toolbar)

        title = self.font_big.render("Level Editor", True, (255, 255, 255))
        surface.blit(title, (16, (self.toolbar_height - title.get_height()) // 2))

        level_name = self.level_path.parent.name or self.level_path.stem
        path_text = self.font.render(f'Editing "{level_name}"', True, (140, 140, 140))
        surface.blit(path_text, (220, (self.toolbar_height - path_text.get_height()) // 2))

        pb = self.playtest_button_rect()
        pg.draw.rect(surface, (40, 160, 60), pb, border_radius=6)
        pg.draw.rect(surface, (80, 220, 100), pb, width=2, border_radius=6)
        play_label = self.font.render("Play", True, (255, 255, 255))
        surface.blit(play_label, play_label.get_rect(center=pb.center))

        pb = self.open_button_rect()
        pg.draw.rect(surface, (60, 60, 60), pb, border_radius=6)
        pg.draw.rect(surface, (180, 180, 180), pb, width=2, border_radius=6)
        open_label = self.font.render("Open", True, (255, 255, 255))
        surface.blit(open_label, open_label.get_rect(center=pb.center))

        pb = self.new_button_rect()
        pg.draw.rect(surface, (60, 60, 60), pb, border_radius=6)
        pg.draw.rect(surface, (180, 180, 180), pb, width=2, border_radius=6)
        new_label = self.font.render("New", True, (255, 255, 255))
        surface.blit(new_label, new_label.get_rect(center=pb.center))

        pb = self.level_options_button_rect()
        pg.draw.rect(surface, (60, 60, 60), pb, border_radius=6)
        pg.draw.rect(surface, (180, 180, 180), pb, width=2, border_radius=6)
        options_label = self.font.render("Level Options", True, (255, 255, 255))
        surface.blit(options_label, options_label.get_rect(center=pb.center))

        pb = self.delete_level_button_rect()
        pg.draw.rect(surface, (60, 0, 0), pb, border_radius=6)
        pg.draw.rect(surface, (180, 0, 0), pb, width=2, border_radius=6)
        delete_label = self.font.render("Delete Level", True, (255, 255, 255))
        surface.blit(delete_label, delete_label.get_rect(center=pb.center))

        if self.message_timer > 0:
            msg = self.font.render(self.message, True, (255, 255, 120))
            surface.blit(msg, (pb.left - msg.get_width() - 16, (self.toolbar_height - msg.get_height()) // 2))

    def render_mode_buttons(self, surface):
        label = self.font.render("Mode", True, (220, 220, 220))
        surface.blit(label, (14, self.toolbar_height + 6))

        for mode, rect in (("build", self.build_button_rect()), ("edit", self.edit_button_rect())):
            active = self.editor_mode == mode
            bg = (40, 120, 200) if active else (50, 50, 50)
            border = (120, 200, 255) if active else (180, 180, 180)

            pg.draw.rect(surface, bg, rect, border_radius=8)
            pg.draw.rect(surface, border, rect, width=2, border_radius=8)

            txt = self.font.render(mode.capitalize(), True, (255, 255, 255))
            surface.blit(txt, txt.get_rect(center=rect.center))

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

    def render_palette(self, surface):
        w = surface.get_width()
        h = surface.get_height()
        bar = pg.Rect(0, h - self.palette_height, w, self.palette_height)
        pg.draw.rect(surface, (20, 20, 20), bar)
        pg.draw.line(surface, (55, 55, 55), bar.topleft, bar.topright, 2)

        for index, tile_type in enumerate(self.palette):
            rect = self.palette_rect(index)
            is_selected = self.selected_tile == tile_type
            bg = (40, 85, 145) if is_selected else (45, 45, 45)
            border = (90, 170, 255) if is_selected else (75, 75, 75)
            pg.draw.rect(surface, bg, rect, border_radius=8)
            pg.draw.rect(surface, border, rect, width=2, border_radius=8)

            icon = self.palette_icons.get(tile_type)
            if icon:
                icon_area = pg.Rect(rect.x, rect.y + 15, rect.w, rect.h - 16)
                surface.blit(icon, icon.get_rect(center=icon_area.center))

            num = self.font.render(str(index + 1), True, (180, 180, 180))
            surface.blit(num, (rect.x + 4, rect.y + 3))

        pb = self.swipe_button_rect()
        active = self.swipe_mode and self.editor_mode == "build"
        pg.draw.rect(surface, (40, 160, 60) if active else (60, 60, 60), pb, border_radius=6)
        pg.draw.rect(surface, (80, 220, 100) if active else (180, 180, 180), pb, width=2, border_radius=6)
        label = self.font.render("Swipe", True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=pb.center))

    def tile_from_block(self, block):
        normalized = self.normalize_block(block)
        if normalized is None:
            return None

        tile_type, grid_x, grid_y, color, scale, rotation = normalized

        tile_class = self.tile_classes.get(str(tile_type))
        if tile_class is None:
            return None

        rect = self.level_rect_from_grid(grid_x, grid_y, scale)
        if rect is None:
            return None

        tile = tile_class(rect, color)
        tile._editor_rotation = rotation
        return tile

    def level_rect_from_grid(self, grid_x, grid_y, scale=1):
        try:
            scale_x, scale_y = self.normalize_scale(scale)
            width = max(1, round(self.tile_size * scale_x))
            height = max(1, round(self.tile_size * scale_y))
            x = round(self.grid_origin_x + float(grid_x) * self.tile_size)
            y = round(self.ground_y - float(grid_y) * self.tile_size - height)
        except Exception:
            return None

        return x, y, width, height

    def grid_rect(self, grid_x, grid_y):
        x = self.grid_origin_x + grid_x * self.tile_size
        y = self.ground_y - (grid_y + 1) * self.tile_size
        return pg.Rect(x, y, self.tile_size, self.tile_size)

    def world_rect_to_screen(self, rect):
        x, y = self.world_to_screen(rect.x, rect.y)
        return pg.Rect(
            x,
            y,
            max(1, int(rect.w * self.zoom)),
            max(1, int(rect.h * self.zoom)),
        )

    def palette_tile_at_pos(self, pos):
        for index, tile_type in enumerate(self.palette):
            if self.palette_rect(index).collidepoint(pos):
                return tile_type

        return None

    def palette_rect(self, index):
        btn_w, btn_h = 70, 72
        gap = 14
        total = len(self.palette) * (btn_w + gap) - gap
        start_x = (self.SCREEN_W - total) // 2
        y = (self.SCREEN_H - self.palette_height) + (self.palette_height - btn_h) // 2
        return pg.Rect(start_x + index * (btn_w + gap), y, btn_w, btn_h)

    def is_scale_value(self, value):
        return isinstance(value, (int, float)) or (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and all(isinstance(v, (int, float)) for v in value)
        )

    def normalize_scale(self, scale):
        if isinstance(scale, (int, float)):
            value = max(0.1, float(scale))
            return value, value

        if isinstance(scale, (list, tuple)) and len(scale) >= 2:
            return max(0.1, float(scale[0])), max(0.1, float(scale[1]))

        return 1, 1

    def _render_tile_compatible(self, tile, surface, camera_x, camera_y, zoom):
        try:
            tile.render(surface, camera_x=camera_x, camera_y=camera_y, zoom=zoom)
            return
        except TypeError:
            pass

        try:
            tile.render(surface, camera_x, camera_y, zoom)
            return
        except TypeError:
            pass

        try:
            tile.render(surface, camera_x, camera_y)
            return
        except TypeError:
            pass

        tile.render(surface)