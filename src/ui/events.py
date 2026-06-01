from enum import Enum


class Button(Enum):
    A = "A"
    B = "B"
    PWR = "PWR"


class Edge(Enum):
    PRESS = "PRESS"
    RELEASE = "RELEASE"


class ButtonEvent(Enum):
    BTN_A_PRESS = "BTN_A_PRESS"
    BTN_A_DOUBLE = "BTN_A_DOUBLE"
    BTN_A_LONG = "BTN_A_LONG"
    BTN_B_PRESS = "BTN_B_PRESS"
    BTN_B_LONG = "BTN_B_LONG"
    PWR_SHORT = "PWR_SHORT"
    PWR_DOUBLE = "PWR_DOUBLE"
    PWR_LONG = "PWR_LONG"
