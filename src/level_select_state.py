from pathlib import Path
import json

import pygame as pg

from game_state import GameState


class LevelSelectState:

    def __init__(self, initial_dir=None, edit_mode=False):
        self.initial_dir = initial_dir
        self.edit_mode = edit_mode

    def enter(self, manager):
        self.manager = manager
        self.font_big = pg.font.SysFont(None, 78)
        self.font = pg.font.SysFont("segoeuisymbol", 34)
        self.font_small = pg.font.SysFont(None, 24)
        self.levels = self.find_levels()
        self.level_labels = [self.level_label(level_path) for level_path in self.levels]
        self.selected_index = 0
        self.hovered_index = None
        self.back_hovered = False
        self.row_size = (420, 54)
        self.back_size = (120, 46)

    def find_levels(self):
        levels_dir = Path("levels")
        if not levels_dir.exists():
            return []

        level_files = list(levels_dir.glob("*.json")) + list(levels_dir.glob("*/level.json"))
        return sorted(level_files, key=lambda path: self.level_sort_name(path).lower())

    def level_sort_name(self, level_path):
        if level_path.name == "level.json":
            return level_path.parent.name

        return level_path.stem

    def level_label(self, level_path):
        name = self.level_sort_name(level_path)
        difficulty = None

        try:
            with open(level_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            data = None

        if isinstance(data, dict):
            name = str(data.get("name") or data.get("title") or name)
            difficulty = data.get("difficulty")

        if difficulty is None:
            return name

        return f"{name} ({difficulty}★)"

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            self.handle_keydown(event.key)
        elif event.type == pg.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_click(event.pos)

    def handle_keydown(self, key):
        if key in (pg.K_ESCAPE, pg.K_BACKSPACE):
            self.go_back()
        elif key in (pg.K_DOWN, pg.K_s):
            self.move_selection(1)
        elif key in (pg.K_UP, pg.K_w):
            self.move_selection(-1)
        elif key == pg.K_RETURN:
            self.start_selected_level()

    def handle_mouse_motion(self, pos):
        self.hovered_index = self.level_index_at_pos(pos)
        self.back_hovered = self.back_rect().collidepoint(pos)

        if self.hovered_index is not None:
            self.selected_index = self.hovered_index

    def handle_click(self, pos):
        clicked_index = self.level_index_at_pos(pos)
        if clicked_index is not None:
            self.selected_index = clicked_index
            self.start_selected_level()
        elif self.back_rect().collidepoint(pos):
            self.go_back()

    def move_selection(self, direction):
        if not self.levels:
            return

        self.selected_index = (self.selected_index + direction) % len(self.levels)

    def start_selected_level(self):
        if not self.levels:
            return

        if self.edit_mode:
            from level_editor_state import LevelEditorState
            self.manager.change(LevelEditorState(self.levels[self.selected_index]))
        else:
            self.manager.change(GameState(self.levels[self.selected_index]))

    def go_back(self):
        from menu_state import MenuState

        self.manager.change(MenuState())

    def render(self, surface):
        surface.fill((30, 30, 30))
        title = self.font_big.render("Select Level", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, 120)))

        if self.levels:
            for index, level_path in enumerate(self.levels):
                self.render_level_row(surface, index, level_path)
        else:
            empty = self.font.render("No levels found!", True, (180, 180, 180))
            surface.blit(empty, empty.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2)))

        self.render_back_button(surface)

    def render_level_row(self, surface, index, level_path):
        rect = self.level_rect(index)
        is_selected = index == self.selected_index
        color = (150, 150, 150) if is_selected else (90, 90, 90)
        pg.draw.rect(surface, color, rect, border_radius=8)
        pg.draw.rect(surface, (255, 255, 255), rect, width=2, border_radius=8)

        label = self.font.render(self.level_labels[index], True, (255, 255, 255))
        surface.blit(label, label.get_rect(midleft=(rect.left + 22, rect.centery)))

    def render_back_button(self, surface):
        rect = self.back_rect()
        color = (140, 140, 140) if self.back_hovered else (100, 100, 100)
        pg.draw.rect(surface, color, rect, border_radius=8)

        label = self.font_small.render("Back", True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=rect.center))

    def level_index_at_pos(self, pos):
        for index in range(len(self.levels)):
            if self.level_rect(index).collidepoint(pos):
                return index

        return None

    def level_rect(self, index):
        surface = pg.display.get_surface()
        width = surface.get_width() if surface else 1280
        rect = pg.Rect(0, 0, self.row_size[0], self.row_size[1])
        rect.center = (width // 2, 220 + index * 68)
        return rect

    def back_rect(self):
        surface = pg.display.get_surface()
        width, height = surface.get_size() if surface else (1280, 720)
        rect = pg.Rect(0, 0, self.back_size[0], self.back_size[1])
        rect.center = (width // 2, height - 78)
        return rect

    def update(self, dt):
        pass
