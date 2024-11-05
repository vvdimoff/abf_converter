from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import re
import json

@dataclass
class Hole:
    center: Tuple[float, float]
    diameter: float
    depth: float

    def to_dict(self):
        return {
            "center": {
                "x": self.center[0],
                "y": self.center[1]
            },
            "diameter": self.diameter,
            "depth": self.depth
        }

@dataclass
class Groove:
    start: Tuple[float, float]
    end: Tuple[float, float]
    width: float
    depth: float

    def to_dict(self):
        return {
            "start": {
                "x": self.start[0],
                "y": self.start[1]
            },
            "end": {
                "x": self.end[0],
                "y": self.end[1]
            },
            "width": self.width,
            "depth": self.depth
        }

@dataclass
class Panel:
    thickness: float
    front_face: List[Tuple[Tuple[float, float], Tuple[float, float]]]
    grain_direction: Tuple[float, float]
    origin_point: Tuple[float, float]
    dimensions: Dict[str, float]
    holes: List[Hole]
    grooves: List[Groove]

    def to_dict(self):
        return {
            "dimensions": self.dimensions,
            "grain_direction": {
                "x": self.grain_direction[0],
                "y": self.grain_direction[1]
            },
            "origin_point": {
                "x": self.origin_point[0],
                "y": self.origin_point[1]
            },
            "holes": [hole.to_dict() for hole in self.holes],
            "grooves": [groove.to_dict() for groove in self.grooves]
        }

class PanelBuilder:
    def __init__(self, panel_data: Dict):
        self.panel_data = panel_data

    def build(self) -> Dict:
        """Создает JSON-представление панели из данных"""
        panel = {
            'size': self.panel_data['size'],
            'edges': [],
            'holes': [],
            'grooves': [],
            'corners': []
        }

        # Добавляем кромки
        for edge in self.panel_data['edges']:
            panel['edges'].append({
                'thickness': edge['thickness'],
                'side': edge['side'],
                'position': {
                    'tip': [abs(edge['coordinates']['tip'][0]), edge['coordinates']['tip'][1]],
                    'base1': [abs(edge['coordinates']['base1'][0]), edge['coordinates']['base1'][1]],
                    'base2': [abs(edge['coordinates']['base2'][0]), edge['coordinates']['base2'][1]]
                }
            })

        # Добавляем отверстия
        for hole in self.panel_data['holes']:
            panel['holes'].append(hole.to_dict())

        # Добавляем пазы
        for groove in self.panel_data['grooves']:
            panel['grooves'].append(groove.to_dict())

        return panel