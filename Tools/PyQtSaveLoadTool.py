import json

from PyQt5.QtWidgets import QWidget, QFileDialog


class PyQtSaveLoadTool(QWidget):
    def __init__(self):
        QWidget.__init__(self)

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Load tracker save", "",
                                                  "LinSoTracker Save(*.trackersave)", options=options)

        if fileName:
            f = open(fileName)
            return json.load(f)
        else:
            return None

    def saveFileDialog(self, data):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Save tracker save", "",
                                                  "LinSoTracker Save(*.trackersave)", options=options)
        if fileName:
            with open(fileName, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.close()
