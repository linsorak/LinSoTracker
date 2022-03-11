import os.path
import platform
import subprocess
import sys
from tkinter import ttk
from tkinter import *
from tkinter import messagebox as m_box
from zipfile import ZipFile

import requests

from Tools.CoreService import CoreService


class Updater:
    def __init__(self):
        self.core_service = CoreService()
        self.win = Tk()
        self.win.title("LinSoTracker Updater")
        self.win.geometry("250x150")
        self.win.minsize(250, 150)
        self.win.resizable(False, False)
        self.label = Label(self.win)
        self.label.config(text='Downloading update, please wait')
        self.label.pack(side=TOP, expand=YES, fill=BOTH)
        self.win.title("Updater")
        self.center(self.win)

        self.os = None

        if platform.system() == 'Windows':
            self.os = "win"
        elif platform.system() == 'Linux':
            self.os = "linux"
        elif platform.system() == 'Darwin':
            if platform.machine() == 'arm64':
                self.os = "mac-apple-silicon"
            else:
                self.os = "mac-intel"

        print(self.core_service.get_temp_path())
        self.update_dir = os.path.join(self.core_service.get_temp_path(), "Update")
        self.core_service.create_directory(self.update_dir)
        self.extract_updator()
        self.download_path()


        self.win.mainloop()

    def download_path(self):
        url, file = self.generate_url()
        req = requests.get(url)
        filename = os.path.join(self.update_dir, file)

        try:
            with open(filename, 'wb') as output_file:
                output_file.write(req.content)

            resources_path = os.path.join(self.core_service.get_temp_path(), "tracker")
            win_updator_path = os.path.join(resources_path, "updator.exe")
            subprocess.run([win_updator_path, "-exe_path {}".format(self.core_service.app_path)])
            exit(1)
        except:
            exit(1)

    def generate_url(self):
        main_url = "http://linsotracker.com/tracker_python/update/patch/"
        file = "{}-{}.ltp".format(self.os, self.core_service.get_new_version())
        return main_url + file, file

    def onClick(self):
        m_box.showerror("Error", "Only PDF Files are Allowed to Download !")

    def extract_updator(self):
        filename = os.path.join(self.core_service.get_app_path(), "tracker.data")
        resources_path = os.path.join(self.core_service.get_temp_path(), "tracker")
        self.core_service.create_directory(resources_path)
        if os.path.isfile(filename):
            zip = ZipFile(filename)
            zip.extractall(resources_path)
            zip.close()

    @staticmethod
    def center(win):
        win.update_idletasks()
        width = win.winfo_width()
        frm_width = win.winfo_rootx() - win.winfo_x()
        win_width = width + 2 * frm_width
        height = win.winfo_height()
        titlebar_height = win.winfo_rooty() - win.winfo_y()
        win_height = height + titlebar_height + frm_width
        x = win.winfo_screenwidth() // 2 - win_width // 2
        y = win.winfo_screenheight() // 2 - win_height // 2
        win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        win.deiconify()
