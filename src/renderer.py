"""
Unified rendering system for both game state and level editor.

This module provides all rendering functionality shared and specific to both
the main game and the level editor, with proper Z-ordering and tile handling.
"""

import pygame as pg
import math
from render_utils import RenderUtils


# ============================================================================
# GAME STATE RENDERING
# ============================================================================

class GameRenderer:
    """Handles rendering for the main game state."""

    @staticmethod
    def render_game(game_state, surface):
        """Main render function for game state."""
        surface.fill((80, 160, 240))
        GameRenderer.render_tiles(game_state, surface)
        GameRenderer.render_player(game_state, surface)
        GameRenderer.render_hud(game_state, surface)

    @staticmethod
    def render_tiles(game_state, surface):
        """Render all level tiles with proper Z-ordering."""
        # Sort blocks for proper Z-ordering (SolidBlockTile first, then by Y position)
        sorted_blocks = RenderUtils.sort_blocks_by_depth(
            game_state.blocks, 
            is_tile_objects=True
        )
        
        for tile in sorted_blocks:
            tile_x = tile.rect.x
            if game_state.pos.x - tile_x > 720 and not (type(tile).__name__ == "GroundTile"):
                continue
            
            rotation = getattr(tile, "_rotation", 0)
            RenderUtils.render_tile_with_rotation(
                surface, tile, game_state.camera_x, game_state.camera_y, rotation
            )

    @staticmethod
    def render_player(game_state, surface):
        """Render the player (cube or ship mode, or death animation)."""
        if getattr(game_state, "is_dead", False):
            GameRenderer.render_death_explosion(game_state, surface)
            return

        rect = pg.Rect(0, 0, int(game_state.player_size.x), int(game_state.player_size.y))
        rect.center = (int(game_state.pos.x - game_state.camera_x), int(game_state.pos.y - game_state.camera_y))
        
        if getattr(game_state, "mode", "cube") == "ship":
            GameRenderer.render_ship(game_state, surface, rect)
        else:
            pg.draw.rect(surface, (200, 50, 50), rect, border_radius=6)

    @staticmethod
    def render_ship(game_state, surface, rect):
        """Render the player as a spaceship."""
        # Draw ship body (triangle pointing right)
        ship_width = rect.width * 0.8
        ship_height = rect.height * 0.6
        
        left = rect.centerx - ship_width / 2
        top = rect.centery - ship_height / 2
        
        # Main ship body - triangle
        points = [
            (left + ship_width, rect.centery),  # nose (right point)
            (left, top),                         # top-left
            (left, top + ship_height),           # bottom-left
        ]
        pg.draw.polygon(surface, (0, 150, 255), points)
        pg.draw.polygon(surface, (100, 200, 255), points, width=2)
        
        # Engine glow (circle at back)
        engine_x = int(left - 8)
        engine_y = rect.centery
        pg.draw.circle(surface, (255, 150, 50), (engine_x, engine_y), 6)
        pg.draw.circle(surface, (255, 200, 100), (engine_x, engine_y), 3)

    @staticmethod
    def render_death_explosion(game_state, surface):
        """Render death explosion animation."""
        if game_state.death_pos is None:
            return

        progress = min(1.0, game_state.death_timer / game_state.death_duration)
        center = pg.Vector2(
            game_state.death_pos.x - game_state.camera_x, 
            game_state.death_pos.y - game_state.camera_y
        )
        radius = int(36 + 116 * progress)
        alpha = max(0, int(255 * (1.0 - progress)))

        burst = pg.Surface(surface.get_size(), pg.SRCALPHA)
        pg.draw.circle(burst, (255, 255, 255, alpha), center, radius, width=3)
        pg.draw.circle(burst, (255, 80, 50, alpha // 2), center, max(4, radius // 2), width=4)

        particle_colors = [
            (255, 255, 255),
            (255, 210, 80),
            (255, 80, 50),
        ]

        for index in range(16):
            angle = (math.tau / 16) * index
            distance = 16 + 72 * progress
            particle_pos = (
                int(center.x + math.cos(angle) * distance),
                int(center.y + math.sin(angle) * distance),
            )
            size = max(2, int(8 * (1.0 - progress)))
            color = particle_colors[index % len(particle_colors)]
            pg.draw.circle(burst, (*color, alpha), particle_pos, size)

        surface.blit(burst, (0, 0))

    @staticmethod
    def render_hud(game_state, surface):
        """Render HUD (heads-up display) information."""
        info = f"Attempt {game_state.attempts} | Progress: idk it's not in yet"
        text = game_state.font.render(info, True, (0, 0, 0))
        surface.blit(text, (10, 10))


# ============================================================================
# LEVEL EDITOR RENDERING
# ============================================================================

class EditorRenderer:
    """Handles rendering for the level editor."""

    @staticmethod
    def render_editor(editor_state, surface):
        """Main render function for level editor."""
        surface.fill((80, 160, 240))
        EditorRenderer.render_grid(editor_state, surface)
        EditorRenderer.render_blocks(editor_state, surface)
        EditorRenderer.render_ground(editor_state, surface)
        EditorRenderer.render_music_progress_bar(editor_state, surface)
        EditorRenderer.render_toolbar(editor_state, surface)
        EditorRenderer.render_mode_buttons(editor_state, surface)
        EditorRenderer.render_palette(editor_state, surface)
        
        if (editor_state.selection_dragging and editor_state.selection_rect_start 
            and editor_state.selection_rect_current):
            EditorRenderer.render_selection_box(editor_state, surface)

    # ========================================================================
    # EDITOR: GRID AND COORDINATES
    # ========================================================================

    @staticmethod
    def render_grid(editor_state, surface):
        """Render the grid lines and hover indicator."""
        width, height = surface.get_size()

        world_left = editor_state.camera_x
        world_top = editor_state.camera_y
        world_right = editor_state.camera_x + width / editor_state.zoom
        world_bottom = editor_state.camera_y + height / editor_state.zoom

        first_x = (editor_state.grid_origin_x + 
                   math.floor((world_left - editor_state.grid_origin_x) / editor_state.tile_size) * editor_state.tile_size)
        last_x = world_right + editor_state.tile_size

        x = first_x
        while x <= last_x:
            sx, _ = editor_state.coords.world_to_screen(x, world_top)
            pg.draw.line(surface, (90, 170, 245), (sx, 0), (sx, height))
            x += editor_state.tile_size

        first_y = (editor_state.ground_y - 
                   math.floor((editor_state.ground_y - world_top) / editor_state.tile_size) * editor_state.tile_size)
        last_y = world_bottom + editor_state.tile_size

        y = first_y
        while y <= last_y:
            _, sy = editor_state.coords.world_to_screen(world_left, y)
            pg.draw.line(surface, (90, 170, 245), (0, sy), (width, sy))
            y += editor_state.tile_size

        if editor_state.hover_grid is not None:
            rect = editor_state.coords.grid_rect(*editor_state.hover_grid)
            screen_rect = editor_state.coords.world_rect_to_screen(rect)
            pg.draw.rect(surface, (255, 255, 255), screen_rect, 
                        width=max(1, int(2 * editor_state.zoom)))

    # ========================================================================
    # EDITOR: BLOCKS AND TILES
    # ========================================================================

    @staticmethod
    def render_blocks(editor_state, surface):
        """Render all blocks and selection highlights with proper Z-ordering."""
        # Sort blocks using shared depth sorting (SolidBlockTile first, then by Y position)
        sorted_blocks = RenderUtils.sort_blocks_by_depth(
            enumerate(editor_state.blocks), 
            is_tile_objects=False
        )

        for index, block in sorted_blocks:
            tile = editor_state.blocks_mgr.tile_from_block(block)
            if tile:
                EditorRenderer.render_tile(editor_state, surface, tile)

        if editor_state.editor_mode == "edit":
            if editor_state.selected_block_indices:
                EditorRenderer.render_selected_block_outlines(editor_state, surface)
            elif editor_state.selected_block_index is not None:
                EditorRenderer.render_selected_block_outline(editor_state, surface)

    @staticmethod
    def render_tile(editor_state, surface, tile):
        """Render a single tile with rotation support."""
        rotation = editor_state.blocks_mgr.normalize_rotation(
            getattr(tile, "_editor_rotation", 0)
        )
        RenderUtils.render_tile_with_rotation_and_zoom(
            surface, tile, editor_state.camera_x, editor_state.camera_y, 
            editor_state.zoom, rotation
        )

    @staticmethod
    def render_selected_block_outline(editor_state, surface):
        """Render outline for a single selected block."""
        if not (0 <= editor_state.selected_block_index < len(editor_state.blocks)):
            return

        block = editor_state.blocks[editor_state.selected_block_index]
        rect = editor_state.blocks_mgr.block_rect(block)
        if rect is None:
            return

        screen_rect = editor_state.coords.world_rect_to_screen(rect)
        pg.draw.rect(surface, (255, 255, 0), screen_rect, 
                    width=max(1, int(3 * editor_state.zoom)))

    @staticmethod
    def render_selected_block_outlines(editor_state, surface):
        """Render outlines for all selected blocks."""
        for index in editor_state.get_selected_indices():
            if not (0 <= index < len(editor_state.blocks)):
                continue

            rect = editor_state.blocks_mgr.block_rect(editor_state.blocks[index])
            if rect is None:
                continue

            screen_rect = editor_state.coords.world_rect_to_screen(rect)
            pg.draw.rect(surface, (255, 255, 0), screen_rect, 
                        width=max(1, int(3 * editor_state.zoom)))

    @staticmethod
    def render_selection_box(editor_state, surface):
        """Render the selection drag box."""
        x1, y1 = editor_state.selection_rect_start
        x2, y2 = editor_state.selection_rect_current

        rect = pg.Rect(
            min(x1, x2),
            min(y1, y2),
            abs(x2 - x1),
            abs(y2 - y1),
        )

        pg.draw.rect(surface, (120, 180, 255), rect, 2)

    # ========================================================================
    # EDITOR: MUSIC AND GROUND
    # ========================================================================

    @staticmethod
    def render_music_progress_bar(editor_state, surface):
        """Render a vertical bar showing music playback progress."""
        if not editor_state.music_mgr.is_playing or editor_state.music_mgr.music_duration <= 0:
            return

        if not editor_state.blocks:
            return

        # Find level bounds
        min_x = min((block[1] for block in editor_state.blocks if len(block) > 1), default=0)
        max_x = max((block[1] for block in editor_state.blocks if len(block) > 1), default=100)
        level_width = max_x - min_x if max_x > min_x else 100

        # Current music playback progress (0 to 1)
        music_pos = editor_state.music_mgr.get_current_position()
        progress = music_pos / editor_state.music_mgr.music_duration if editor_state.music_mgr.music_duration > 0 else 0
        progress = max(0.0, min(1.0, progress))

        # Convert music progress to world X coordinate
        world_x = min_x + progress * level_width

        # Convert to screen coordinates
        screen_x, _ = editor_state.coords.world_to_screen(world_x, 0)

        # Draw vertical bar
        pg.draw.line(surface, (0, 255, 0), (screen_x, 0), (screen_x, surface.get_height()), width=3)

    @staticmethod
    def render_ground(editor_state, surface):
        """Render the ground/base plane."""
        ground_screen_y = int((editor_state.ground_y - editor_state.camera_y) * editor_state.zoom)

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
                width=max(1, int(2 * editor_state.zoom)),
            )

    # ========================================================================
    # EDITOR: UI ELEMENTS (TOOLBAR, BUTTONS, PALETTE)
    # ========================================================================

    @staticmethod
    def render_toolbar(editor_state, surface):
        """Render the top toolbar with buttons and info."""
        toolbar = pg.Rect(0, 0, surface.get_width(), editor_state.toolbar_height)
        pg.draw.rect(surface, (25, 25, 25), toolbar)

        # Music button
        mb = editor_state.music_button_rect()
        is_playing = editor_state.music_mgr.is_playing
        bg = (40, 160, 60) if is_playing else (60, 60, 60)
        border = (80, 220, 100) if is_playing else (180, 180, 180)
        pg.draw.rect(surface, bg, mb, border_radius=6)
        pg.draw.rect(surface, border, mb, width=2, border_radius=6)
        music_label = editor_state.font.render("Music" if not is_playing else "Stop", True, (255, 255, 255))
        surface.blit(music_label, music_label.get_rect(center=mb.center))

        title = editor_state.font_big.render("Level Editor", True, (255, 255, 255))
        surface.blit(title, (16 + mb.width + 16, (editor_state.toolbar_height - title.get_height()) // 2))

        level_name = editor_state.level_path.parent.name or editor_state.level_path.stem
        path_text = editor_state.font.render(f'Editing "{level_name}"', True, (140, 140, 140))
        surface.blit(path_text, (220, (editor_state.toolbar_height - path_text.get_height()) // 2))

        pb = editor_state.playtest_button_rect()
        pg.draw.rect(surface, (40, 160, 60), pb, border_radius=6)
        pg.draw.rect(surface, (80, 220, 100), pb, width=2, border_radius=6)
        play_label = editor_state.font.render("Play", True, (255, 255, 255))
        surface.blit(play_label, play_label.get_rect(center=pb.center))

        pb = editor_state.open_button_rect()
        pg.draw.rect(surface, (60, 60, 60), pb, border_radius=6)
        pg.draw.rect(surface, (180, 180, 180), pb, width=2, border_radius=6)
        open_label = editor_state.font.render("Open", True, (255, 255, 255))
        surface.blit(open_label, open_label.get_rect(center=pb.center))

        pb = editor_state.new_button_rect()
        pg.draw.rect(surface, (60, 60, 60), pb, border_radius=6)
        pg.draw.rect(surface, (180, 180, 180), pb, width=2, border_radius=6)
        new_label = editor_state.font.render("New", True, (255, 255, 255))
        surface.blit(new_label, new_label.get_rect(center=pb.center))

        pb = editor_state.level_options_button_rect()
        pg.draw.rect(surface, (60, 60, 60), pb, border_radius=6)
        pg.draw.rect(surface, (180, 180, 180), pb, width=2, border_radius=6)
        options_label = editor_state.font.render("Level Options", True, (255, 255, 255))
        surface.blit(options_label, options_label.get_rect(center=pb.center))

        pb = editor_state.delete_level_button_rect()
        pg.draw.rect(surface, (60, 0, 0), pb, border_radius=6)
        pg.draw.rect(surface, (180, 0, 0), pb, width=2, border_radius=6)
        delete_label = editor_state.font.render("Delete Level", True, (255, 255, 255))
        surface.blit(delete_label, delete_label.get_rect(center=pb.center))

        if editor_state.message_timer > 0:
            msg = editor_state.font.render(editor_state.message, True, (255, 255, 120))
            surface.blit(msg, (pb.left - msg.get_width() - 16, 
                              (editor_state.toolbar_height - msg.get_height()) // 2))

    @staticmethod
    def render_mode_buttons(editor_state, surface):
        """Render build/edit mode buttons."""
        label = editor_state.font.render("Mode", True, (220, 220, 220))
        surface.blit(label, (14, editor_state.toolbar_height + 6))

        for mode, rect in (("build", editor_state.build_button_rect()), 
                          ("edit", editor_state.edit_button_rect())):
            active = editor_state.editor_mode == mode
            bg = (40, 120, 200) if active else (50, 50, 50)
            border = (120, 200, 255) if active else (180, 180, 180)

            pg.draw.rect(surface, bg, rect, border_radius=8)
            pg.draw.rect(surface, border, rect, width=2, border_radius=8)

            txt = editor_state.font.render(mode.capitalize(), True, (255, 255, 255))
            surface.blit(txt, txt.get_rect(center=rect.center))

    @staticmethod
    def render_palette(editor_state, surface):
        """Render the tile palette at the bottom."""
        w = surface.get_width()
        h = surface.get_height()
        bar = pg.Rect(0, h - editor_state.palette_height, w, editor_state.palette_height)
        pg.draw.rect(surface, (20, 20, 20), bar)
        pg.draw.line(surface, (55, 55, 55), bar.topleft, bar.topright, 2)

        for index, tile_type in enumerate(editor_state.palette):
            rect = editor_state.palette_rect(index)
            is_selected = editor_state.selected_tile == tile_type
            bg = (40, 85, 145) if is_selected else (45, 45, 45)
            border = (90, 170, 255) if is_selected else (75, 75, 75)
            pg.draw.rect(surface, bg, rect, border_radius=8)
            pg.draw.rect(surface, border, rect, width=2, border_radius=8)

            icon = editor_state.palette_icons.get(tile_type)
            if icon:
                icon_area = pg.Rect(rect.x, rect.y + 15, rect.w, rect.h - 16)
                surface.blit(icon, icon.get_rect(center=icon_area.center))

            num = editor_state.font.render(str(index + 1), True, (180, 180, 180))
            surface.blit(num, (rect.x + 4, rect.y + 3))

        pb = editor_state.swipe_button_rect()
        active = editor_state.swipe_mode and editor_state.editor_mode == "build"
        pg.draw.rect(surface, (40, 160, 60) if active else (60, 60, 60), pb, border_radius=6)
        pg.draw.rect(surface, (80, 220, 100) if active else (180, 180, 180), pb, width=2, border_radius=6)
        label = editor_state.font.render("Swipe", True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=pb.center))
