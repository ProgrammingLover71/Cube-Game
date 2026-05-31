import pygame as pg


class State:
    def enter(self, manager):
        self.manager = manager

    def exit(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def render(self, surface):
        pass


class StateManager:

    def __init__(self, initial_state):
        self.current = initial_state
        self.pending_state = None
        self.transition_duration = 0.18
        self.transition_timer = 0.0
        self.transition_phase = None

        if hasattr(self.current, 'enter'):
            self.current.enter(self)

    @property
    def is_transitioning(self):
        return self.transition_phase is not None

    def change(self, new_state):
        self.pending_state = new_state
        self.transition_timer = 0.0
        self.transition_phase = "out"

    def finish_state_change(self):
        if hasattr(self.current, 'exit'):
            self.current.exit()

        self.current = self.pending_state
        self.pending_state = None

        if hasattr(self.current, 'enter'):
            self.current.enter(self)

    def handle_event(self, event):
        if self.is_transitioning:
            return

        if hasattr(self.current, 'handle_event'):
            self.current.handle_event(event)

    def update(self, dt):
        if self.is_transitioning:
            self.update_transition(dt)
            return

        if hasattr(self.current, 'update'):
            self.current.update(dt)

    def update_transition(self, dt):
        self.transition_timer += dt
        if self.transition_timer < self.transition_duration:
            return

        self.transition_timer = 0.0
        if self.transition_phase == "out":
            self.finish_state_change()
            self.transition_phase = "in"
        else:
            self.transition_phase = None

    def render(self, surface):
        if hasattr(self.current, 'render'):
            self.current.render(surface)

        if self.is_transitioning:
            self.render_transition(surface)

    def render_transition(self, surface):
        progress = min(1.0, self.transition_timer / self.transition_duration)
        if self.transition_phase == "out":
            alpha = int(255 * progress)
        else:
            alpha = int(255 * (1.0 - progress))

        overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))
