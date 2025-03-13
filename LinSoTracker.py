import base64
import gc
import glob
import multiprocessing
import os
import sys
import tempfile
import tkinter
import traceback
import logging
from datetime import datetime

import pygame

from Engine.MainMenu import MainMenu
from Tools.CoreService import CoreService


def setup_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")

    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return log_file


def log_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    log_file = setup_logger()
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error(f"Unhandled Exception:\n{error_msg}")


sys.excepthook = log_exception

core_service = CoreService()


def main():
    try:
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

    except Exception as e:
        setup_logger()
        logging.error("Crashed detected ! Please report on Discord", exc_info=True)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn")
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
