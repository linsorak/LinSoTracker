import base64
import gc
import glob
import os
import tempfile
import tkinter

import pygame

from Engine.MainMenu import MainMenu
from Tools.CoreService import CoreService
import ctypes

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

    try:
        while loop:
            background_color = core_service.get_background_color()
            screen.fill(background_color)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    loop = False
                    break

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

            if not loop:
                del main_menu
                gc.collect()
                core_service.delete_temp_path()

        pygame.quit()
    except SystemExit:
        core_service.delete_temp_path()
        pygame.quit()


if __name__ == '__main__':
    if core_service.detect_os() == "win" and not core_service.dev_version:
        #     # BASE 64 ENCODE OF : ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0) For hide console
        checker = "Y3R5cGVzLndpbmRsbC51c2VyMzIuU2hvd1dpbmRvdyhjdHlwZXMud2luZGxsLmtlcm5lbDMyLkdldENvbnNvbGVXaW5kb3coKSwgMCk="
        exec(base64.b64decode(checker))

    rootdir = tempfile.gettempdir()
    for path in glob.glob(f'{rootdir}/*/'):
        if "LinSoTracker" in path:
            core_service.delete_directory(path)

    root = tkinter.Tk()
    root.overrideredirect(1)
    root.withdraw()
    main()
