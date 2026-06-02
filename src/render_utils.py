"""Shared rendering utilities for both game state and level editor."""

import pygame as pg
import math


class RenderUtils:
    """Common rendering utilities shared between game state and level editor."""

    @staticmethod
    def sort_blocks_by_depth(blocks, is_tile_objects=True):
        """
        Sort blocks for proper Z-ordering (depth perception).
        SolidBlockTile always renders first (behind), then other blocks by Y position.
        
        Args:
            blocks: List of tile objects or block dictionaries
            is_tile_objects: If True, blocks are tile objects. If False, they're block dicts [type, x, y, ...]
        
        Returns:
            Sorted list (same type as input)
        """
        def sort_key(item):
            if is_tile_objects:
                # For tile objects
                tile = item
                tile_type = type(tile).__name__
                tile_y = tile.rect.y if hasattr(tile, 'rect') else 0
                
                if tile_type == "SolidBlockTile":
                    return (0, 0)  # Solid blocks render first
                else:
                    return (1, -tile_y)  # Other tiles by Y position (descending)
            else:
                # For block dictionaries [type, x, y, color, scale, rotation]
                if isinstance(item, tuple):
                    # If it's (index, block), extract the block
                    index, block = item
                    block_type = block[0] if len(block) > 0 else None
                    block_y = block[2] if len(block) > 2 else 0
                else:
                    # Direct block reference
                    block_type = item[0] if len(item) > 0 else None
                    block_y = item[2] if len(item) > 2 else 0
                
                if block_type == "block_solid":
                    return (0, 0)  # Solid blocks render first
                else:
                    return (1, -block_y)  # Other blocks by Y position (descending)

        return sorted(blocks, key=sort_key)

    @staticmethod
    def render_tile_with_rotation(surface, tile, camera_x, camera_y, rotation=0):
        """
        Render a tile with optional rotation support.
        
        Handles multiple tile.render() signatures for compatibility.
        """
        rotation = int(round(rotation)) % 360

        if rotation == 0:
            RenderUtils._render_tile_compatible(tile, surface, camera_x, camera_y)
            return

        rect = tile.rect
        temp = pg.Surface((max(1, rect.w), max(1, rect.h)), pg.SRCALPHA)

        try:
            tile.render(temp, camera_x=rect.x, camera_y=rect.y)
        except TypeError:
            try:
                tile.render(temp, rect.x, rect.y)
            except TypeError:
                tile.render(temp)

        rotated = pg.transform.rotate(temp, -rotation)
        screen_x = rect.centerx - camera_x
        screen_y = rect.centery - camera_y
        rotated_rect = rotated.get_rect(center=(screen_x, screen_y))
        surface.blit(rotated, rotated_rect)

    @staticmethod
    def render_tile_with_rotation_and_zoom(surface, tile, camera_x, camera_y, zoom, rotation=0):
        """
        Render a tile with rotation and zoom support (for level editor).
        """
        rotation = int(round(rotation)) % 360

        if rotation == 0:
            RenderUtils._render_tile_compatible(tile, surface, camera_x, camera_y, zoom)
            return

        rect = tile.rect
        temp_w = max(1, int(rect.w * zoom))
        temp_h = max(1, int(rect.h * zoom))
        temp = pg.Surface((temp_w, temp_h), pg.SRCALPHA)

        try:
            tile.render(temp, camera_x=rect.x, camera_y=rect.y, zoom=zoom)
        except TypeError:
            try:
                tile.render(temp, rect.x, rect.y, zoom)
            except TypeError:
                try:
                    tile.render(temp, rect.x, rect.y)
                except TypeError:
                    tile.render(temp)

        rotated = pg.transform.rotate(temp, -rotation)
        screen_center = (rect.centerx - camera_x, rect.centery - camera_y)
        blit_rect = rotated.get_rect(center=screen_center)
        surface.blit(rotated, blit_rect)

    @staticmethod
    def _render_tile_compatible(tile, surface, camera_x, camera_y, zoom=None):
        """
        Render a tile with multiple fallback rendering modes for compatibility.
        Tries: (camera_x/y kwargs), (positional args), (no camera args).
        """
        if zoom is not None:
            # Try with zoom parameter
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

        # Try with camera parameters (no zoom)
        try:
            tile.render(surface, camera_x=camera_x, camera_y=camera_y)
            return
        except TypeError:
            pass

        try:
            tile.render(surface, camera_x, camera_y)
            return
        except TypeError:
            pass

        # Fallback: just render to surface
        tile.render(surface)

