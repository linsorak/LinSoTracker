import json
from tkinter import filedialog, messagebox

from cryptography.fernet import Fernet

from Tools.CoreService import CoreService

core_service = CoreService()


class SaveLoadTool:
    def __init__(self):
        self.extension = ".trackersave"
        self.filetypes = [("LinSoTracker Save", self.extension)]
        self.fernet = Fernet(core_service.key_encryption)

    def openFileNameDialog(self):
        filename = filedialog.askopenfilename(initialdir="/", title="Load tracker save",
                                              filetypes=self.filetypes)
        return self.loadEcryptedFile(filename)

    def loadEcryptedFile(self, filename):
        if filename:
            # if filename.endswith(self.filetypes[0]):
            f = open(filename)
            with open(filename, 'rb') as enc_file:
                try:
                    encrypted = enc_file.read()
                    decrypted = self.fernet.decrypt(encrypted)
                    return json.loads(decrypted)
                except:
                    messagebox.showerror('Error', 'This save is not compatible with this version')
                    return None
        else:
            return None

    def saveFileDialog(self, data):
        filename = filedialog.asksaveasfilename(initialdir="/", title="Saving tracker informations",
                                                filetypes=self.filetypes)
        if filename:

            if not filename.endswith(self.extension):
                filename = filename + self.extension

            # json_data_dump = json.dumps(data, indent=2)
            json_data_dump = json.dumps(data, indent=4).encode('utf-8')
            encrypted = self.fernet.encrypt(json_data_dump)
            with open(filename, 'wb') as f:
                f.write(encrypted)
                f.close()
