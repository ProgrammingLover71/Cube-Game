import pygame as pg
from level_select_state import LevelSelectState
from level_editor import LevelEditorState


class MenuState:
	def enter(self, manager):
		self.manager = manager
		self.font_big = pg.font.SysFont(None, 96)
		self.font_sml = pg.font.SysFont(None, 28)
		self.button_size = (140, 56)
		self.hovered_button = None

	def handle_event(self, event):
		if event.type == pg.KEYDOWN:
			if event.key == pg.K_RETURN:
				self.manager.change(LevelSelectState())
			elif event.key == pg.K_ESCAPE:
				pg.event.post(pg.event.Event(pg.QUIT))

		elif event.type == pg.MOUSEMOTION:
			self.hovered_button = self._button_at_pos(event.pos)

		elif event.type == pg.MOUSEBUTTONDOWN:
			if event.button == 1:
				button = self._button_at_pos(event.pos)
				if button == "play":
					self.manager.change(LevelSelectState())
				elif button == "editor":
					self.manager.change(LevelEditorState())
				elif button == "exit":
					pg.event.post(pg.event.Event(pg.QUIT))

	def update(self, dt):
		pass

	def render(self, surface):
		surface.fill((30, 30, 30))
		title = self.font_big.render("Cube Game", True, (255, 255, 255))
		surface.blit(title, title.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 - 160)))

		self._render_button(surface, "play", "Play")
		self._render_button(surface, "editor", "Editor")
		self._render_button(surface, "exit", "Exit")

	def _render_button(self, surface, button_id, label):
		button_rect = self._button_rect(button_id)
		color = (140, 140, 140) if self.hovered_button == button_id else (100, 100, 100)
		pg.draw.rect(surface, color, button_rect, border_radius=8)

		button_text = self.font_sml.render(label, True, (255, 255, 255))
		surface.blit(button_text, button_text.get_rect(center=button_rect.center))

	def _button_at_pos(self, pos):
		for button_id in ("play", "editor", "exit"):
			if self._button_rect(button_id).collidepoint(pos):
				return button_id

		return None

	def _button_rect(self, button_id):
		try:
			w, h = pg.display.get_surface().get_size()
		except Exception:
			w, h = 1280, 720

		rect = pg.Rect(0, 0, self.button_size[0], self.button_size[1])
		y_offsets = {
			"play": -72,
			"editor": 0,
			"exit": 72,
		}
		rect.center = (w // 2, h // 2 + y_offsets[button_id])
		return rect

