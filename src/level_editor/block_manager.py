"""Block management utilities for the level editor."""

import pygame as pg


class BlockManager:
    """Handles all block operations including placement, deletion, movement, and queries."""

    def __init__(self, state):
        self.state = state

    def normalize_rotation(self, rotation):
        """Normalize rotation value to 0-359 range."""
        try:
            return int(round(float(rotation))) % 360
        except Exception:
            return 0

    def normalize_block(self, block):
        """Normalize block data into standard [type, x, y, color, scale, rotation] format."""
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

    def is_scale_value(self, value):
        """Check if a value is a valid scale value."""
        return isinstance(value, (int, float)) or (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and all(isinstance(v, (int, float)) for v in value)
        )

    def place_block(self, grid_x, grid_y):
        """Place a block at the given grid position."""
        self.erase_block(grid_x, grid_y)
        self.state.blocks.append([self.state.selected_tile, grid_x, grid_y, None, 1, 0])

    def erase_block(self, grid_x, grid_y):
        """Erase block(s) at the given grid position."""
        removed_any = False
        new_blocks = []
        for i, block in enumerate(self.state.blocks):
            if self.block_grid_pos(block) != (grid_x, grid_y):
                new_blocks.append(block)
            else:
                removed_any = True
                if self.state.selected_block_index == i:
                    self.state.selected_block_index = None
                elif self.state.selected_block_index is not None and self.state.selected_block_index > i:
                    self.state.selected_block_index -= 1

                if i in self.state.selected_block_indices:
                    self.state.selected_block_indices.discard(i)

        self.state.blocks = new_blocks

        if removed_any:
            self.state.selected_block_indices = {
                (idx - 1 if idx > -1 else idx)
                for idx in self.state.selected_block_indices
                if 0 <= idx < len(self.state.blocks)
            }

            self.state.selected_block_indices = {
                idx for idx in self.state.selected_block_indices
                if 0 <= idx < len(self.state.blocks)
            }

            if self.state.selected_block_index is not None and self.state.selected_block_index >= len(self.state.blocks):
                self.state.selected_block_index = len(self.state.blocks) - 1 if self.state.blocks else None

    def delete_block(self, index):
        """Delete a block at the given index."""
        if not (0 <= index < len(self.state.blocks)):
            return

        del self.state.blocks[index]

        if self.state.selected_block_index == index:
            self.state.selected_block_index = None
        elif self.state.selected_block_index is not None and self.state.selected_block_index > index:
            self.state.selected_block_index -= 1

        if self.state.selected_block_indices:
            updated = set()
            for idx in self.state.selected_block_indices:
                if idx == index:
                    continue
                if idx > index:
                    updated.add(idx - 1)
                else:
                    updated.add(idx)
            self.state.selected_block_indices = updated

        if self.state.selected_block_index is not None and self.state.selected_block_index >= len(self.state.blocks):
            self.state.selected_block_index = len(self.state.blocks) - 1 if self.state.blocks else None

        if self.state.selected_block_index is None and self.state.selected_block_indices:
            self.state.selected_block_index = next(iter(sorted(self.state.selected_block_indices)))

    def delete_selected_blocks(self):
        """Delete all selected blocks."""
        indices = self.state.get_selected_indices()
        if not indices:
            return

        for index in sorted(indices, reverse=True):
            self.delete_block(index)

        self.state.selected_block_index = None
        self.state.selected_block_indices.clear()

    def move_selected_block(self, dx, dy):
        """Move the currently selected block."""
        if self.state.selected_block_index is None or not (0 <= self.state.selected_block_index < len(self.state.blocks)):
            return

        block = self.state.blocks[self.state.selected_block_index]
        block[1] = round((float(block[1]) + float(dx)) * 2) / 2
        block[2] = round((float(block[2]) + float(dy)) * 2) / 2

    def move_selected_blocks(self, dx, dy):
        """Move all selected blocks."""
        indices = self.state.get_selected_indices()
        if not indices:
            return

        for index in indices:
            if not (0 <= index < len(self.state.blocks)):
                continue
            block = self.state.blocks[index]
            block[1] = round((float(block[1]) + float(dx)) * 2) / 2
            block[2] = round((float(block[2]) + float(dy)) * 2) / 2

    def rotate_selected_block(self, delta_degrees):
        """Rotate the currently selected block."""
        if self.state.selected_block_index is None or not (0 <= self.state.selected_block_index < len(self.state.blocks)):
            return

        block = self.state.blocks[self.state.selected_block_index]
        while len(block) < 6:
            block.append(0)

        block[5] = self.normalize_rotation(block[5] + delta_degrees)

    def rotate_selected_blocks(self, delta_degrees):
        """Rotate all selected blocks."""
        indices = self.state.get_selected_indices()
        if not indices:
            return

        for index in indices:
            if not (0 <= index < len(self.state.blocks)):
                continue

            block = self.state.blocks[index]
            while len(block) < 6:
                block.append(0)

            block[5] = self.normalize_rotation(block[5] + delta_degrees)

    def find_block_at_pos(self, pos):
        """Find a block at the given screen position."""
        world_x, world_y = self.state.coords.screen_to_world(pos)

        for index in range(len(self.state.blocks) - 1, -1, -1):
            block = self.state.blocks[index]
            rect = self.block_rect(block)
            if rect and rect.collidepoint(world_x, world_y):
                return index

        return None

    def block_rect(self, block):
        """Get the screen rect for a block."""
        normalized = self.normalize_block(block)
        if normalized is None:
            return None

        _, grid_x, grid_y, _, scale, _rotation = normalized
        rect = self.state.coords.level_rect_from_grid(grid_x, grid_y, scale)
        if rect is None:
            return None

        return pg.Rect(rect)

    def block_grid_pos(self, block):
        """Get the grid position of a block."""
        normalized = self.normalize_block(block)
        if normalized is None:
            return None

        return normalized[1], normalized[2]

    def tile_from_block(self, block):
        """Create a tile object from block data."""
        normalized = self.normalize_block(block)
        if normalized is None:
            return None

        tile_type, grid_x, grid_y, color, scale, rotation = normalized

        tile_class = self.state.tile_classes.get(str(tile_type))
        if tile_class is None:
            return None

        rect = self.state.coords.level_rect_from_grid(grid_x, grid_y, scale)
        if rect is None:
            return None

        tile = tile_class(rect, color)
        tile._editor_rotation = rotation
        return tile
