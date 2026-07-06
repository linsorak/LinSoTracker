import base64
import json
import os
import platform
import shlex
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib
import webbrowser
from contextlib import contextmanager
from datetime import date
from tkinter import messagebox
from urllib.error import URLError
from urllib.request import urlopen

import pygame

from Tools import ptext


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class CoreService(metaclass=Singleton):
    def __init__(self):
        self.show_hint_on_item = None
        self.temp_dir_delete = None
        self.official_template = None
        self.new_version = None
        self.background_color = (0, 0, 0)
        self.tracker_temp_path = None
        self.app_name = "LinSoTracker"
        self.version = "2.5.0.0"
        self.beta_version = "BETA" in self.version.upper()
        self.beta_lock_enabled = True
        self.beta_end_date = None
        self.key_encryption = "I5WpbQcf6qeid_6pnm54RlQOKftZBL-ZQ8XjJCO6AGc="
        self.temp_path = tempfile.gettempdir()
        self.json_data = None
        self.zoom = 1
        self.zoom_index = 0
        self.sound_active = False
        self.draw_esc_menu_label = True
        self.show_timer = True
        self.go_mode_glow_clockwise = True
        self.current_tracker = None
        self.current_tracker_name = None
        self.app_path = self.resolve_app_path()
        self.menu_font = None
        self.ui_font = None
        self.launch_registered = False
        self.launch_count = 0
        self.show_donation_popup = False

        self.temp_path_fixe = os.path.join(os.path.expanduser('~/Documents'), self.app_name)

        with self.tempdir() as tmpdirname:
            self.temp_path = tmpdirname

        self.create_directory(path=self.temp_path_fixe)

        self.dev_version = os.path.isfile(os.path.join(self.app_path, '.dev'))

        # if not self.dev_version:
        self.read_checker()
        self.print_beta_status()
        self.load_default_configuration()
        self.fps_max = 30
        self.clock = pygame.time.Clock()

    @contextmanager
    def tempdir(self):
        path = tempfile.mkdtemp(suffix="-LinSoTracker")
        try:
            yield path
        finally:
            try:
                ptext.clean()
                shutil.rmtree(path)
                # self.delete_directory(path)
            except IOError:
                sys.stderr.write('Failed to clean up temp dir {}'.format(path))

    def set_current_tracker_name(self, name):
        self.current_tracker_name = name

    def get_current_tracker_name(self):
        return self.current_tracker_name

    def set_current_tracker(self, tracker):
        self.current_tracker = tracker

    def get_current_tracker(self):
        return self.current_tracker

    @staticmethod
    def resolve_app_path():
        # sys.frozen is set by both Nuitka standalone and onefile.
        # sys.executable reliably points to the main binary in both cases,
        # whereas __compiled__.containing_dir returns the module's own subdir
        # (e.g. Contents/MacOS/Tools/) which is wrong for macOS app bundles.
        if getattr(sys, 'frozen', False):
            return os.path.dirname(os.path.abspath(sys.executable))

        if getattr(sys, 'argv', None) and sys.argv[0]:
            argv_path = os.path.abspath(sys.argv[0])
            if os.path.exists(argv_path):
                return os.path.dirname(argv_path)

        return os.path.abspath(os.path.dirname(__file__)).replace("{}{}".format(os.sep, "Tools"), os.sep)

    def save_configuration(self, session, value):
        user_configuration = os.path.join(self.temp_path_fixe, "user.conf")

        data = {}
        if os.path.exists(user_configuration):
            try:
                with open(user_configuration, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print("The file 'user.conf' is corrupted or empty. Resetting the file.")
                data = {}
        data[session] = value
        try:
            with open(user_configuration, 'w') as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            print(f"Failed to write to 'user.conf': {e}")

    def load_cached_beta_configuration(self):
        user_configuration = os.path.join(self.temp_path_fixe, "user.conf")
        if not os.path.exists(user_configuration):
            return
        try:
            with open(user_configuration, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        self.beta_lock_enabled = bool(data.get("betaLockEnabled", self.beta_lock_enabled))
        self.beta_end_date = self.parse_date(data.get("betaEndDate")) or self.beta_end_date

    def save_beta_configuration(self):
        if self.beta_end_date:
            self.save_configuration("betaEndDate", self.beta_end_date.isoformat())
        self.save_configuration("betaLockEnabled", self.beta_lock_enabled)

    @staticmethod
    def parse_date(value):
        if not value:
            return None
        try:
            return date.fromisoformat(str(value).split("T", 1)[0])
        except ValueError:
            return None

    def register_app_launch(self):
        if self.launch_registered:
            return self.show_donation_popup

        user_configuration = os.path.join(self.temp_path_fixe, "user.conf")
        data = {}
        if os.path.exists(user_configuration):
            try:
                with open(user_configuration, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {}

        self.launch_count = data.get("launchCount", 0) + 1
        data["launchCount"] = self.launch_count
        self.show_donation_popup = self.launch_count == 1 or self.launch_count % 10 == 0
        self.launch_registered = True

        try:
            with open(user_configuration, 'w') as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            print(f"Failed to write to 'user.conf': {e}")

        return self.show_donation_popup

    def load_default_configuration(self):
        user_configuration = os.path.join(self.temp_path_fixe, "user.conf")
        if not os.path.exists(user_configuration):
            data = {
                "defaultZoom": 0,
                "soundWhenItemActive": False,
                "showESCLabel": True,
                "showHint": True,
                "showTimer": True,
                "goModeGlowClockwise": True
            }

            with open(user_configuration, 'w') as f:
                json.dump(data, f, indent=2)

            self.zoom_index = data["defaultZoom"]
            self.sound_active = data["soundWhenItemActive"]
            self.draw_esc_menu_label = data["showESCLabel"]
            self.show_hint_on_item = data["showHint"]
            self.show_timer = data["showTimer"]
            self.go_mode_glow_clockwise = data["goModeGlowClockwise"]
        else:
            with open(user_configuration) as f:
                data = json.load(f)

                if "defaultZoom" in data:
                    self.zoom_index = data["defaultZoom"]
                else:
                    self.zoom_index = 0

                if "soundWhenItemActive" in data:
                    self.sound_active = data["soundWhenItemActive"]
                else:
                    self.sound_active = False

                if "showESCLabel" in data:
                    self.draw_esc_menu_label = data["showESCLabel"]
                else:
                    self.draw_esc_menu_label = True

                if "showHint" in data:
                    self.show_hint_on_item = data["showHint"]
                else:
                    self.show_hint_on_item = True

                if "showTimer" in data:
                    self.show_timer = data["showTimer"]
                else:
                    self.show_timer = True

                if "goModeGlowClockwise" in data:
                    self.go_mode_glow_clockwise = data["goModeGlowClockwise"]
                else:
                    self.go_mode_glow_clockwise = True

    def read_checker(self):
        url = "https://linsotracker.com/tracker/update.json"
        self.load_cached_beta_configuration()
        try:
            response = self.safe_urlopen(url, timeout=15)
            data_json = json.loads(response.read())
            self.read_beta_configuration(data_json)

            if "lastest_version" in data_json:
                if self.get_version() != data_json["lastest_version"] \
                        and (self.detect_os() == "win" or self.detect_os() == "linux") \
                        and not self.dev_version \
                        and not self.beta_version:
                    self.new_version = data_json["lastest_version"]

                    args_current_version = f'--current_version="{self.version}"'
                    args_url_json = f'--url_json="{url}"'
                    args_destination_path = f'--destination_path="{self.app_path}"'
                    args_file_to_execute = f'--file_to_execute="{self.app_name}"'

                    path_to_exe = os.path.join(self.app_path, "updater")
                    if self.detect_os() == "win":
                        args_file_to_execute = f'{args_file_to_execute}.exe'
                        path_to_exe = f'{path_to_exe}.exe'

                    arguments = [args_current_version,
                                 args_url_json,
                                 args_destination_path,
                                 args_file_to_execute]

                    if self.detect_os() == "win":
                        cmd = f'start /B "" "{path_to_exe}" {" ".join(arguments)}'
                        subprocess.Popen(cmd, shell=True)
                    else:
                        cmd = f'nohup {path_to_exe} {" ".join(arguments)} > /dev/null 2>&1 &'
                        subprocess.Popen(cmd, shell=True)

                    time.sleep(1)
                    os._exit(0)

            if "official_template" in data_json:
                self.official_template = data_json["official_template"]

        except Exception as exc:
            print(f"Update checker failed: {type(exc).__name__}: {exc}")

    @staticmethod
    def safe_urlopen(url, timeout=15):
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
            return urlopen(url, timeout=timeout, context=context)
        except Exception as https_error:
            if url.startswith("https://"):
                fallback_url = "http://" + url[len("https://"):]
                print(f"HTTPS request failed, retrying without SSL: {type(https_error).__name__}: {https_error}")
                return urlopen(fallback_url, timeout=timeout)
            raise

    def read_beta_configuration(self, data_json):
        beta_data = data_json.get("beta", {})
        if isinstance(beta_data, dict):
            self.beta_lock_enabled = bool(beta_data.get("enabled", self.beta_lock_enabled))
            beta_end_date = (
                beta_data.get("end_date")
                or beta_data.get("endDate")
                or beta_data.get("end")
            )
        else:
            beta_end_date = None

        beta_end_date = beta_end_date or data_json.get("beta_end_date") or data_json.get("betaEndDate")
        parsed_date = self.parse_date(beta_end_date)
        if parsed_date:
            self.beta_end_date = parsed_date
        self.save_beta_configuration()

    def get_new_version(self):
        return self.new_version

    def get_official_template(self):
        return self.official_template

    def get_temp_path(self):
        return self.temp_path

    def set_tracker_temp_path(self, value):
        self.tracker_temp_path = value

    def get_tracker_temp_path(self):
        return self.tracker_temp_path

    def get_app_path(self):
        return self.app_path

    def get_window_title(self):
        return "{} v{}".format(self.app_name, self.version)

    def set_json_data(self, value):
        self.json_data = value

    def get_json_data(self):
        return self.json_data

    def get_font(self, session):
        return self.json_data[2]["Fonts"][session]

    def get_custom_font(self, session):
        return self.json_data[2]["Fonts"]["customFonts"][session]

    def get_version(self):
        return self.version

    def is_beta_version(self):
        return self.beta_version

    def print_beta_status(self):
        if not self.beta_version:
            print("LinSoTracker build mode: release")
            return
        end_date = self.beta_end_date.isoformat() if self.beta_end_date else "unknown"
        print(f"LinSoTracker build mode: beta (lock={'on' if self.beta_lock_enabled else 'off'}, end={end_date})")

    def is_beta_expired(self):
        return (
            self.beta_lock_enabled
            and self.beta_version
            and not self.dev_version
            and self.beta_end_date is not None
            and date.today() >= self.beta_end_date
        )

    def zoom_image(self, image):
        return pygame.transform.smoothscale(image, (image.get_rect().w * self.zoom, image.get_rect().h * self.zoom))

    def get_background_color(self):
        return self.background_color

    def set_background_color(self, r, g, b):
        self.background_color = (r, g, b)

    def get_color_from_font(self, font_datas, session):
        return (
            font_datas["Colors"][session]["r"], font_datas["Colors"][session]["g"], font_datas["Colors"][session]["b"])

    def is_update(self):
        if self.get_new_version():
            return False
        else:
            return True

    def delete_temp_path(self):
        self.delete_directory(self.temp_path)

    def set_menu_font(self, path):
        self.menu_font = path
        self.ui_font = path

    def get_menu_font(self):
        return self.menu_font

    def get_ui_font(self):
        if self.ui_font and os.path.exists(self.ui_font):
            return self.ui_font
        if self.menu_font and os.path.exists(self.menu_font):
            self.ui_font = self.menu_font
            return self.ui_font

        tracker_font = os.path.join(self.temp_path, "tracker", "NotoSans-Bold.ttf")
        if os.path.exists(tracker_font):
            self.ui_font = tracker_font
            return self.ui_font

        self.ui_font = pygame.font.match_font("notosans,segoe ui,arial,dejavusans,liberationsans")
        return self.ui_font

    @staticmethod
    def detect_os():
        if platform.system() == 'Windows':
            return "win"
        elif platform.system() == 'Linux':
            return "linux"
        elif platform.system() == 'Darwin':
            if platform.machine() == 'arm64':
                return "macARM64"
            else:
                return "macIntel"

    @staticmethod
    def setgamewindowcenter(x=500, y=100):
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x, y)

    @staticmethod
    def set_image_transparent(opacity_disable, image):
        transparent_image = image.copy()
        transparent_image.fill((255, 255, 255, 255 * opacity_disable), special_flags=pygame.BLEND_RGBA_MULT)
        return transparent_image

    @staticmethod
    def convert_to_gs(surf):
        # pygame-ce's transform.grayscale() drops the alpha channel, which causes
        # transparent pixels to become opaque gray. Modify RGB directly via surfarray
        # so the alpha channel is never touched.
        try:
            import pygame.surfarray
            import numpy as np
            px = pygame.surfarray.pixels3d(surf)
            gray = ((px[:, :, 0].astype(np.uint16) +
                     px[:, :, 1].astype(np.uint16) +
                     px[:, :, 2].astype(np.uint16)) // 3).astype(np.uint8)
            px[:, :, 0] = gray
            px[:, :, 1] = gray
            px[:, :, 2] = gray
            del px
            return
        except Exception:
            pass
        width, height = surf.get_size()
        for x in range(width):
            for y in range(height):
                red, green, blue, alpha = surf.get_at((x, y))
                average = (red + green + blue) // 3
                surf.set_at((x, y), (average, average, average, alpha))

    @staticmethod
    def create_directory(path):
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def delete_directory(path):
        if os.path.exists(path):
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path, ignore_errors=True)

                    os.rmdir(path)
                except Exception as e:
                    pass

    @staticmethod
    def is_on_element(mouse_positions, element_positons, element_dimension):
        deadzone = 2
        return ((mouse_positions[0] >= element_positons[0] + deadzone) & (
                mouse_positions[0] <= (element_positons[0] + element_dimension[0]) - deadzone) &
                (mouse_positions[1] >= element_positons[1] + deadzone) & (
                        mouse_positions[1] <= (element_positons[1] + element_dimension[1]) - deadzone))

    @staticmethod
    def copytree_skip_locked(src, dst):
        for root, dirs, files in os.walk(src):
            rel_path = os.path.relpath(root, src)
            dest_dir = os.path.join(dst, rel_path)
            os.makedirs(dest_dir, exist_ok=True)

            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_dir, file)
                try:
                    shutil.copy2(src_file, dst_file)
                except (PermissionError, OSError) as e:
                    pass

    @staticmethod
    def launch_app(path):
        if os.path.exists(path):
            os.startfile(path)

    def sync_tracker_data(self):
        """Compare local tracker.data with the remote one and replace it if they
        differ. Returns True if the file was updated."""
        if self.dev_version:
            return False
        url = "http://linsotracker.com/tracker/tracker.data"
        local_path = os.path.join(self.app_path, "tracker.data")
        try:
            response = urlopen(url, timeout=15)
            remote_bytes = response.read()
        except (URLError, Exception):
            return False
        if not remote_bytes:
            return False
        try:
            if os.path.exists(local_path):
                with open(local_path, "rb") as file:
                    if file.read() == remote_bytes:
                        return False
            with open(local_path, "wb") as file:
                file.write(remote_bytes)
            return True
        except Exception:
            return False

    def download_and_replace(self, url, destination_path, destination_filename):
        download_path_location_file = os.path.join(self.temp_path, destination_filename)
        urllib.request.urlretrieve(url, download_path_location_file)
        destination_path_file = os.path.join(destination_path, destination_filename)

        if os.path.exists(destination_path_file):
            os.remove(destination_path_file)

        shutil.copy(download_path_location_file, destination_path_file)
