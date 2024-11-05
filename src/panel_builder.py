from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import re

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
    def __init__(self, dxf_data: Dict):
        self.dxf_data = dxf_data
        
    def build(self) -> Panel:
        """Создает панель из проанализированных данных DXF"""
        print("\nDebug: Analyzing blocks for holes")
        for layer_name, layer_content in self.dxf_data.items():
            for block_name, block in layer_content.get('blocks', {}).items():
                if block_name.startswith('GROUP'):
                    print(f"\nBlock: {block_name}")
                    print(f"References: {block.get('block_references', set())}")
                    print(f"Special refs: {block.get('special_refs', set())}")
                    if 'circles' in block:
                        print(f"Circles: {block['circles']}")
                    if 'instances' in block:
                        print(f"Instances: {block['instances']}")
                    if hasattr(block, 'attribs'):
                        print(f"Attributes: {block.attribs}")
        
        # Находим контур
        front_face = self._find_cutting_lines()
        
        # Находим размеры и origin point из контура
        dimensions, origin_point = self._calculate_dimensions(front_face)
        
        # Находим ABF метку (толщина и дугие параметры)
        abf_info = self._find_abf_label()
        thickness = abf_info.get('thickness', 18.0)
        
        # Находим отверстия и пазы
        holes = self._find_holes()
        grooves = self._find_grooves()
        
        return Panel(
            thickness=thickness,
            front_face=front_face,
            grain_direction=(0.0, 1.0),
            origin_point=origin_point,
            dimensions=dimensions,
            holes=holes,
            grooves=grooves
        )
    
    def _find_cutting_lines(self) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Находит линии контура (грани) панели"""
        cutting_lines = []
        layer_content = self.dxf_data.get('0', {})
        
        for block_name, block in layer_content.get('blocks', {}).items():
            # Ищем блок с контуром (обычно это _______3)
            if block_name.startswith('_______'):
                cutting_lines.extend(list(block['lines']))
        
        return cutting_lines
    
    def _find_abf_label(self) -> Dict[str, Any]:
        """Находит и анализирует ABF метку"""
        label_info = {}
        layer_content = self.dxf_data.get('0', {})
        
        for block_name, block in layer_content.get('blocks', {}).items():
            if block_name.startswith('THICKNESS_'):
                try:
                    thickness = float(block_name.split('THICKNESS_')[1])
                    label_info['thickness'] = thickness
                except ValueError:
                    pass
        
        return label_info
    
    def _find_holes(self) -> List[Hole]:
        """Находит отверстия в блоках GROUP* по слою окружности"""
        holes = []
        
        for layer_content in self.dxf_data.values():
            for block_name, block in layer_content.get('blocks', {}).items():
                if not block_name.startswith('GROUP'):
                    continue
                
                # Проверяем есть ли окружности в блоке
                for circle in block.get('circles', []):
                    circle_layer = circle.get('layer', '')
                    if circle_layer.startswith('D') and ('DEPTH' in circle_layer):
                        try:
                            # Парсим диаметр и глубину из имени слоя
                            diameter = float(circle_layer.split('D')[1].split('_')[0].replace('_', '.'))
                            depth = "through" if 'DEPTHF' in circle_layer else float(circle_layer.split('DEPTH')[1].replace('_', '.'))
                            
                            holes.append(Hole(
                                center=circle['center'],
                                diameter=diameter,
                                depth=depth
                            ))
                            print(f"Found hole: center={circle['center']}, diameter={diameter}, depth={depth}")
                        except (ValueError, IndexError) as e:
                            print(f"Warning: Could not parse hole layer: {circle_layer}, error: {e}")
        
        return holes
    
    def _find_grooves(self) -> List[Groove]:
        """Находит пазы в слое PAZ_DEPTH*"""
        grooves = []
        
        for layer_name, layer_content in self.dxf_data.items():
            if not layer_name.startswith('PAZ_DEPTH'):
                continue
                
            depth = float(layer_name.split('PAZ_DEPTH')[1].replace('_', '.'))
            
            for block_name, block in layer_content.get('blocks', {}).items():
                if len(block['lines']) == 4:  # Паз состоит из 4 линий
                    # Находим крайние точки паза
                    all_points = []
                    for start, end in block['lines']:
                        all_points.extend([start, end])
                    
                    x_coords = [p[0] for p in all_points]
                    y_coords = [p[1] for p in all_points]
                    
                    # Определяем ориентацию паза
                    if max(x_coords) - min(x_coords) > max(y_coords) - min(y_coords):
                        # Горизонтальный паз
                        start = (min(x_coords), sum(y_coords) / len(y_coords))
                        end = (max(x_coords), sum(y_coords) / len(y_coords))
                        width = max(y_coords) - min(y_coords)
                    else:
                        # Вертикальный паз
                        start = (sum(x_coords) / len(x_coords), min(y_coords))
                        end = (sum(x_coords) / len(x_coords), max(y_coords))
                        width = max(x_coords) - min(x_coords)
                    
                    grooves.append(Groove(
                        start=start,
                        end=end,
                        width=width,
                        depth=depth
                    ))
        
        return grooves
    
    def _calculate_dimensions(self, front_face) -> Tuple[Dict[str, float], Tuple[float, float]]:
        """Вычисляет размеры панели и точку начала координат"""
        if not front_face:
            return {'width': 0, 'height': 0, 'thickness': 18.0}, (0, 0)
        
        # Находим минимальные и максимальные координаты
        x_coords = []
        y_coords = []
        for start, end in front_face:
            x_coords.extend([start[0], end[0]])
            y_coords.extend([start[1], end[1]])
        
        min_x = min(x_coords) if x_coords else 0
        max_x = max(x_coords) if x_coords else 0
        min_y = min(y_coords) if y_coords else 0
        max_y = max(y_coords) if y_coords else 0
        
        dimensions = {
            'width': abs(max_x - min_x),
            'height': abs(max_y - min_y),
            'thickness': 18.0
        }
        
        origin_point = (min_x, min_y)
        
        return dimensions, origin_point