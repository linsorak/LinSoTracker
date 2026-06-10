import json
import os
from tkinter import filedialog, messagebox

from cryptography.fernet import Fernet

from Tools.CoreService import CoreService

key_encryption = "I5WpbQcf6qeid_6pnm54RlQOKftZBL-ZQ8XjJCO6AGc="

class SaveLoadTool:
    def __init__(self):
        self.extension = ".trackersave"
        self.filetypes = [("LinSoTracker Save", self.extension)]
        self.fernet = Fernet(key_encryption)
        self.core_service = CoreService()
        self.last_path_key = "lastTrackerSavePath"

    def get_last_directory(self):
        user_configuration = os.path.join(self.core_service.temp_path_fixe, "user.conf")
        if os.path.exists(user_configuration):
            try:
                with open(user_configuration, 'r') as f:
                    data = json.load(f)
                path = data.get(self.last_path_key)
                if path and os.path.isdir(path):
                    return path
            except (json.JSONDecodeError, OSError):
                pass
        return os.path.expanduser("~/Documents")

    def save_last_directory(self, filename):
        if filename:
            directory = os.path.dirname(os.path.abspath(filename))
            if directory and os.path.isdir(directory):
                self.core_service.save_configuration(self.last_path_key, directory)

    def openFileNameDialog(self):
        filename = filedialog.askopenfilename(initialdir=self.get_last_directory(), title="Load tracker save",
                                              filetypes=self.filetypes)
        self.save_last_directory(filename)
        return self.loadFile(filename)

    def loadFile(self, filename):
        if filename:
            try:
                with open(filename, 'rb') as file:
                    content = file.read()

                try:
                    decrypted = self.fernet.decrypt(content)
                    return json.loads(decrypted)
                except:
                    try:
                        return json.loads(content.decode('utf-8'))
                    except:
                        messagebox.showerror('Error', 'This save is not compatible with this version')
                        return None
            except Exception as e:
                messagebox.showerror('Error', f'Failed to load the file: {str(e)}')
                return None
        else:
            return None

    def saveFileDialog(self, data):
        filename = filedialog.asksaveasfilename(initialdir=self.get_last_directory(), title="Saving tracker informations",
                                                filetypes=self.filetypes)
        if filename:

            if not filename.endswith(self.extension):
                filename = filename + self.extension
            self.save_last_directory(filename)

            # json_data_dump = json.dumps(data, indent=2)
            json_data_dump = json.dumps(data, indent=4).encode('utf-8')
            # encrypted = self.fernet.encrypt(json_data_dump)
            with open(filename, 'wb') as f:
                f.write(json_data_dump)
                f.close()
