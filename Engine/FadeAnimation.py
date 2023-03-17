import math
from enum import Enum


class FadeMode(Enum):
    REPEAT = 0
    FADE = 1


class FadeAnimation:
    def __init__(self, fadeStart, fadeEnd, fadeStep, mode):
        self.amount = None
        self.fadeValue = None
        self.fadeStart = fadeStart
        self.fadeEnd = fadeEnd
        self.fadeStep = fadeStep
        self.mode = mode
        self.done = False
        self.reset()

    def reset(self):
        self.fadeValue = self.fadeStart
        self.amount = 0
        self.done = False

    def update(self):
        if self.done:
            return self.fadeValue

        self.amount += self.fadeStep
        angle = self.amount * math.pi / 1000
        self.fadeValue = round((self.fadeEnd - self.fadeStart) * math.sin(angle)) + self.fadeStart

        if self.mode == FadeMode.REPEAT and self.fadeValue <= self.fadeStart:
            self.reset()

        if self.mode == FadeMode.FADE:
            if self.fadeStart < self.fadeEnd:
                if self.fadeValue >= self.fadeEnd:
                    self.fadeValue = self.fadeEnd
                    self.done = True
            else:
                if self.fadeValue <= self.fadeEnd:
                    self.fadeValue = self.fadeEnd
                    self.done = True

        return self.fadeValue

    def getFadeValue(self):
        return self.fadeValue
