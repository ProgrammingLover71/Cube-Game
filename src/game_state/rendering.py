import pygame as pg
import math


class RenderingMixin:
    def render(self, surface):
        surface.fill((80, 160, 240))
        self.render_tiles(surface)
        self.render_player(surface)
        self.render_hud(surface)
        
    def render_tiles(self, surface):
        sorted_blocks = sorted(self.blocks, key=lambda tile: tile.z_order)
        for tile in sorted_blocks:
            tile_x = tile.rect.x
            if self.pos.x - tile_x > 720 and not (type(tile).__name__ == "GroundTile"):
                continue
            
            rotation = getattr(tile, "_rotation", 0) % 360

            if rotation == 0:
                tile.render(
                    surface,
                    camera_x=self.camera_x,
                    camera_y=self.camera_y,
                )
                continue

            rect = tile.rect

            temp = pg.Surface(
                (max(1, rect.w), max(1, rect.h)),
                pg.SRCALPHA,
            )

            try:
                tile.render(
                    temp,
                    camera_x=rect.x,
                    camera_y=rect.y,
                )
            except TypeError:
                try:
                    tile.render(
                        temp,
                        rect.x,
                        rect.y,
                    )
                except TypeError:
                    tile.render(temp)

            rotated = pg.transform.rotate(temp, -rotation)

            screen_x = rect.centerx - self.camera_x
            screen_y = rect.centery - self.camera_y

            rotated_rect = rotated.get_rect(
                center=(screen_x, screen_y)
            )

            surface.blit(rotated, rotated_rect)

    def render_player(self, surface):
        if getattr(self, "is_dead", False):
            self.render_death_explosion(surface)
            return

        rect = pg.Rect(0, 0, int(self.player_size.x), int(self.player_size.y))
        rect.center = (int(self.pos.x - self.camera_x), int(self.pos.y - self.camera_y))
        
        if getattr(self, "mode", "cube") == "ship":
            self.render_ship(surface, rect)
        else:
            pg.draw.rect(surface, (200, 50, 50), rect, border_radius=6)

    def render_ship(self, surface, rect):
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

    def render_death_explosion(self, surface):
        if self.death_pos is None:
            return

        progress = min(1.0, self.death_timer / self.death_duration)
        center = pg.Vector2(self.death_pos.x - self.camera_x, self.death_pos.y - self.camera_y)
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

    def render_hud(self, surface):
        info = f"Attempt {self.attempts} | Progress: idk it's not in yet"
        text = self.font.render(info, True, (0, 0, 0))
        surface.blit(text, (10, 10))
