"""Coordinate transformation utilities for the level editor."""

import math
import pygame as pg


class CoordinateSystem:
    """Handles coordinate transformations between screen, world, and grid space."""

    def __init__(self, state):
        self.state = state

    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates."""
        return (
            int((x - self.state.camera_x) * self.state.zoom),
            int((y - self.state.camera_y) * self.state.zoom),
        )

    def screen_to_world(self, pos):
        """Convert screen coordinates to world coordinates."""
        x, y = pos
        return (
            self.state.camera_x + x / self.state.zoom,
            self.state.camera_y + y / self.state.zoom,
        )

    def screen_to_grid(self, pos):
        """Convert screen coordinates to grid coordinates."""
        x, y = pos
        if y < self.state.toolbar_height or y >= self.state.SCREEN_H - self.state.palette_height:
            return None

        world_x, world_y = self.screen_to_world(pos)
        grid_x = int((world_x - self.state.grid_origin_x) / self.state.tile_size)
        grid_y = int((self.state.ground_y - world_y) / self.state.tile_size)
        return grid_x, grid_y

    def zoom_at(self, screen_pos, direction):
        """Zoom in/out at a specific screen position."""
        if direction == 0:
            return

        before = self.screen_to_world(screen_pos)
        factor = self.state.ZOOM_FACTOR if direction > 0 else 1.0 / self.state.ZOOM_FACTOR
        new_zoom = max(self.state.MIN_ZOOM, min(self.state.MAX_ZOOM, self.state.zoom * factor))

        if abs(new_zoom - self.state.zoom) < 1e-9:
            return

        sx, sy = screen_pos
        self.state.zoom = new_zoom
        self.state.camera_x = before[0] - sx / self.state.zoom
        self.state.camera_y = before[1] - sy / self.state.zoom

    def world_rect_to_screen(self, rect):
        """Convert a world-space rectangle to screen coordinates."""
        x, y = self.world_to_screen(rect.x, rect.y)
        return pg.Rect(
            x,
            y,
            max(1, int(rect.w * self.state.zoom)),
            max(1, int(rect.h * self.state.zoom)),
        )

    def grid_rect(self, grid_x, grid_y):
        """Get a rectangle for a grid cell in world coordinates."""
        x = self.state.grid_origin_x + grid_x * self.state.tile_size
        y = self.state.ground_y - (grid_y + 1) * self.state.tile_size
        return pg.Rect(x, y, self.state.tile_size, self.state.tile_size)

    def level_rect_from_grid(self, grid_x, grid_y, scale=1):
        """Convert grid position and scale to a world-space rectangle."""
        try:
            scale_x, scale_y = self.normalize_scale(scale)
            width = max(1, round(self.state.tile_size * scale_x))
            height = max(1, round(self.state.tile_size * scale_y))
            x = round(self.state.grid_origin_x + float(grid_x) * self.state.tile_size)
            y = round(self.state.ground_y - float(grid_y) * self.state.tile_size - height)
        except Exception:
            return None

        return x, y, width, height

    def normalize_scale(self, scale):
        """Normalize scale value to (scale_x, scale_y) tuple."""
        if isinstance(scale, (int, float)):
            value = max(0.1, float(scale))
            return value, value

        if isinstance(scale, (list, tuple)) and len(scale) >= 2:
            return max(0.1, float(scale[0])), max(0.1, float(scale[1]))

        return 1, 1
