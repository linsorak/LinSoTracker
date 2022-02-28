import pygame
import tkinter as tk
from Engine.MainMenu import MainMenu
from Tools.CoreService import CoreService

def main():
    core_service = CoreService()
    main_menu = MainMenu()
    dimension = main_menu.get_dimension()
    pygame.init()
    screen = pygame.display.set_mode(dimension)
    pygame.display.set_caption(core_service.get_window_title())
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Tahoma", 20)

    main_menu.initialization()
    pygame.display.set_icon(main_menu.get_icon())

    core_service.setgamewindowcenter(x=dimension[0], y=dimension[1])
    loop = True
    mouse_position = None

    while loop:
        screen.fill((0, 0, 0))
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
    root = tk.Tk()
    root.destroy()
    main()