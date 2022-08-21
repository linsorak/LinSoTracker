import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo
from calendar import month_name

class MapSelector:
    def __init__(self):
        global window  # so it can be destroyed in the other function
        window = tk.Tk()
        # message = ...
        # message.grid ...
        button = tk.Button(window, text="restart", width=5)
        button.grid  # where you want it