import json

import easygui

from Tools.CoreService import CoreService

core_service = CoreService()


class SaveLoadTool:
    def __init__(self):
        self.filetypes = [["*.trackersave", "LinSoTracker Save"]]

    def openFileNameDialog(self):
        filename = easygui.fileopenbox(msg='Load tracker save',
                                       title='Specify File',
                                       default='*.trackersave',
                                       filetypes=self.filetypes)
        if filename:
            # if filename.endswith(self.filetypes[0]):
            f = open(filename)
            return json.load(f)
        else:
            return None

    def saveFileDialog(self, data):
        filename = easygui.filesavebox(msg='Load tracker save',
                                       title='Specify File',
                                       default='*.trackersave',
                                       filetypes=self.filetypes)

        if filename:
            extension = self.filetypes[0][0].replace('*', '')
            if not filename.endswith(extension):
                filename = filename + extension
            with open(filename, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.close()
