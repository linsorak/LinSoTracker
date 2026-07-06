import base64
import ctypes
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
from tkinter import messagebox

import pygame

from Engine.MainMenu import MainMenu
from Tools.CoreService import CoreService


PRINT_SCREEN_KEYS = {k for k in (
    getattr(pygame, "K_PRINTSCREEN", None),
    getattr(pygame, "K_PRINT", None),
    getattr(pygame, "K_SYSREQ", None),
) if k is not None}

def show_beta_expired_message():
    messagebox.showerror(
        "LinSoTracker beta ended",
        "This LinSoTracker beta build has expired and can no longer be launched.\n\n"
        "Please download an updated release to continue using LinSoTracker."
    )


def save_screenshot(surface, base_dir):
    try:
        folder = os.path.join(base_dir, "Screenshots")
        os.makedirs(folder, exist_ok=True)
        name = "screenshot-{}.png".format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        pygame.image.save(surface, os.path.join(folder, name))
    except Exception:
        pass


def setup_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"LinSoTracker_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")

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
        if core_service.is_beta_expired():
            show_beta_expired_message()
            return

        os.environ["SDL_MOUSE_FOCUS_CLICKTHROUGH"] = "1"
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
        pygame.init()
        pygame.mixer.init()
        try:
            pygame.joystick.quit()
        except Exception:
            pass
        joystick_event_names = (
            "JOYAXISMOTION", "JOYBALLMOTION", "JOYHATMOTION",
            "JOYBUTTONDOWN", "JOYBUTTONUP",
            "JOYDEVICEADDED", "JOYDEVICEREMOVED",
            "CONTROLLERAXISMOTION", "CONTROLLERBUTTONDOWN", "CONTROLLERBUTTONUP",
            "CONTROLLERDEVICEADDED", "CONTROLLERDEVICEREMOVED", "CONTROLLERDEVICEREMAPPED",
            "CONTROLLERTOUCHPADDOWN", "CONTROLLERTOUCHPADMOTION", "CONTROLLERTOUCHPADUP",
            "CONTROLLERSENSORUPDATE",
        )
        for name in joystick_event_names:
            ev = getattr(pygame, name, None)
            if ev is not None:
                try:
                    pygame.event.set_blocked(ev)
                except Exception:
                    pass
        main_menu = MainMenu()
        dimension = main_menu.get_dimension()
        screen = pygame.display.set_mode(dimension)
        pygame.key.set_repeat(350, 35)
        pygame.display.set_caption(core_service.get_window_title())
        main_menu.initialization()
        pygame.display.set_icon(main_menu.get_icon())
        core_service.setgamewindowcenter(*dimension)
        clock = core_service.clock
        loop = True
        mouse_position = (0, 0)
        CLICK_THRESHOLD = 150
        TEMPLATE_MAKER_CLICK_THRESHOLD = 35
        is_mouse_down = False
        start_time = 0
        button_event = None
        resize_pending = None
        resize_pending_time = 0
        RESIZE_DEBOUNCE_MS = 250
        screenshot_pending = False

        while loop:
            background_color = core_service.get_background_color()
            screen.fill(background_color)
            events = pygame.event.get()
            time_delta = clock.tick(core_service.fps_max) / 1000.0

            for event in events:
                if event.type in (pygame.KEYUP, pygame.KEYDOWN) and event.key in PRINT_SCREEN_KEYS:
                    screenshot_pending = True
                    continue
                if main_menu.events(event, time_delta):
                    continue
                if event.type == pygame.QUIT:
                    loop = False
                    break
                elif event.type == pygame.MOUSEMOTION:
                    mouse_position = pygame.mouse.get_pos()
                    main_menu.mouse_move(mouse_position)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_position = event.pos
                    if event.button == 1:
                        is_mouse_down = True
                        start_time = pygame.time.get_ticks()
                        button_event = event.button
                elif event.type == pygame.MOUSEBUTTONUP:
                    mouse_position = event.pos
                    if event.button == 1:
                        is_mouse_down = False
                        main_menu.click(mouse_position, event.button)
                    else:
                        main_menu.click(mouse_position, event.button)
                elif event.type == pygame.KEYUP:
                    main_menu.keyup(event.key, screen)
                elif event.type == pygame.VIDEORESIZE:
                    if getattr(main_menu, "template_maker", None) is not None:
                        screen = pygame.display.set_mode((max(1280, event.w), max(720, event.h)), pygame.RESIZABLE)
                    tracker = getattr(main_menu, "loaded_tracker", None)
                    if tracker is not None and getattr(tracker, "tracker_json_data", None):
                        dims = tracker.tracker_json_data[1]["Datas"]["Dimensions"]
                        base_w = dims["width"]
                        base_h = dims["height"]
                        new_w = max(1, event.w)
                        new_h = int(new_w * base_h / base_w)
                        new_zoom = new_w / base_w
                        new_zoom = max(0.5, min(3.0, new_zoom))
                        screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
                        resize_pending = new_zoom
                        resize_pending_time = pygame.time.get_ticks()

            if resize_pending is not None and pygame.time.get_ticks() - resize_pending_time > RESIZE_DEBOUNCE_MS:
                tracker = getattr(main_menu, "loaded_tracker", None)
                if tracker is not None:
                    tracker.change_zoom(value=resize_pending)
                    surf = pygame.display.get_surface()
                    if surf is not None:
                        screen = surf
                resize_pending = None

            if is_mouse_down and button_event == 1:
                current_time = pygame.time.get_ticks()
                click_threshold = (
                    TEMPLATE_MAKER_CLICK_THRESHOLD
                    if getattr(main_menu, "template_maker", None) is not None
                    else CLICK_THRESHOLD
                )
                if current_time - start_time >= click_threshold:
                    main_menu.click_down(mouse_position, button_event)
                    is_mouse_down = False
                    start_time = 0

            main_menu.draw(screen, time_delta)
            pygame.display.update()

            if screenshot_pending:
                save_screenshot(pygame.display.get_surface() or screen, core_service.temp_path_fixe)
                screenshot_pending = False

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
    root.withdraw()
    main()
