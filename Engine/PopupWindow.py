class PopupWindow:
    def __init__(self, background_image, positions, title, list_items):
        self.background_image = background_image
        self.positions = positions
        self.title = title
        self.list_items = list_items
        self.open = False
        self.box_rect = None
        # CHECKS PAGES
        self.current_check_page = 1
        self.check_page_max = 1
        self.check_per_page = 1
        # END CHECKS PAGES
        self.left_arrow = None
        self.left_arrow_base = None
        self.right_arrow = None
        self.right_arrow_base = None

    def update(self):
        pass

    def draw(self, screen):
        pass

    def is_open(self):
        return self.open

    def get_box_rect(self):
        return self.box_rect

    def set_box_rect(self, box_rect):
        self.box_rect = box_rect