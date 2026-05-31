import pygame as pg
from state_manager import StateManager
from menu_state import MenuState


def main():

    pg.mixer.pre_init(44100, -16, 2, 512)
    pg.init()
    screen = pg.display.set_mode((1280, 720))
    pg.display.set_caption("Cube Game")
    clock = pg.time.Clock()

    manager = StateManager(MenuState())

    running = True
    while running:

        dt = clock.tick(120) / 1000.0
        
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            else:
                manager.handle_event(event)

        manager.update(dt)
        manager.render(screen)
        pg.display.flip()

    pg.quit()


if __name__ == "__main__":
    main()
