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
            'size': {
                'width': round(self.panel_data['size']['width'], 2),
                'height': round(self.panel_data['size']['height'], 2),
                'thickness': self.panel_data['size']['thickness']
            },
            'edges': [],
            'holes': [],
            'grooves': [],
            'cutouts': [],
            'corners': []
        }

        # Добавляем кромки
        for edge in self.panel_data['edges']:
            panel['edges'].append({
                'thickness': round(edge['thickness'], 2),
                'side': edge['side'],
                'position': {
                    'start': [round(abs(edge['coordinates']['start'][0]), 2), 
                             round(edge['coordinates']['start'][1], 2)],
                    'end': [round(abs(edge['coordinates']['end'][0]), 2), 
                           round(edge['coordinates']['end'][1], 2)]
                }
            })

        # Добавляем вырезы
        for cutout in self.panel_data.get('cutouts', []):
            if cutout['type'] == 'L':
                panel['cutouts'].append({
                    'type': 'L',
                    'position': cutout['position'],
                    'size': {
                        'x': round(cutout['size_x'], 2),
                        'y': round(cutout['size_y'], 2)
                    }
                })

        return panel