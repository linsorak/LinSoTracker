from Tools.CoreService import CoreService


class Tracker:
    def __init__(self, template_name):
        self.template_name = template_name
        self.core_service = CoreService()
        print("PATH =", self.core_service.get_temp_path())

    def extract_data(self):
        pass