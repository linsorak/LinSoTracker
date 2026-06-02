import os

import pygame

from Entities.Item import Item


class TimerItem(Item):
    def __init__(self, id, name, position, image, opacity_disable, hint, timer_config, buttons_config,
                 group=None, group_controls=None, tracker=None, enable=True, always_enable=False):
        self.timer_config = timer_config or {}
        self.buttons_config = buttons_config or {}
        self.group = group
        self.group_controls = group_controls or {}
        self.tracker = tracker
        self.elapsed = float(self.timer_config.get("StartValue", 0))
        self.running = bool(self.timer_config.get("AutoStart", False))
        self.last_tick = pygame.time.get_ticks() / 1000.0
        self.clicked_control = None
        self.zoom = tracker.core_service.zoom if tracker else 1
        Item.__init__(self, id=id, name=name, image=image, position=position, enable=enable,
                      opacity_disable=opacity_disable, hint=hint, always_enable=always_enable)
        self.can_drag = False
        self.update()

    def update(self):
        now = pygame.time.get_ticks() / 1000.0
        if self.running:
            self.elapsed += now - self.last_tick
        self.last_tick = now
        self.render()

    def render(self):
        bounds = self.get_bounds()
        self.image = pygame.Surface((max(1, bounds.width), max(1, bounds.height)), pygame.SRCALPHA).convert_alpha()
        offset = (-bounds.x, -bounds.y)
        self.rect = pygame.Rect(self.position[0] + bounds.x, self.position[1] + bounds.y, bounds.width, bounds.height)
        self.base_rect = self.rect

        timer_rect = self.relative_rect(self.timer_config.get("Rect", {"x": 0, "y": 0, "w": 180, "h": 42}))
        timer_rect.move_ip(offset)
        self.draw_background(timer_rect, self.timer_config.get("Background", {}))
        self.draw_timer_text(timer_rect)

        self.draw_config_button("StartPause", self.running)
        self.draw_config_button("Reset", False)
        if self.buttons_config.get("GroupToggle", {}).get("Enable", False):
            self.draw_config_button("GroupToggle", self.is_group_running())
        if self.buttons_config.get("GroupReset", {}).get("Enable", False):
            self.draw_config_button("GroupReset", False)

    def draw_timer_text(self, rect):
        font_cfg = self.timer_config.get("Font", {})
        font = self.load_font(font_cfg, 32)
        text = self.format_time()
        color = self.color(font_cfg.get("Color"), (150, 255, 160))
        if font_cfg.get("FixedWidthDigits", True):
            surface = self.render_fixed_width(text, font, color)
        else:
            surface = font.render(text, True, color)
        self.image.blit(surface, (rect.centerx - surface.get_width() // 2,
                                  rect.centery - surface.get_height() // 2))

    def draw_config_button(self, key, active):
        cfg = self.buttons_config.get(key, {})
        if not cfg or cfg.get("Enable") is False:
            return
        rect = self.relative_rect(cfg.get("Rect", {"x": 0, "y": 0, "w": 80, "h": 28}))
        bounds = self.get_bounds()
        rect.move_ip(-bounds.x, -bounds.y)

        labels = cfg.get("Labels", {})
        if key in ("StartPause", "GroupToggle"):
            label = labels.get("Pause" if active else "Start", "Pause" if active else "Start")
            colors = cfg.get("Colors", {})
            fill = self.color(colors.get("Pause" if active else "Start"), (165, 100, 35) if active else (35, 130, 85))
            border = self.color(colors.get("Border"), (235, 235, 235))
        else:
            label = cfg.get("Label", "Reset")
            fill = self.color(cfg.get("Color"), (110, 65, 135))
            border = self.color(cfg.get("BorderColor"), (235, 235, 235))

        pygame.draw.rect(self.image, fill, rect, border_radius=int(cfg.get("Radius", 6) * self.zoom))
        border_size = int(cfg.get("BorderSize", 2) * self.zoom)
        if border_size > 0:
            pygame.draw.rect(self.image, border, rect, border_size, border_radius=int(cfg.get("Radius", 6) * self.zoom))

        font = self.load_font(cfg.get("Font", {}), 16)
        text = font.render(label, True, self.color(cfg.get("Font", {}).get("Color"), (255, 255, 255)))
        self.image.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def draw_background(self, rect, cfg):
        fill = self.color(cfg.get("Color"), None)
        if fill:
            pygame.draw.rect(self.image, fill, rect, border_radius=int(cfg.get("Radius", 0) * self.zoom))
        border_size = int(cfg.get("BorderSize", 0) * self.zoom)
        border = self.color(cfg.get("BorderColor"), None)
        if border and border_size > 0:
            pygame.draw.rect(self.image, border, rect, border_size, border_radius=int(cfg.get("Radius", 0) * self.zoom))

    def format_time(self):
        total_centiseconds = int(self.elapsed * 100)
        total_seconds = total_centiseconds // 100
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        centiseconds = total_centiseconds % 100
        if self.timer_config.get("ShowCentiseconds", True):
            return "{:02d}:{:02d}.{:02d}".format(minutes, seconds, centiseconds)
        return "{:02d}:{:02d}".format(minutes, seconds)

    @staticmethod
    def render_fixed_width(text, font, color):
        digit_width = max(font.size(str(i))[0] for i in range(10))
        separator_width = max(font.size(":")[0], font.size(".")[0])
        height = font.get_height()
        widths = [separator_width if char in ":." else digit_width for char in text]
        surface = pygame.Surface((sum(widths), height), pygame.SRCALPHA)
        x = 0
        for char, width in zip(text, widths):
            char_surface = font.render(char, True, color)
            surface.blit(char_surface, (x + (width - char_surface.get_width()) // 2, 0))
            x += width
        return surface

    def check_click(self, pos):
        self.clicked_control = None
        local_pos = (pos[0] - self.position[0], pos[1] - self.position[1])
        for key in ("StartPause", "Reset", "GroupToggle", "GroupReset"):
            cfg = self.buttons_config.get(key, {})
            if cfg and cfg.get("Enable") is not False and self.relative_rect(cfg.get("Rect", {})).collidepoint(local_pos):
                self.clicked_control = key
                return True
        return False

    def left_click(self):
        control = self.clicked_control
        self.clicked_control = None
        if control == "StartPause":
            self.toggle()
        elif control == "Reset":
            self.reset_timer()
        elif control == "GroupToggle":
            self.set_group_running(not self.is_group_running())
        elif control == "GroupReset":
            self.reset_group()
        self.update()

    def right_click(self):
        self.left_click()

    def wheel_click(self):
        pass

    def toggle(self):
        self.set_running(not self.running)

    def set_running(self, running):
        self.update_elapsed()
        self.running = running
        self.last_tick = pygame.time.get_ticks() / 1000.0

    def reset_timer(self):
        self.elapsed = float(self.timer_config.get("StartValue", 0))
        self.running = False
        self.last_tick = pygame.time.get_ticks() / 1000.0

    def update_elapsed(self):
        if self.running:
            now = pygame.time.get_ticks() / 1000.0
            self.elapsed += now - self.last_tick
            self.last_tick = now

    def iter_group_timers(self):
        if not self.tracker or not self.group:
            return []
        return [
            item for item in self.tracker.items
            if isinstance(item, TimerItem) and item.group == self.group
        ]

    def is_group_running(self):
        timers = self.iter_group_timers()
        return bool(timers) and any(timer.running for timer in timers)

    def set_group_running(self, running):
        for timer in self.iter_group_timers():
            timer.set_running(running)
            timer.update()

    def reset_group(self):
        for timer in self.iter_group_timers():
            timer.reset_timer()
            timer.update()

    def get_bounds(self):
        rects = [self.relative_rect(self.timer_config.get("Rect", {"x": 0, "y": 0, "w": 180, "h": 42}))]
        for key, cfg in self.buttons_config.items():
            if cfg and cfg.get("Enable") is not False and "Rect" in cfg:
                rects.append(self.relative_rect(cfg["Rect"]))
        bounds = rects[0].copy()
        for rect in rects[1:]:
            bounds.union_ip(rect)
        return bounds

    def relative_rect(self, data):
        return pygame.Rect(
            int(data.get("x", 0) * self.zoom),
            int(data.get("y", 0) * self.zoom),
            int(data.get("w", 1) * self.zoom),
            int(data.get("h", 1) * self.zoom)
        )

    def load_font(self, cfg, fallback_size):
        size = int(cfg.get("Size", fallback_size) * self.zoom)
        font_name = cfg.get("Name")
        if font_name and self.tracker:
            font_path = os.path.join(self.tracker.resources_path, font_name)
            if os.path.isfile(font_path):
                return pygame.font.Font(font_path, size)
        return pygame.font.Font(None, size)

    @staticmethod
    def color(data, fallback):
        if data is None:
            return fallback
        if "a" in data:
            return data["r"], data["g"], data["b"], data["a"]
        return data["r"], data["g"], data["b"]

    def get_data(self):
        data = Item.get_data(self)
        self.update_elapsed()
        data["elapsed"] = self.elapsed
        data["running"] = self.running
        return data

    def set_data(self, datas):
        Item.set_data(self, datas)
        self.elapsed = float(datas.get("elapsed", self.timer_config.get("StartValue", 0)))
        self.running = bool(datas.get("running", False))
        self.last_tick = pygame.time.get_ticks() / 1000.0
        self.update()

    def reinitialize(self):
        self.reset_timer()
        Item.reinitialize(self)
