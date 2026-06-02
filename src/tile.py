import math

import pygame as pg


class Tile:
    """Base tile class."""
    default_color = (120, 120, 120)
    z_order = 0

    def __init__(self, rect, color=None):
        self.rect = pg.Rect(rect)
        self.color = self.normalize_color(color) or self.default_color
        self._baked = None
        self._bake()

    def _bake(self):
        """Pre-render the tile to a cached surface. Override in subclasses."""
        pass

    @staticmethod
    def normalize_color(color):
        if color is None:
            return None

        if isinstance(color, str):
            try:
                parsed = pg.Color(color)
                return parsed.r, parsed.g, parsed.b
            except ValueError:
                return None

        if isinstance(color, (list, tuple)) and len(color) >= 3:
            try:
                return tuple(max(0, min(255, int(value))) for value in color[:3])
            except (TypeError, ValueError):
                return None

        return None

    def update(self, dt):
        pass

    def screen_rect(self, camera_x=0, camera_y=0, zoom=1.0):
        zoom = float(zoom) if zoom else 1.0
        return pg.Rect(
            int((self.rect.x - camera_x) * zoom),
            int((self.rect.y - camera_y) * zoom),
            max(1, int(self.rect.w * zoom)),
            max(1, int(self.rect.h * zoom)),
        )

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if self._baked is not None and zoom == 1.0:
            surface.blit(self._baked, (self.rect.x - int(camera_x), self.rect.y - int(camera_y)))
            return
        # fallback for zoom != 1.0 or unbaked tiles
        draw_rect = self.screen_rect(camera_x, camera_y, zoom)
        pg.draw.rect(surface, self.color, draw_rect)

    def render_faded_rect(self, surface, rect):
        # Only called as fallback (zoom != 1.0) — not hot path anymore
        fade = self.create_vertical_fade(rect.size, self.color)
        surface.blit(fade, rect.topleft)

    def render_faded_polygon(self, surface, points):
        # Only called as fallback (zoom != 1.0) — not hot path anymore
        bounds = pg.Rect(points[0], (0, 0))
        for point in points[1:]:
            bounds.union_ip(pg.Rect(point, (0, 0)))

        bounds.width += 1
        bounds.height += 1
        local_points = [(x - bounds.x, y - bounds.y) for x, y in points]
        fade = self.create_vertical_fade(bounds.size, self.color)

        mask = pg.Surface(bounds.size, pg.SRCALPHA)
        pg.draw.polygon(mask, (255, 255, 255, 255), local_points)
        fade.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        surface.blit(fade, bounds.topleft)

    def create_vertical_fade(self, size, color):
        width, height = max(1, size[0]), max(1, size[1])
        fade = pg.Surface((width, height), pg.SRCALPHA)
        denominator = max(1, height - 1)

        for y in range(height):
            alpha = int(255 * (1 - y / denominator))
            pg.draw.line(fade, (*color, alpha), (0, y), (width, y))

        return fade

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        return (False, None, None, False, None)


class BlockTile(Tile):
    default_color = (0, 0, 0)
    z_order = 10
    ledge_landing_tolerance = 18
    ledge_climb_tolerance = 35
    underside_kill_speed = 650

    def __init__(self, rect, color=None):
        super().__init__(rect, color)

    def _bake(self):
        w, h = self.rect.w, self.rect.h
        surf = pg.Surface((w, h), pg.SRCALPHA)
        fade = self.create_vertical_fade((w, h), self.color)
        surf.blit(fade, (0, 0))
        pg.draw.rect(surf, (255, 255, 255), (0, 0, w, h), width=2)
        self._baked = surf

    def update(self, dt):
        pass

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if self._baked is not None and zoom == 1.0:
            surface.blit(self._baked, (self.rect.x - int(camera_x), self.rect.y - int(camera_y)))
            return
        draw_rect = self.screen_rect(camera_x, camera_y, zoom)
        self.render_faded_rect(surface, draw_rect)
        pg.draw.rect(surface, (255, 255, 255), draw_rect, width=max(1, int(2 * zoom)))

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        block = self.rect
        if not player_rect.colliderect(block):
            return (False, None, None, False, None)

        previous_top = prev_bottom - player_rect.height
        overlap_x = min(player_rect.right, block.right) - max(player_rect.left, block.left)

        if overlap_x > 0 and self.is_near_top_lip(player_rect, prev_bottom):
            new_center_y = block.top - player_rect.height / 2
            return (True, new_center_y, 0.0, True, None)

        if player_vel.y < 0 and previous_top >= block.bottom - 1:
            if abs(player_vel.y) >= self.underside_kill_speed:
                return (True, None, None, False, "kill")
            new_center_y = block.bottom + player_rect.height / 2
            return (True, new_center_y, 0.0, False, None)

        return (True, None, None, False, "kill")

    def is_near_top_lip(self, player_rect, prev_bottom):
        block = self.rect
        previous_feet_near_top = prev_bottom <= block.top + self.ledge_landing_tolerance
        current_feet_near_top = player_rect.bottom <= block.top + self.ledge_climb_tolerance
        return previous_feet_near_top or current_feet_near_top

    def on_click(self, gs):
        pass


class ShortBlockTile(BlockTile):
    """Half-height block. Extends BlockTile — was 60 lines of copy-paste before."""
    z_order = 10

    def _bake(self):
        w, h = self.rect.w, self.rect.h // 2
        surf = pg.Surface((w, h), pg.SRCALPHA)
        fade = self.create_vertical_fade((w, h), self.color)
        surf.blit(fade, (0, 0))
        pg.draw.rect(surf, (255, 255, 255), (0, 0, w, h), width=2)
        self._baked = surf

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if self._baked is not None and zoom == 1.0:
            surface.blit(self._baked, (self.rect.x - int(camera_x), self.rect.y - int(camera_y)))
            return
        draw_rect = self.screen_rect(camera_x, camera_y, zoom)
        draw_rect.h //= 2
        self.render_faded_rect(surface, draw_rect)
        pg.draw.rect(surface, (255, 255, 255), draw_rect, width=max(1, int(2 * zoom)))


class SolidBlockTile(Tile):
    default_color = (0, 0, 0)
    z_order = 15
    ledge_landing_tolerance = 18
    ledge_climb_tolerance = 35
    underside_kill_speed = 650
    alpha = 0.5

    def __init__(self, rect, color=None):
        super().__init__(rect, color)

    def _bake(self):
        w, h = self.rect.w, self.rect.h
        surf = pg.Surface((w, h), pg.SRCALPHA)
        col = (self.color[0], self.color[1], self.color[2], int(255 * self.alpha))
        surf.fill(col)
        self._baked = surf

    def update(self, dt):
        pass

    def render_faded_rect(self, surface, rect):
        # Override to render solid color instead of faded
        solid = pg.Surface(rect.size)
        col = (self.color[0], self.color[1], self.color[2], int(255 * self.alpha))
        solid.fill(col)
        surface.blit(solid, rect.topleft)

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if self._baked is not None and zoom == 1.0:
            surface.blit(self._baked, (self.rect.x - int(camera_x), self.rect.y - int(camera_y)))
            return
        draw_rect = self.screen_rect(camera_x, camera_y, zoom)
        self.render_faded_rect(surface, draw_rect)

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        return (True, None, None, False, None)

    def is_near_top_lip(self, player_rect, prev_bottom):
        block = self.rect
        previous_feet_near_top = prev_bottom <= block.top + self.ledge_landing_tolerance
        current_feet_near_top = player_rect.bottom <= block.top + self.ledge_climb_tolerance
        return previous_feet_near_top or current_feet_near_top

    def on_click(self, gs):
        pass


class GroundTile(BlockTile):
    default_color = (35, 95, 150)
    z_order = -100

    def _bake(self):
        pass  # 50000px wide — baking this would be insane

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        draw_rect = self.screen_rect(camera_x, camera_y, zoom)
        visible_rect = draw_rect.clip(surface.get_rect())
        if visible_rect.width <= 0 or visible_rect.height <= 0:
            return

        pg.draw.rect(surface, self.color, visible_rect)
        pg.draw.line(
            surface,
            (255, 255, 255),
            visible_rect.topleft,
            visible_rect.topright,
            width=max(1, int(2 * zoom)),
        )

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        block = self.rect
        if not player_rect.colliderect(block):
            return (False, None, None, False, None)

        if player_vel.y > 0 and prev_bottom <= block.top + self.ledge_landing_tolerance:
            new_center_y = block.top - player_rect.height / 2
            return (True, new_center_y, 0.0, True, None)

        return (False, None, None, False, None)

    def on_click(self, gs):
        pass


class NormalSpikeTile(Tile):
    default_color = (0, 0, 0)
    z_order = 20

    def __init__(self, rect, color=None):
        super().__init__(rect, color)
        r = self.rect.copy()
        w = int(r.width * 0.4)
        h = int(r.height * 0.4)
        x = r.left + (r.width - w) // 2
        y = r.top + int(r.height * 0.5)
        self.hitbox = pg.Rect(x, y, w, h)

    def _bake(self):
        w, h = self.rect.w, self.rect.h
        surf = pg.Surface((w, h), pg.SRCALPHA)
        points = [(0, h), (w / 2, 0), (w, h)]
        fade = self.create_vertical_fade((w, h), self.color)
        mask = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.polygon(mask, (255, 255, 255, 255), points)
        fade.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        surf.blit(fade, (0, 0))
        pg.draw.polygon(surf, (255, 255, 255), points, width=2)
        self._baked = surf

    def update(self, dt):
        pass

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if self._baked is not None and zoom == 1.0:
            surface.blit(self._baked, (self.rect.x - int(camera_x), self.rect.y - int(camera_y)))
            return
        r = self.screen_rect(camera_x, camera_y, zoom)
        cx, cy, w, h = r.left, r.top, r.width, r.height
        points = [(cx, cy + h), (cx + w / 2, cy), (cx + w, cy + h)]
        self.render_faded_polygon(surface, points)
        pg.draw.polygon(surface, (255, 255, 255), points, width=max(1, int(2 * zoom)))

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        if player_rect.colliderect(self.hitbox):
            return (True, None, None, False, "kill")
        return (False, None, None, False, None)

    def on_click(self, gs):
        pass


class ShortSpikeTile(Tile):
    default_color = (0, 0, 0)
    z_order = 20

    def __init__(self, rect, color=None):
        super().__init__(rect, color)
        r = self.rect.copy()
        w = int(r.width * 0.4)
        h = int(r.height * 0.4)
        x = r.left + (r.width - w) // 2
        y = r.top + int(r.height * 0.5)
        self.hitbox = pg.Rect(x, y, w, h)

    def _bake(self):
        w, h_full = self.rect.w, self.rect.h
        spike_h = (h_full * 2) // 5
        spike_y = h_full - spike_h

        surf = pg.Surface((w, h_full), pg.SRCALPHA)

        # Bake only the spike area, positioned at the bottom of the tile
        fade = self.create_vertical_fade((w, spike_h), self.color)
        mask = pg.Surface((w, spike_h), pg.SRCALPHA)
        mask_points = [(0, spike_h), (w / 2, 0), (w, spike_h)]
        pg.draw.polygon(mask, (255, 255, 255, 255), mask_points)
        fade.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        surf.blit(fade, (0, spike_y))

        full_points = [(0, h_full), (w / 2, spike_y), (w, h_full)]
        pg.draw.polygon(surf, (255, 255, 255), full_points, width=2)
        self._baked = surf

    def update(self, dt):
        pass

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if self._baked is not None and zoom == 1.0:
            surface.blit(self._baked, (self.rect.x - int(camera_x), self.rect.y - int(camera_y)))
            return
        r = self.screen_rect(camera_x, camera_y, zoom)
        w = r.width
        h = (r.height * 2) // 5
        cx = r.left
        cy = r.top + (r.height - h)
        points = [(cx, cy + h), (cx + w / 2, cy), (cx + w, cy + h)]
        self.render_faded_polygon(surface, points)
        pg.draw.polygon(surface, (255, 255, 255), points, width=max(1, int(2 * zoom)))

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        if player_rect.colliderect(self.hitbox):
            return (True, None, None, False, "kill")
        return (False, None, None, False, None)

    def on_click(self, gs):
        pass


class YellowOrbTile(Tile):
    default_color = (255, 255, 30)
    z_order = 20

    def __init__(self, rect, color=None):
        super().__init__(rect, color)
        r = self.rect.copy()
        w = int(r.width * 1.15)
        h = int(r.height * 1.15)
        x = r.left + (r.width - w) // 2
        y = r.top + (r.height - h) // 2
        self.hitbox = pg.Rect(x, y, w, h)

    def _bake(self):
        w, h = self.rect.w, self.rect.h
        surf = pg.Surface((w, h), pg.SRCALPHA)
        radius = min(w, h) // 2
        center = (w // 2, h // 2)
        pg.draw.circle(surf, (255, 255, 255), center, radius)
        pg.draw.circle(surf, (85, 130, 185), center, max(1, int(radius * 0.82)))
        pg.draw.circle(surf, (255, 255, 255), center, max(1, int(radius * 0.64)))
        pg.draw.circle(surf, self.color, center, max(1, int(radius * 0.55)))
        pg.draw.circle(surf, (255, 255, 110), center, max(1, int(radius * 0.38)))
        self._baked = surf

    def update(self, dt):
        pass

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if self._baked is not None and zoom == 1.0:
            surface.blit(self._baked, (self.rect.x - int(camera_x), self.rect.y - int(camera_y)))
            return
        r = self.screen_rect(camera_x, camera_y, zoom)
        radius = min(r.width, r.height) // 2
        center = r.center
        pg.draw.circle(surface, (255, 255, 255), center, radius)
        pg.draw.circle(surface, (85, 130, 185), center, max(1, int(radius * 0.82)))
        pg.draw.circle(surface, (255, 255, 255), center, max(1, int(radius * 0.64)))
        pg.draw.circle(surface, self.color, center, max(1, int(radius * 0.55)))
        pg.draw.circle(surface, (255, 255, 110), center, max(1, int(radius * 0.38)))

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        if player_rect.colliderect(self.rect):
            return (True, None, None, False, None)
        return (False, None, None, False, None)

    def on_click(self, gs):
        gs.vel.y = -1080


class YellowPadTile(Tile):
    default_color = (255, 255, 30)
    z_order = 20

    def __init__(self, rect, color=None):
        super().__init__(rect, self.default_color)
        r = self.rect.copy()
        w = int(r.width * 0.9)
        h = int(r.height * 0.5)
        x = r.left + (r.width - w) // 2
        y = r.top + int(r.height * 0.6)
        self.hitbox = pg.Rect(x, y, w, h)

    def update(self, dt):
        pass

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        r = self.screen_rect(camera_x, camera_y, zoom)
        r.y += int(r.height * 0.9)

        ellipse_rect = pg.Rect(r.x, r.y, r.width, max(1, r.height // 6))
        pg.draw.ellipse(surface, self.color, ellipse_rect)
        pg.draw.arc(
            surface,
            self.color,
            ellipse_rect,
            3.14,
            2 * 3.14,
            max(1, int(12 * zoom)),
        )

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        if player_rect.colliderect(self.hitbox):
            return (True, None, -1560, False, None)
        return (False, None, None, False, None)  # Fixed: nu mai returnam -1560 cand nu e coliziune


############################################################################################################
## TRIGGERRRRSSSSS
############################################################################################################


class EndTriggerTile(Tile):
    default_color = (30, 30, 30)
    z_order = 30

    def update(self, dt):
        pass

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        draw_rect = self.screen_rect(camera_x, camera_y, zoom)
        pg.draw.rect(surface, self.default_color, draw_rect)
        pg.draw.rect(surface, (255, 255, 255), draw_rect, width=max(1, int(2 * zoom)))

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        if player_rect.colliderect(self.rect):
            return (True, None, None, False, "end")
        return (False, None, None, False, None)

    def on_click(self, gs):
        pass


class ShipPortalTile(Tile):
    default_color = (255, 100, 200)
    z_order = 30

    def __init__(self, rect, color=None):
        super().__init__(rect, self.default_color)
        self.animation_time = 0.0

    def _bake(self):
        pass  # animat — nu putem cache-ui

    def update(self, dt):
        self.animation_time += dt

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        r = self.screen_rect(camera_x, camera_y, zoom)
        center = r.center

        portal_width = int(r.width * 1.5)
        portal_height = int(r.height * 2.5)

        outer_ellipse = pg.Rect(
            center[0] - portal_width // 2,
            center[1] - portal_height // 2,
            portal_width,
            portal_height,
        )
        pg.draw.ellipse(surface, (255, 100, 200), outer_ellipse, width=max(2, int(4 * zoom)))

        orb_radius = max(3, int(6 * zoom))
        orb_distance = max(portal_width, portal_height) // 2 + 15
        phase = self.animation_time * 2

        for i in range(4):
            angle = phase + (i * 1.5708)
            orb_x = int(center[0] + math.cos(angle) * orb_distance)
            orb_y = int(center[1] + math.sin(angle) * orb_distance)
            pg.draw.circle(surface, (255, 150, 220), (orb_x, orb_y), orb_radius)
            pg.draw.circle(surface, (255, 200, 240), (orb_x, orb_y), max(1, orb_radius // 2))

    def handle_collision(self, player_rect, player_vel, prev_bottom):
        if player_rect.colliderect(self.rect):
            return (True, None, None, False, "ship_mode")
        return (False, None, None, False, None)

    def on_click(self, gs):
        pass