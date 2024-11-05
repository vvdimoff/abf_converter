from typing import Tuple, Union

class Hole:
    def __init__(self, center: Tuple[float, float], diameter: float, depth: Union[float, str]):
        self.center = center
        self.diameter = diameter
        self.depth = depth  # может быть числом или "through" для сквозных отверстий

    def to_dict(self):
        return {
            "center": {"x": self.center[0], "y": self.center[1]},
            "diameter": self.diameter,
            "depth": self.depth
        }

class Groove:
    def __init__(self, start: Tuple[float, float], end: Tuple[float, float], 
                 width: float, depth: float):
        self.start = start
        self.end = end
        self.width = width
        self.depth = depth

    def to_dict(self):
        return {
            "start": {"x": self.start[0], "y": self.start[1]},
            "end": {"x": self.end[0], "y": self.end[1]},
            "width": self.width,
            "depth": self.depth
        } 