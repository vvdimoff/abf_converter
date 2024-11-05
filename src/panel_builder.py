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
    def __init__(self, panels_data):
        self.panels_data = panels_data

    def to_json(self):
        """Преобразует данные панелей в JSON строку"""
        result = {
            "panels": []
        }
        
        for panel in self.panels_data:
            panel_json = {
                "name": panel["name"],
                "dimensions": {
                    "width": panel["width"],
                    "height": panel["height"]
                },
                "origin_point": {
                    "x": panel["origin_point"][0],
                    "y": panel["origin_point"][1]
                },
                "elements": {
                    "holes": [
                        {
                            "center": {
                                "x": hole["center"][0],
                                "y": hole["center"][1]
                            },
                            "radius": hole["radius"],
                            "type": hole["layer"]
                        } for hole in panel["holes"]
                    ],
                    "grooves": [
                        {
                            "start": {
                                "x": groove["start"][0],
                                "y": groove["start"][1]
                            },
                            "end": {
                                "x": groove["end"][0],
                                "y": groove["end"][1]
                            }
                        } for groove in panel["grooves"]
                    ]
                }
            }
            result["panels"].append(panel_json)
        
        return json.dumps(result, indent=2, ensure_ascii=False)