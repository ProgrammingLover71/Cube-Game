import json
from numbers import Number

from .tile import BlockTile, GroundTile, NormalSpikeTile, ShortBlockTile, ShortSpikeTile, SolidBlockTile, YellowOrbTile, YellowPadTile, ShipPortalTile


class LevelMixin:
    def build_blocks(self):
        """Build the default ground as one large collision object."""
        self.blocks = self.ground_tiles()

    def _build_blocks(self):
        self.build_blocks()

    def blocks_from_rect(self, platform):
        return [GroundTile(platform)]

    def _blocks_from_rect(self, platform):
        return self.blocks_from_rect(platform)

    def load_level(self, path):
        """Load a JSON level from either the legacy list or folder-level format."""
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            self.build_blocks()
            return

        level_items = self.level_items_from_data(data)
        if level_items is None:
            self.build_blocks()
            return

        self.level_metadata = self.level_metadata_from_data(data)
        tile_size = int(self.tile_size)
        self.blocks = []

        for item in level_items:
            obj = self.parse_level_item(item)
            if obj is None:
                continue

            tile_type = obj.get("type")
            grid_x = obj.get("x")
            grid_y = obj.get("y")
            color = obj.get("color")
            scale = obj.get("scale", 1)

            if tile_type is None or grid_x is None or grid_y is None:
                continue

            rect = self.level_rect_from_grid(grid_x, grid_y, tile_size, scale)
            if rect is None:
                continue

            tile = self.create_level_tile(tile_type, rect, color)
            if tile:
                tile._level_data = obj
                tile._rotation = self.normalize_rotation(obj.get("rotation", 0))
                tile._properties = obj.get("properties", {})
                if hasattr(tile, "apply_level_data"):
                    try:
                        tile.apply_level_data(obj)
                    except Exception:
                        pass
                self.blocks.append(tile)

        self.blocks.extend(self.ground_tiles())

        self.world_width = max((tile.rect.right for tile in self.blocks), default=0)

    def level_items_from_data(self, data):
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in ("blocks", "tiles", "objects"):
                items = data.get(key)
                if isinstance(items, list):
                    return items

        return None

    def level_metadata_from_data(self, data):
        if not isinstance(data, dict):
            return {}

        return {key: value for key, value in data.items() if key not in ("blocks", "tiles", "objects")}

    def parse_level_item(self, item):
        if isinstance(item, list):
            if len(item) < 3:
                return None

            tile_type = item[0]
            grid_x = item[1]
            grid_y = item[2]

            color = None
            scale = 1
            rotation = 0

            tail = list(item[3:])

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

            return {
                "type": tile_type,
                "x": grid_x,
                "y": grid_y,
                "color": color,
                "scale": scale,
                "rotation": rotation,
            }

        if isinstance(item, dict):
            return {
                "type": item.get("type"),
                "x": item.get("x"),
                "y": item.get("y"),
                "color": item.get("color"),
                "scale": item.get("scale", 1),
                "rotation": item.get("rotation", 0),
            }

        return None

    def level_rect_from_grid(self, grid_x, grid_y, tile_size, scale=1):
        try:
            scale_x, scale_y = self.normalize_scale(scale)
            width = max(1, round(tile_size * scale_x))
            height = max(1, round(tile_size * scale_y))
            x = round(self.grid_origin_x + float(grid_x) * tile_size)
            y = round(self.ground_y - float(grid_y) * tile_size - height)
        except Exception:
            return None

        return x, y, width, height

    def is_scale_value(self, value):
        return isinstance(value, Number) or (
            isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(v, Number) for v in value)
        )

    def normalize_scale(self, scale):
        if isinstance(scale, Number):
            value = max(0.1, float(scale))
            return value, value

        if isinstance(scale, (list, tuple)) and len(scale) >= 2:
            return max(0.1, float(scale[0])), max(0.1, float(scale[1]))

        return 1, 1

    def normalize_rotation(self, rotation):
        try:
            return int(round(float(rotation))) % 360
        except Exception:
            return 0

    def ground_tiles(self):
        return [GroundTile(platform) for platform in self.platforms]

    def create_level_tile(self, tile_type, rect, color=None):
        tile_classes = {
            "block": BlockTile,
            "block_short": ShortBlockTile,
            "block_solid": SolidBlockTile,
            "spike_norm": NormalSpikeTile,
            "spike_short": ShortSpikeTile,
            "orb_y": YellowOrbTile,
            "pad_y": YellowPadTile,
            "portal_ship": ShipPortalTile,
        }

        tile_class = tile_classes.get(str(tile_type).lower())
        if tile_class is None:
            return None

        tile = tile_class(rect, color)
        return tile