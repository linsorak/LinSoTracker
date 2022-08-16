import os
import signal
from multiprocessing import Process

class Updater:
    def __init__(self):
        proc = Process(target=self.count())

        proc.start()


        proc.join()


    def count(self):
        à
        for i in range(0, 100000):
            print(i)