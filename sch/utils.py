from enum import Enum
from PyQt5.QtGui import QColor


class Coord:
    # database unit is the micron
    DBU_PER_MM = 1000
    DBU_PER_INCH = 25400

    @staticmethod
    def inchToSch(x):
        return int(x*Coord.DBU_PER_INCH)

    @staticmethod
    def mmToSch(x):
        return int(x*Coord.DBU_PER_MM)

    @staticmethod
    def schToMm(x):
        return float(x) / Coord.DBU_PER_MM

    @staticmethod
    def schToInch(x):
        return float(x) / Coord.DBU_PER_INCH


class LayerType(Enum):
    """Layer type enumeration"""
    background = 0,  # page background
    grid = 1,        # grid dots / lines
    annotate = 2,    # annotation elements (lines, titleblocks, text, etc)
    symbol = 3,      # symbol elements
    wire = 4,        # wires
    junction = 5     # wire junctions


class Layer:
    COLORS = {LayerType.background:     QColor(0, 0, 0),
              LayerType.grid:           QColor(250, 250, 250),
              LayerType.annotate:       QColor(255, 255, 255),
              LayerType.symbol:         QColor(255, 255, 255),
              LayerType.wire:           QColor(255, 255, 255),
              LayerType.junction:       QColor(255, 255, 255),
              }

    @staticmethod
    def color(t):
        return Layer.COLORS[t]
