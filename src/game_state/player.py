import pygame as pg



JUMP_KEYS = (pg.K_SPACE, pg.K_UP, pg.K_w)


class PlayerMixin:
    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            self.handle_keydown(event.key)
        elif event.type == pg.KEYUP:
            self.handle_keyup(event.key)

    def handle_keydown(self, key):
        if key == pg.K_ESCAPE and getattr(self, "playtest_mode", False):
            self.stop_level_music()
            from level_editor_state import LevelEditorState
            self.manager.change(LevelEditorState(self.level_path))
            return

        if getattr(self, "is_dead", False):
            if key == pg.K_ESCAPE:
                from level_select_state import LevelSelectState
                self.manager.change(LevelSelectState())
            return

        if key in JUMP_KEYS:
            if self.mode not in ("ship,"):
                self.try_jump(reset_cooldown=True)
            self.click_touching_tiles()

        if key == pg.K_ESCAPE:
            from level_select_state import LevelSelectState
            self.manager.change(LevelSelectState())

    def handle_keyup(self, key):
        if key in JUMP_KEYS:
            self.jump_cooldown_timer = 0.0

    def update(self, dt):
        if not self.start_level_run_if_ready():
            return

        if self.is_dead:
            self.update_death(dt)
            return

        self.level_time += dt
        keys = pg.key.get_pressed()

        if self.mode == "ship":
            self.update_ship_mode(dt, keys)
        else:
            self.update_cube_mode(dt, keys)

        self.update_tiles(dt)
        self.update_camera()

    def update_cube_mode(self, dt, keys):
        self.update_jump_timers(dt)
        self.handle_held_jump(keys)
        self.update_horizontal_velocity(keys)
        self.apply_gravity(dt)
        self.move_horizontally(dt)
        if self.move_vertically(dt):
            return

    def update_ship_mode(self, dt, keys):
        # Ship always moves right like the cube
        self.vel.x = self.speed
        
        # GD-style vertical acceleration: accelerate up when pressing UP/W, accelerate down otherwise
        ship_accel = self.ship_vertical_accel
        if any(keys[k] for k in JUMP_KEYS):
            self.vel.y -= ship_accel * 1.1 * dt  # Accelerate upward
        self.vel.y += self.gravity * 0.5 * dt
        
        # Move horizontally
        self.move_horizontally(dt)
        
        # Move vertically and handle collisions
        if self.move_vertically(dt):
            return
        

    def update_jump_timers(self, dt):
        if self.coyote_timer > 0:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        if self.jump_cooldown_timer > 0:
            self.jump_cooldown_timer = max(0.0, self.jump_cooldown_timer - dt)

    def handle_held_jump(self, keys):
        jump_pressed = any(keys[key] for key in JUMP_KEYS)
        if jump_pressed and self.jump_cooldown_timer <= 0:
            self.try_jump(reset_cooldown=False)

    def try_jump(self, reset_cooldown):
        if not self.can_jump():
            return False

        self.vel.y = self.jump_impulse
        self.on_ground = False
        self.coyote_timer = 0.0
        self.jump_cooldown_timer = 0.0 if reset_cooldown else self.jump_cooldown
        return True

    def can_jump(self):
        return self.on_ground or self.coyote_timer > 0

    def click_touching_tiles(self):
        player_rect = self.player_rect()
        for tile in self.blocks:
            if hasattr(tile, "on_click") and tile.rect.colliderect(player_rect):
                tile.on_click(self)

    def update_horizontal_velocity(self, keys):
        self.vel.x = self.speed
        if keys[pg.K_LEFT]:
            self.vel.x = -self.speed

    def apply_gravity(self, dt):
        self.vel.y += self.gravity * dt

    def move_horizontally(self, dt):
        self.pos.x += self.vel.x * dt

    def move_vertically(self, dt):
        self.pos.y += self.vel.y * dt

        player_rect = self.player_rect()
        was_on_ground = self.on_ground
        self.on_ground = False

        prev_bottom = self.previous_player_bottom(player_rect, dt)
        for tile in self.blocks:
            result = self.handle_tile_collision(tile, player_rect, prev_bottom)
            if result == "stop":
                return True
            if result == "ground":
                break

        self.update_coyote_timer(was_on_ground)
        return False

    def player_rect(self):
        rect = pg.Rect(0, 0, int(self.player_size.x), int(self.player_size.y))
        rect.center = (int(self.pos.x), int(self.pos.y))
        return rect

    def previous_player_bottom(self, player_rect, dt):
        prev_center_y = self.pos.y - self.vel.y * dt
        return prev_center_y + player_rect.height / 2

    def handle_tile_collision(self, tile, player_rect, prev_bottom):
        result = tile.handle_collision(player_rect, self.vel, prev_bottom)
        parsed = self.parse_collision_result(result)
        if parsed is None:
            return False

        handled, new_center_y, new_vel_y, on_ground, action = parsed
        if not handled:
            return False

        if action == "kill":
            self.die()
            return "stop"

        if action == "end":
            self.complete_level()
            return "stop"

        if action == "ship_mode":
            self.mode = "ship"
            return None

        if new_center_y is not None:
            self.pos.y = new_center_y

        if new_vel_y is not None:
            self.vel.y = new_vel_y

        self.on_ground = bool(on_ground)
        player_rect.center = (int(self.pos.x), int(self.pos.y))
        return "ground" if self.on_ground else None

    def parse_collision_result(self, result):
        if not isinstance(result, (list, tuple)):
            return None

        if len(result) == 5:
            return result

        if len(result) == 4:
            handled, new_center_y, new_vel_y, on_ground = result
            return handled, new_center_y, new_vel_y, on_ground, None

        return None

    def update_coyote_timer(self, was_on_ground):
        if self.on_ground:
            if not was_on_ground:
                self.coyote_timer = self.coyote_time
        elif was_on_ground:
            self.coyote_timer = self.coyote_time

    def update_camera(self):
        surface = pg.display.get_surface()
        if not surface:
            return

        width, height = surface.get_size()
        threshold_x = width * 0.3
        threshold_y = height * 0.5
        
        if (self.pos.x - self.camera_x) > threshold_x:
            self.camera_x = self.pos.x - threshold_x
        
        # Follow player vertically
        # use min to prevent showing area below the level
        target_y = int(self.pos.y - threshold_y)
        self.camera_y += (target_y - self.camera_y) // 16

    def update_tiles(self, dt):
        for tile in self.blocks:
            tile.update(dt)

    def update_death(self, dt):
        self.death_timer += dt
        self.update_tiles(dt)
        if self.death_timer >= self.death_duration:
            self.respawn()

    def respawn(self):
        self.restart_level_run()
    

    def complete_level(self):
        self.stop_level_music()
        from level_select_state import LevelSelectState
        self.manager.change(LevelSelectState())