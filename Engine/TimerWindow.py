import base64
import multiprocessing
import os
import queue

import pygame


def _timer_window_process(command_queue, state_queue, title, font_path, window_position, icon_path):
    if window_position:
        os.environ["SDL_VIDEO_WINDOW_POS"] = "{},{}".format(window_position[0], window_position[1])

    pygame.init()
    if icon_path and os.path.isfile(icon_path):
        try:
            pygame.display.set_icon(pygame.image.load(icon_path))
        except Exception:
            pass
    screen = pygame.display.set_mode((520, 720), pygame.RESIZABLE)
    pygame.display.set_caption("{} timer".format(title))
    clock = pygame.time.Clock()

    font_title = pygame.font.Font(None, 32)
    if font_path and os.path.isfile(font_path):
        font_timer = pygame.font.Font(font_path, 86)
        font_entry_time = pygame.font.Font(font_path, 26)
    else:
        font_timer = pygame.font.Font(None, 78)
        font_entry_time = pygame.font.Font(None, 26)
    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 20)

    running = False
    elapsed = 0.0
    entries = []
    pending_entries = {}
    scroll = 0
    loop = True
    state_dirty = True
    last_state_push = 0.0
    start_button_rect = pygame.Rect(70, 154, 170, 42)
    reset_button_rect = pygame.Rect(280, 154, 170, 42)
    clear_button_rect = pygame.Rect(0, 0, 1, 1)

    def format_time(seconds):
        total_centiseconds = int(seconds * 100)
        total_seconds = total_centiseconds // 100
        minutes = total_seconds // 60
        secs = total_seconds % 60
        centiseconds = total_centiseconds % 100
        return "{:02d}:{:02d}.{:02d}".format(minutes, secs, centiseconds)

    def read_commands():
        nonlocal loop, elapsed, running, scroll, entries, pending_entries, state_dirty
        while True:
            try:
                command = command_queue.get_nowait()
            except queue.Empty:
                break

            if command["type"] == "close":
                push_state()
                loop = False
            elif command["type"] == "restore":
                state = command.get("state") or {}
                elapsed = float(state.get("elapsed", 0.0))
                running = bool(state.get("running", False))
                scroll = int(state.get("scroll", 0))
                entries = [build_entry_from_payload(entry) for entry in state.get("entries", [])]
                pending_entries = {}
                state_dirty = True
            elif command["type"] == "entry":
                entry = build_entry_from_payload(command, command.get("time", elapsed))
                entries.append(entry)
                if len(entries) > 300:
                    del entries[:-300]
                state_dirty = True
            elif command["type"] == "pending_entry":
                key = command["key"]
                previous = pending_entries.get(key)
                entry_time = previous["entry"]["time"] if previous else elapsed
                entry = build_entry_from_payload(command, entry_time)
                pending_entries[key] = {
                    "due": pygame.time.get_ticks() / 1000.0 + command.get("delay", 0),
                    "entry": entry,
                }
                state_dirty = True

    def build_entry_from_payload(payload, fallback_time=None):
        entry = {
            "action": payload["action"],
            "name": payload["name"],
            "checks": payload.get("checks") or [],
            "time": payload.get("time", fallback_time if fallback_time is not None else elapsed),
            "icon": None,
            "icon_payload": payload.get("icon"),
            "marker": payload.get("marker"),
        }
        icon = entry["icon_payload"]
        if icon:
            try:
                image = pygame.image.fromstring(icon["pixels"], icon["size"], "RGBA")
                entry["icon"] = pygame.transform.smoothscale(image.convert_alpha(), (32, 32))
            except Exception:
                entry["icon"] = None
        return entry

    def serialize_entry(entry):
        return {
            "action": entry["action"],
            "name": entry["name"],
            "checks": entry.get("checks", []),
            "time": entry["time"],
            "icon": entry.get("icon_payload"),
            "marker": entry.get("marker"),
        }

    def push_state():
        try:
            state_queue.put_nowait({
                "elapsed": elapsed,
                "running": running,
                "scroll": scroll,
                "entries": [serialize_entry(entry) for entry in entries],
            })
        except Exception:
            pass

    def draw_button(rect, label, color):
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, (230, 230, 235), rect, 2, border_radius=6)
        text = font.render(label, True, (255, 255, 255))
        screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def draw_small_button(rect, label):
        pygame.draw.rect(screen, (46, 46, 58), rect, border_radius=5)
        pygame.draw.rect(screen, (120, 120, 138), rect, 1, border_radius=5)
        text = font_small.render(label, True, (230, 230, 238))
        screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def render_gradient_text(text, text_font, top_color, bottom_color):
        mask = text_font.render(text, True, (255, 255, 255)).convert_alpha()
        gradient = pygame.Surface(mask.get_size(), pygame.SRCALPHA)
        height = max(1, mask.get_height() - 1)
        for y in range(mask.get_height()):
            ratio = y / height
            color = (
                int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio),
                int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio),
                int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio),
            )
            pygame.draw.line(gradient, color, (0, y), (gradient.get_width(), y))
        gradient.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return gradient

    def render_fixed_width_timer(text):
        digit_width = max(font_timer.size(str(i))[0] for i in range(10))
        separator_width = max(font_timer.size(":")[0], font_timer.size(".")[0])
        height = font_timer.get_height()
        char_widths = [separator_width if char in ":." else digit_width for char in text]
        surface = pygame.Surface((sum(char_widths), height), pygame.SRCALPHA)

        x = 0
        for char, cell_width in zip(text, char_widths):
            char_surface = render_gradient_text(char, font_timer, (175, 255, 175), (55, 170, 75))
            surface.blit(char_surface, (x + (cell_width - char_surface.get_width()) // 2, 0))
            x += cell_width
        return surface

    def render_fixed_width_entry_time(text):
        digit_width = max(font_entry_time.size(str(i))[0] for i in range(10))
        separator_width = max(font_entry_time.size(":")[0], font_entry_time.size(".")[0])
        height = font_entry_time.get_height()
        char_widths = [separator_width if char in ":." else digit_width for char in text]
        surface = pygame.Surface((sum(char_widths), height), pygame.SRCALPHA)

        x = 0
        for char, cell_width in zip(text, char_widths):
            char_surface = font_entry_time.render(char, True, (180, 225, 190))
            surface.blit(char_surface, (x + (cell_width - char_surface.get_width()) // 2, 0))
            x += cell_width
        return surface

    def get_entry_height(entry):
        return 40 + (18 * len(entry.get("checks", [])))

    def get_max_scroll(entries_to_draw, visible_height):
        total_height = sum(get_entry_height(entry) + 8 for entry in entries_to_draw)
        if total_height <= visible_height:
            return 0

        consumed_height = 0
        for index, entry in enumerate(entries_to_draw):
            consumed_height += get_entry_height(entry) + 8
            if total_height - consumed_height <= visible_height:
                return index + 1
        return 0

    def draw_entry(entry, x, y, width):
        row_rect = pygame.Rect(x, y, width, get_entry_height(entry))
        pygame.draw.rect(screen, (28, 28, 36), row_rect, border_radius=4)
        icon_rect = pygame.Rect(x + 6, y + 4, 32, 32)
        if entry.get("marker"):
            marker_color = (95, 235, 130) if entry["marker"] == "green" else (240, 95, 95)
            pygame.draw.circle(screen, marker_color, icon_rect.center, 7)
            pygame.draw.circle(screen, (12, 12, 18), icon_rect.center, 8, 2)
        elif entry["icon"]:
            screen.blit(entry["icon"], icon_rect)

        action_column = pygame.Rect(x + 44, y, 68, 40)
        time_column_width = 88
        time_x = x + width - time_column_width - 10
        name_x = x + 122

        action_text = entry["action"].upper()
        action_color = (135, 230, 160) if action_text in ("GET", "CHECK") or action_text.startswith("+") else (240, 120, 120)
        action = font_small.render(action_text, True, action_color)
        screen.blit(action, (action_column.centerx - action.get_width() // 2,
                             action_column.centery - action.get_height() // 2))

        checks = entry.get("checks", [])
        name = "{} :".format(entry["name"]) if checks else entry["name"]
        max_name_width = max(40, time_x - name_x - 12)
        while name and font_small.size(name)[0] > max_name_width:
            name = name[:-2] + "."
        name_surface = font_small.render(name, True, (235, 235, 235))
        screen.blit(name_surface, (name_x, y + 20 - name_surface.get_height() // 2))

        check_y = y + 38
        for check_name in checks:
            visible_check_name = "- {}".format(check_name)
            max_check_width = max(40, time_x - (name_x + 14) - 12)
            while visible_check_name and font_small.size(visible_check_name)[0] > max_check_width:
                visible_check_name = visible_check_name[:-2] + "."
            check_surface = font_small.render(visible_check_name, True, (190, 195, 210))
            screen.blit(check_surface, (name_x + 14, check_y))
            check_y += 18

        time_surface = render_fixed_width_entry_time(format_time(entry["time"]))
        screen.blit(time_surface, (x + width - time_surface.get_width() - 10,
                                   y + 20 - time_surface.get_height() // 2))

    while loop:
        dt = clock.tick(60) / 1000.0
        read_commands()
        if running:
            elapsed += dt
            state_dirty = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                loop = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if start_button_rect.collidepoint(event.pos):
                    running = not running
                    state_dirty = True
                elif reset_button_rect.collidepoint(event.pos):
                    elapsed = 0.0
                    running = False
                    state_dirty = True
                elif clear_button_rect.collidepoint(event.pos):
                    entries.clear()
                    scroll = 0
                    state_dirty = True
            elif event.type == pygame.MOUSEWHEEL:
                scroll = max(0, scroll - event.y)
                state_dirty = True

        now = pygame.time.get_ticks() / 1000.0
        ready_pending_keys = [key for key, pending in pending_entries.items() if pending["due"] <= now]
        for key in ready_pending_keys:
            entries.append(pending_entries.pop(key)["entry"])
            if len(entries) > 300:
                del entries[:-300]
            state_dirty = True

        width, height = screen.get_size()
        screen.fill((18, 18, 24))

        title_surface = font_title.render("Session timer", True, (235, 235, 245))
        screen.blit(title_surface, ((width - title_surface.get_width()) // 2, 22))

        timer_box = pygame.Rect(0, 58, width, 86)
        timer_text = render_fixed_width_timer(format_time(elapsed))
        screen.blit(timer_text, (timer_box.centerx - timer_text.get_width() // 2,
                                 timer_box.centery - timer_text.get_height() // 2))

        start_button_rect = pygame.Rect(width // 2 - 190, 166, 170, 42)
        reset_button_rect = pygame.Rect(width // 2 + 20, 166, 170, 42)
        draw_button(start_button_rect, "Pause timer" if running else "Start timer",
                    (165, 100, 35) if running else (35, 130, 85))
        draw_button(reset_button_rect, "Reset timer", (110, 65, 135))

        list_top = 272
        pygame.draw.line(screen, (70, 70, 80), (24, list_top - 16), (width - 24, list_top - 16), 1)
        header = font.render("Items log", True, (220, 220, 230))
        screen.blit(header, (24, list_top - 42))
        clear_button_rect = pygame.Rect(width - 94, list_top - 47, 70, 24)
        draw_small_button(clear_button_rect, "Clear")

        y = list_top
        visible_entries = sorted(entries, key=lambda entry: entry["time"], reverse=True)
        scroll = min(scroll, get_max_scroll(visible_entries, height - list_top - 8))
        for entry in visible_entries[scroll:]:
            if y > height - 44:
                break
            draw_entry(entry, 24, y, width - 48)
            y += get_entry_height(entry) + 8

        pygame.display.flip()

        now_for_state = pygame.time.get_ticks() / 1000.0
        if state_dirty or now_for_state - last_state_push > 0.5:
            push_state()
            last_state_push = now_for_state
            state_dirty = False

    push_state()
    pygame.quit()


class TimerWindow:
    DEBOUNCE_SECONDS = 3.0

    def __init__(self, title, resources_path=None, visible=True):
        self.title = title
        self.closed = True
        self.command_queue = None
        self.state_queue = None
        self.process = None
        self.resources_path = resources_path
        self.state = {
            "elapsed": 0.0,
            "running": False,
            "scroll": 0,
            "entries": [],
            "visible": bool(visible),
        }
        if visible:
            self.show()

    def show(self):
        if self.is_visible():
            return
        try:
            ctx = multiprocessing.get_context("spawn")
            self.command_queue = ctx.Queue()
            self.state_queue = ctx.Queue()
            self.process = ctx.Process(target=_timer_window_process,
                                       args=(self.command_queue, self.state_queue, self.title, self.find_timer_font(),
                                             self.get_initial_window_position(), self.find_window_icon()),
                                       daemon=True)
            self.process.start()
            self.closed = False
            self.restore_state()
        except Exception:
            self.closed = True

    def find_timer_font(self):
        candidates = [
            os.path.join(self.resources_path, "DS-DIGI.TTF") if self.resources_path else None,
            os.path.join(os.getcwd(), "DS-DIGI.TTF"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def find_window_icon(self):
        candidates = [
            os.path.join(self.resources_path, "icon.png") if self.resources_path else None,
            os.path.join(os.getcwd(), "icon.png"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    @staticmethod
    def get_initial_window_position():
        try:
            from pygame._sdl2.video import Window
            main_window = Window.from_display_module()
            main_x, main_y = main_window.position
            main_surface = pygame.display.get_surface()
            main_width = main_surface.get_width() if main_surface else 0
            return int(main_x + main_width + 8), int(main_y)
        except Exception:
            return None

    def close(self):
        if self.closed:
            return
        self.drain_state_updates()
        self.closed = True
        self.state["visible"] = False
        try:
            self.command_queue.put_nowait({"type": "close"})
        except Exception:
            pass

    def set_visible(self, visible):
        if visible:
            self.show()
        else:
            self.close()

    def is_visible(self):
        self.drain_state_updates()
        if self.closed:
            return False
        if self.process and self.process.is_alive():
            return True
        if self.process:
            self.closed = True
            self.state["visible"] = False
        return False

    def handle_event(self, event):
        return False

    def consume_click(self):
        return False

    def should_consume_untagged_mouse_event(self, event):
        return False

    def update(self, dt):
        if not self.is_visible():
            return
        self.drain_state_updates()

    def draw(self):
        pass

    def record_item_changes(self, before_states, items, check_names_by_item=None):
        if not self.is_visible():
            return

        if check_names_by_item is None:
            check_names_by_item = {}

        for item in items:
            if not self.is_loggable_item(item):
                continue

            before = before_states.get(id(item))
            if before is None:
                continue

            before_sig = before.get("timer_state")
            if before_sig is None:
                continue
            after_sig = self.item_signature(item)
            if before_sig == after_sig:
                continue

            if self.is_count_item(item):
                action = self.get_count_action(before_sig, after_sig)
            elif item.__class__.__name__ == "CheckItem":
                action = self.get_check_item_action(before_sig, after_sig)
            else:
                action = self.get_action(before_sig, after_sig)
            if action is None:
                continue

            display_name = self.get_display_name(item, after_sig, before_sig)
            associated_checks = self.get_associated_checks(before_sig, after_sig, check_names_by_item)
            entry = {
                "action": action,
                "name": display_name,
                "checks": associated_checks,
                "icon": self.get_item_icon_payload(item),
            }
            if self.is_delayed_item(item):
                self.send_pending_entry(id(item), entry, self.DEBOUNCE_SECONDS)
            else:
                self.send_entry(entry)

    def record_check_changes(self, before_states, checks):
        if not self.is_visible():
            return

        for check in checks:
            if not self.is_loggable_check(check):
                continue

            before_sig = before_states.get(id(check))
            if before_sig is None:
                continue

            after_sig = self.check_signature(check)
            if before_sig == after_sig or before_sig[1] == after_sig[1]:
                continue

            self.send_entry({
                "action": "Get" if after_sig[1] else "Remove",
                "name": self.get_check_display_name(after_sig),
                "icon": None,
                "marker": "green" if after_sig[1] else "red",
            })

    @staticmethod
    def is_loggable_item(item):
        ignored = {"SubMenuItem", "EditableBox", "ImageItem", "OpenLinkItem", "TimerItem"}
        return (
            item.__class__.__name__ not in ignored
            and not getattr(item, "ignore_timer_log", False)
            and getattr(item, "show_item", True)
        )

    @staticmethod
    def is_loggable_check(check):
        return not getattr(check, "hide", False)

    @staticmethod
    def is_delayed_item(item):
        return any(hasattr(item, attr) for attr in ("next_item_index", "increments_position", "label_count"))

    @staticmethod
    def is_count_item(item):
        return item.__class__.__name__ in ("CountItem", "AlternateCountItem")

    @staticmethod
    def item_signature(item):
        return (
            item.name,
            item.base_name,
            getattr(item, "enable", None),
            getattr(item, "check", None),
            getattr(item, "value", None),
            getattr(item, "increments_position", None),
            getattr(item, "next_item_index", None),
            getattr(item, "label_count", None),
            TimerWindow.get_label_item_value(item),
        )

    @staticmethod
    def check_signature(check):
        entries = getattr(check, "dragged_items", [])
        names = tuple(entry.get("name") for entry in entries if entry.get("name"))
        base_names = tuple(
            entry.get("base_name") for entry in entries if entry.get("base_name"))
        if not names and getattr(check, "dragged_item_name", None):
            names = (check.dragged_item_name,)
            base_names = (getattr(check, "dragged_item_basename", None),)
        return (
            check.name,
            bool(getattr(check, "checked", False)),
            names,
            base_names,
        )

    @staticmethod
    def get_action(before_sig, after_sig):
        before_enabled = bool(before_sig[2])
        after_enabled = bool(after_sig[2])
        before_checked = bool(before_sig[3])
        after_checked = bool(after_sig[3])

        if after_checked != before_checked:
            return "Get" if after_checked else "Remove"
        if after_enabled != before_enabled:
            return "Get" if after_enabled else "Remove"
        return "Get" if after_enabled else None

    @staticmethod
    def get_check_item_action(before_sig, after_sig):
        before_enabled = bool(before_sig[2])
        after_enabled = bool(after_sig[2])
        before_checked = bool(before_sig[3])
        after_checked = bool(after_sig[3])

        if after_enabled != before_enabled:
            return "Get" if after_enabled else "Remove"
        if after_checked != before_checked:
            return "Check" if after_checked else "Uncheck"
        return "Get" if after_enabled else None

    @staticmethod
    def get_count_action(before_sig, after_sig):
        before_value = before_sig[4]
        after_value = after_sig[4]
        if before_value is None or after_value is None or before_value == after_value:
            return None

        delta = after_value - before_value
        if delta > 0:
            return "+{}".format(delta)
        return str(delta)

    @staticmethod
    def get_display_name(item, after_sig, before_sig):
        if item.__class__.__name__ == "LabelItem":
            label = after_sig[8] if after_sig[8] is not None else before_sig[8]
            base_name = after_sig[0] or before_sig[0] or item.base_name
            if label:
                return "{} : {}".format(base_name, label)
        if after_sig[0]:
            return after_sig[0]
        if before_sig[0]:
            return before_sig[0]
        return item.base_name

    @staticmethod
    def get_label_item_value(item):
        if item.__class__.__name__ != "LabelItem":
            return None
        label_list = getattr(item, "label_list", None)
        label_count = getattr(item, "label_count", None)
        if label_list is None or label_count is None:
            return None
        try:
            return label_list[label_count]
        except (IndexError, TypeError):
            return None

    @staticmethod
    def get_associated_checks(before_sig, after_sig, check_names_by_item):
        candidate_item_names = (after_sig[0], after_sig[1], before_sig[0], before_sig[1])
        associated_checks = []
        seen = set()
        for item_name in candidate_item_names:
            for check_name in check_names_by_item.get(item_name, []):
                if check_name not in seen:
                    seen.add(check_name)
                    associated_checks.append(check_name)
        return associated_checks

    @staticmethod
    def get_check_display_name(check_sig):
        check_name = check_sig[0]
        attached_item_names = check_sig[2]
        if attached_item_names:
            if isinstance(attached_item_names, str):
                attached_item_names = (attached_item_names,)
            return "{} : {}".format(", ".join(attached_item_names), check_name)
        return check_name

    @staticmethod
    def get_item_icon_payload(item):
        image = TimerWindow.get_current_plain_item_image(item)
        if not isinstance(image, pygame.Surface) or image.get_width() == 0 or image.get_height() == 0:
            image = getattr(item, "image", None)
        if not isinstance(image, pygame.Surface):
            return None
        try:
            icon = pygame.transform.smoothscale(image.convert_alpha(), (32, 32))
            return {
                "pixels": pygame.image.tostring(icon, "RGBA"),
                "size": icon.get_size(),
            }
        except Exception:
            return None

    @staticmethod
    def get_current_plain_item_image(item):
        if getattr(item, "dragged_item_name", None):
            try:
                tracker = item.core_service.get_current_tracker()
                attached_item = tracker.find_item(
                    item.dragged_item_name,
                    item.dragged_item_name == item.dragged_item_basename
                )
                if attached_item:
                    attached_index = getattr(item, "dragged_item_index", None)
                    return TimerWindow.get_current_plain_item_image_for_index(attached_item, attached_index)
            except Exception:
                pass

        return TimerWindow.get_current_plain_item_image_for_index(
            item,
            getattr(item, "next_item_index", None)
        )

    @staticmethod
    def get_current_plain_item_image_for_index(item, index):
        if hasattr(item, "get_timer_icon_image"):
            image = item.get_timer_icon_image()
            if isinstance(image, pygame.Surface):
                return image
        next_items = getattr(item, "next_items", None)
        if next_items and index is not None and index >= 0:
            try:
                return next_items[index]["Image"]
            except (IndexError, KeyError, TypeError):
                pass
        return getattr(item, "colored_image", None)

    @staticmethod
    def get_check_icon_payload(check):
        image = getattr(check, "dragged_icon_item_image", None)
        if not isinstance(image, pygame.Surface):
            return None
        try:
            icon = pygame.transform.smoothscale(image.convert_alpha(), (32, 32))
            return {
                "pixels": pygame.image.tostring(icon, "RGBA"),
                "size": icon.get_size(),
            }
        except Exception:
            return None

    def send_entry(self, entry):
        try:
            self.command_queue.put_nowait({
                "type": "entry",
                "action": entry["action"],
                "name": entry["name"],
                "checks": entry.get("checks", []),
                "icon": entry["icon"],
                "marker": entry.get("marker"),
            })
        except Exception:
            self.closed = True

    def send_pending_entry(self, key, entry, delay):
        try:
            self.command_queue.put_nowait({
                "type": "pending_entry",
                "key": key,
                "delay": delay,
                "action": entry["action"],
                "name": entry["name"],
                "checks": entry.get("checks", []),
                "icon": entry["icon"],
                "marker": entry.get("marker"),
            })
        except Exception:
            self.closed = True

    def drain_state_updates(self):
        if not self.state_queue:
            return
        while True:
            try:
                state = self.state_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break
            state["visible"] = not self.closed
            self.state.update(state)

    def get_data(self):
        self.drain_state_updates()
        data = dict(self.state)
        data["visible"] = self.is_visible()
        data["entries"] = [self.encode_entry_for_save(entry) for entry in data.get("entries", [])]
        return data

    def set_data(self, data):
        if not isinstance(data, dict):
            return
        self.drain_state_updates()
        self.state.update({
            "elapsed": float(data.get("elapsed", 0.0)),
            "running": False,
            "scroll": int(data.get("scroll", 0)),
            "entries": [self.decode_entry_from_save(entry) for entry in data.get("entries", [])],
            "visible": bool(data.get("visible", True)),
        })
        if self.state["visible"]:
            if not self.process_is_alive():
                self.show()
            self.restore_state()
        else:
            self.close()
            self.state["visible"] = False

    def restore_state(self):
        if not self.command_queue or self.closed:
            return
        try:
            self.command_queue.put_nowait({
                "type": "restore",
                "state": {
                    "elapsed": self.state.get("elapsed", 0.0),
                    "running": self.state.get("running", False),
                    "scroll": self.state.get("scroll", 0),
                    "entries": self.state.get("entries", []),
                }
            })
        except Exception:
            self.closed = True

    def process_is_alive(self):
        return bool(self.process and self.process.is_alive() and not self.closed)

    @staticmethod
    def encode_entry_for_save(entry):
        saved_entry = dict(entry)
        icon = saved_entry.get("icon")
        if icon and isinstance(icon.get("pixels"), bytes):
            saved_entry["icon"] = {
                "pixels": base64.b64encode(icon["pixels"]).decode("ascii"),
                "size": icon.get("size"),
                "encoding": "base64",
            }
        return saved_entry

    @staticmethod
    def decode_entry_from_save(entry):
        loaded_entry = dict(entry)
        icon = loaded_entry.get("icon")
        if icon and icon.get("encoding") == "base64" and isinstance(icon.get("pixels"), str):
            loaded_entry["icon"] = {
                "pixels": base64.b64decode(icon["pixels"].encode("ascii")),
                "size": tuple(icon.get("size", (32, 32))),
            }
        return loaded_entry
