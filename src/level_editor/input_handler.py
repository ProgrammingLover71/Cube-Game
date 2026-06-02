"""Input handling for the level editor."""

import pygame as pg


class InputHandler:
    """Handles keyboard and mouse events for the level editor."""

    def __init__(self, state):
        self.state = state

    def handle_event(self, event):
        """Process a single event."""
        if event.type == pg.KEYDOWN:
            self.handle_keydown(event.key)

        if event.type == pg.KEYUP:
            self.handle_keyup(event.key)

        elif event.type == pg.MOUSEMOTION:
            self.state.hover_grid = self.state.coords.screen_to_grid(event.pos)
            self.handle_swipe_motion(event)
            self.handle_edit_drag_motion(event)
            self.handle_selection_drag(event)

        elif event.type == pg.MOUSEBUTTONDOWN:
            self.handle_mouse_down(event)

        elif event.type == pg.MOUSEBUTTONUP:
            if event.button in (1, 3):
                self.state.last_swipe_grid = None
            if event.button == 1:
                if self.state.selection_dragging:
                    self.finish_box_selection()
                self.state.edit_dragging = False
                self.state.edit_drag_last_grid = None

        elif event.type == pg.MOUSEWHEEL:
            mods = pg.key.get_mods()

            if mods & pg.KMOD_CTRL:
                self.state.coords.zoom_at(pg.mouse.get_pos(), event.y)
            elif mods & pg.KMOD_SHIFT:
                self.state.camera_x -= event.y * self.state.tile_size
            else:
                self.state.camera_y -= event.y * self.state.tile_size

    def handle_keyup(self, key):
        """Handle key release events."""
        mods = pg.key.get_mods()

        if key == pg.K_s and (mods & pg.KMOD_ALT):
            # We released Alt+S, so toggle Swipe mode
            if self.state.editor_mode == "build":
                self.state.swipe_mode = not self.state.swipe_mode
                self.state.last_swipe_grid = None

    def handle_keydown(self, key):
        """Handle key press events."""
        mods = pg.key.get_mods()

        if self.state.editor_mode == "edit" and self.state.has_selection():
            if self.handle_edit_keydown(key, mods):
                return

        if key in (pg.K_ESCAPE, pg.K_BACKSPACE):
            from menu_state import MenuState
            self.state.manager.change(MenuState())
        elif key == pg.K_s:
            if mods & pg.KMOD_CTRL:
                self.state.file_mgr.save_level()
        elif key == pg.K_RETURN:
            self.state.file_mgr.start_playtest()
        elif key == pg.K_o:
            if mods & pg.KMOD_LSHIFT:
                self.state.file_mgr.open_options()
            else:
                self.state.file_mgr.open_level()
        elif key == pg.K_n:
            if mods & pg.KMOD_CTRL:
                self.state.file_mgr.new_level()
        elif key == pg.K_LEFT:
            self.state.camera_x -= self.state.tile_size
        elif key == pg.K_RIGHT:
            self.state.camera_x += self.state.tile_size
        elif key == pg.K_UP:
            self.state.camera_y -= self.state.tile_size
        elif key == pg.K_DOWN:
            self.state.camera_y += self.state.tile_size
        elif key in (pg.K_EQUALS, pg.K_KP_PLUS):
            self.state.coords.zoom_at(pg.mouse.get_pos(), 1)
        elif key in (pg.K_MINUS, pg.K_KP_MINUS):
            self.state.coords.zoom_at(pg.mouse.get_pos(), -1)
        elif pg.K_1 <= key <= pg.K_6:
            self.state.selected_tile = self.state.palette[key - pg.K_1]

    def handle_edit_keydown(self, key, mods):
        """Handle key presses in edit mode."""
        if not self.state.has_selection():
            return False

        moved = False
        rotated = False
        step = 0.5 if (mods & pg.KMOD_SHIFT) else 1.0

        if key == pg.K_LEFT:
            self.state.blocks_mgr.move_selected_blocks(-step, 0.0)
            moved = True
        elif key == pg.K_RIGHT:
            self.state.blocks_mgr.move_selected_blocks(step, 0.0)
            moved = True
        elif key == pg.K_UP:
            self.state.blocks_mgr.move_selected_blocks(0.0, step)
            moved = True
        elif key == pg.K_DOWN:
            self.state.blocks_mgr.move_selected_blocks(0.0, -step)
            moved = True
        elif key == pg.K_q:
            self.state.blocks_mgr.rotate_selected_blocks(-90)
            rotated = True
        elif key == pg.K_e:
            self.state.blocks_mgr.rotate_selected_blocks(90)
            rotated = True
        elif key == pg.K_DELETE:
            self.state.blocks_mgr.delete_selected_blocks()
            return True

        return moved or rotated

    def handle_mouse_down(self, event):
        """Handle mouse button press events."""
        mouse_pos = event.pos

        if event.button == 1:
            if self.state.playtest_button_rect().collidepoint(mouse_pos):
                self.state.file_mgr.start_playtest()
                return

            if self.state.music_button_rect().collidepoint(mouse_pos):
                self.state.music_mgr.toggle()
                return

            if self.state.open_button_rect().collidepoint(mouse_pos):
                self.state.file_mgr.open_level()
                return

            if self.state.new_button_rect().collidepoint(mouse_pos):
                self.state.file_mgr.new_level()
                return

            if self.state.level_options_button_rect().collidepoint(mouse_pos):
                self.state.file_mgr.open_options()
                return

            if self.state.delete_level_button_rect().collidepoint(mouse_pos):
                self.state.file_mgr.delete_level()
                return

            if self.state.build_button_rect().collidepoint(mouse_pos):
                self.state.set_editor_mode("build")
                return

            if self.state.edit_button_rect().collidepoint(mouse_pos):
                self.state.set_editor_mode("edit")
                return

            if self.state.swipe_button_rect().collidepoint(mouse_pos):
                if self.state.editor_mode == "build":
                    self.state.swipe_mode = not self.state.swipe_mode
                    self.state.last_swipe_grid = None
                return

        palette_tile = self.state.palette_tile_at_pos(mouse_pos)
        if palette_tile:
            self.state.selected_tile = palette_tile
            return

        if self.state.editor_mode == "edit":
            if event.button == 1:
                hit = self.state.blocks_mgr.find_block_at_pos(mouse_pos)
                if hit is not None:
                    self.state.selected_block_index = hit
                    self.state.selected_block_indices = {hit}
                    self.state.edit_dragging = True
                    self.state.selection_dragging = False
                    self.state.selection_rect_start = None
                    self.state.selection_rect_current = None
                    self.state.edit_drag_last_grid = self.state.coords.screen_to_grid(mouse_pos)
                else:
                    self.state.selected_block_index = None
                    self.state.selected_block_indices.clear()
                    self.state.edit_dragging = False
                    self.state.edit_drag_last_grid = None
                    self.state.selection_dragging = True
                    self.state.selection_rect_start = mouse_pos
                    self.state.selection_rect_current = mouse_pos
                return

            if event.button == 3:
                hit = self.state.blocks_mgr.find_block_at_pos(mouse_pos)
                if hit is not None:
                    self.state.blocks_mgr.delete_block(hit)
                return

        grid_pos = self.state.coords.screen_to_grid(mouse_pos)
        if grid_pos is None:
            return

        if self.state.editor_mode != "build":
            return

        if event.button == 1:
            self.state.blocks_mgr.place_block(*grid_pos)
            if self.state.swipe_mode:
                self.state.last_swipe_grid = (*grid_pos, 1)
        elif event.button == 3:
            self.state.blocks_mgr.erase_block(*grid_pos)
            if self.state.swipe_mode:
                self.state.last_swipe_grid = (*grid_pos, 3)

    def handle_swipe_motion(self, event):
        """Handle swipe painting mode."""
        if not self.state.swipe_mode or self.state.editor_mode != "build":
            return

        buttons = event.buttons
        left_held = buttons[0]
        right_held = buttons[2]

        if not left_held and not right_held:
            self.state.last_swipe_grid = None
            return

        grid_pos = self.state.coords.screen_to_grid(event.pos)
        if grid_pos is None:
            self.state.last_swipe_grid = None
            return

        if left_held:
            tag = (*grid_pos, 1)
            if self.state.last_swipe_grid != tag:
                self.state.blocks_mgr.place_block(*grid_pos)
                self.state.last_swipe_grid = tag
        elif right_held:
            tag = (*grid_pos, 3)
            if self.state.last_swipe_grid != tag:
                self.state.blocks_mgr.erase_block(*grid_pos)
                self.state.last_swipe_grid = tag

    def handle_edit_drag_motion(self, event):
        """Handle dragging blocks in edit mode."""
        if self.state.editor_mode != "edit":
            return

        if self.state.edit_dragging and self.state.has_selection():
            if not event.buttons or not event.buttons[0]:
                return

            grid_pos = self.state.coords.screen_to_grid(event.pos)
            if grid_pos is None:
                return

            if self.state.edit_drag_last_grid is None:
                self.state.edit_drag_last_grid = grid_pos
                return

            if grid_pos == self.state.edit_drag_last_grid:
                return

            dx = grid_pos[0] - self.state.edit_drag_last_grid[0]
            dy = grid_pos[1] - self.state.edit_drag_last_grid[1]

            if dx or dy:
                self.state.blocks_mgr.move_selected_blocks(dx, dy)
                self.state.edit_drag_last_grid = grid_pos

    def handle_selection_drag(self, event):
        """Handle selection box dragging."""
        if not self.state.selection_dragging:
            return

        self.state.selection_rect_current = event.pos

    def finish_box_selection(self):
        """Complete the selection box and select blocks within it."""
        self.state.selection_dragging = False

        if not self.state.selection_rect_start or not self.state.selection_rect_current:
            self.state.selection_rect_start = None
            self.state.selection_rect_current = None
            return

        x1, y1 = self.state.selection_rect_start
        x2, y2 = self.state.selection_rect_current

        selection_rect = pg.Rect(
            min(x1, x2),
            min(y1, y2),
            abs(x2 - x1),
            abs(y2 - y1),
        )

        self.state.selected_block_indices.clear()

        for i, block in enumerate(self.state.blocks):
            rect = self.state.blocks_mgr.block_rect(block)
            if rect is None:
                continue

            screen_rect = self.state.coords.world_rect_to_screen(rect)
            if selection_rect.colliderect(screen_rect):
                self.state.selected_block_indices.add(i)

        self.state.selected_block_index = next(iter(self.state.selected_block_indices)) if self.state.selected_block_indices else None
        self.state.selection_rect_start = None
        self.state.selection_rect_current = None
