import os
import tkinter

import pygame

from Engine.MainMenu import MainMenu
from Tools.CoreService import CoreService

core_service = CoreService()


def main():
    os.environ["SDL_MOUSE_FOCUS_CLICKTHROUGH"] = "1"
    main_menu = MainMenu()
    dimension = main_menu.get_dimension()
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode(dimension)
    pygame.display.set_caption(core_service.get_window_title())
    clock = pygame.time.Clock()
    main_menu.initialization()
    pygame.display.set_icon(main_menu.get_icon())
    core_service.setgamewindowcenter(x=dimension[0], y=dimension[1])
    loop = True
    mouse_position = None

    while loop:
        background_color = core_service.get_background_color()
        screen.fill(background_color)
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                loop = False

            if event.type == pygame.MOUSEMOTION:
                mouse_position = pygame.mouse.get_pos()
                main_menu.mouse_move(mouse_position)

            if event.type == pygame.MOUSEBUTTONUP:
                main_menu.click(mouse_position, event.button)

            if event.type == pygame.KEYUP:
                main_menu.keyup(event.key, screen)

        clock.tick(30)
        main_menu.draw(screen)
        main_menu.events(events)
        pygame.display.update()

    pygame.quit()


if __name__ == '__main__':
    root = tkinter.Tk()
    root.overrideredirect(1)
    root.withdraw()
    main()
