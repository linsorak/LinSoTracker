import json
from Tools.CoreService import CoreService
from tkinter import filedialog

core_service = CoreService()

class SaveLoadTool:
    def __init__(self):
        self.filetypes = [("LinSoTracker Save", ".trackersave")]

    def openFileNameDialog(self):
        filename = filedialog.askopenfilename(initialdir="/", title="Load tracker save",
                                              filetypes=self.filetypes)
        if filename:
            # if filename.endswith(self.filetypes[0]):
            f = open(filename)
            return json.load(f)
        else:
            return None

    def saveFileDialog(self, data):

        filename = filedialog.asksaveasfilename(initialdir="/", title="Saving tracker informations",
                                                filetypes=self.filetypes)
        if filename:
            with open(filename, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.close()
