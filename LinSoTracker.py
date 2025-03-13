import base64
import gc
import glob
import os
import tempfile
import tkinter

import pygame

from Engine.MainMenu import MainMenu
from Tools.CoreService import CoreService

core_service = CoreService()

def main():
    os.environ["SDL_MOUSE_FOCUS_CLICKTHROUGH"] = "1"
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
    pygame.init()
    pygame.mixer.init()
    main_menu = MainMenu()
    dimension = main_menu.get_dimension()
    screen = pygame.display.set_mode(dimension)
    pygame.display.set_caption(core_service.get_window_title())
    main_menu.initialization()
    pygame.display.set_icon(main_menu.get_icon())
    core_service.setgamewindowcenter(*dimension)
    clock = core_service.clock
    loop = True
    mouse_position = (0, 0)
    CLICK_THRESHOLD = 100
    is_mouse_down = False
    start_time = 0
    button_event = None

    while loop:
        background_color = core_service.get_background_color()
        screen.fill(background_color)
        events = pygame.event.get()
        time_delta = clock.tick(core_service.fps_max) / 1000.0

        for event in events:
            main_menu.events(event, time_delta)
            if event.type == pygame.QUIT:
                loop = False
                break
            elif event.type == pygame.MOUSEMOTION:
                mouse_position = pygame.mouse.get_pos()
                main_menu.mouse_move(mouse_position)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    is_mouse_down = True
                    start_time = pygame.time.get_ticks()
                    button_event = event.button
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    is_mouse_down = False
                    main_menu.click(mouse_position, event.button)
                else:
                    main_menu.click(mouse_position, event.button)
            elif event.type == pygame.KEYUP:
                main_menu.keyup(event.key, screen)

        if is_mouse_down and button_event == 1:
            current_time = pygame.time.get_ticks()
            if current_time - start_time >= CLICK_THRESHOLD:
                main_menu.click_down(mouse_position, button_event)
                is_mouse_down = False
                start_time = 0

        main_menu.draw(screen, time_delta)
        pygame.display.update()

    del main_menu
    gc.collect()
    core_service.delete_temp_path()
    pygame.quit()

if __name__ == '__main__':
    if core_service.detect_os() == "win" and not core_service.dev_version:
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
