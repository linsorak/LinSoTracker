import json
from tkinter import filedialog, messagebox

from cryptography.fernet import Fernet

key_encryption = "I5WpbQcf6qeid_6pnm54RlQOKftZBL-ZQ8XjJCO6AGc="

class SaveLoadTool:
    def __init__(self):
        self.extension = ".trackersave"
        self.filetypes = [("LinSoTracker Save", self.extension)]
        self.fernet = Fernet(key_encryption)

    def openFileNameDialog(self):
        filename = filedialog.askopenfilename(initialdir="/", title="Load tracker save",
                                              filetypes=self.filetypes)
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
        filename = filedialog.asksaveasfilename(initialdir="/", title="Saving tracker informations",
                                                filetypes=self.filetypes)
        if filename:

            if not filename.endswith(self.extension):
                filename = filename + self.extension

            # json_data_dump = json.dumps(data, indent=2)
            json_data_dump = json.dumps(data, indent=4).encode('utf-8')
            # encrypted = self.fernet.encrypt(json_data_dump)
            with open(filename, 'wb') as f:
                f.write(json_data_dump)
                f.close()
