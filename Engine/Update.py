import threading

class Update(threading.Thread):
    def __init__(self, callback=lambda: None):
        threading.Thread.__init__(self)
        self.callback = callback

    def run(self):
        self.callback()
