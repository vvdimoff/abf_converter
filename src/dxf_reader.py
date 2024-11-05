import ezdxf
from dataclasses import dataclass
from typing import List, Tuple, Dict
import re

@dataclass
class Hole:
    center: Tuple[float, float]  # координаты центра
    diameter: float              # диаметр в мм
    depth: float                # глубина в мм

@dataclass
class Groove:
    start: Tuple[float, float]  # начальная точка
    end: Tuple[float, float]    # конечная точка
    width: float               # ширина паза
    depth: float               # глубина паза

@dataclass
class Panel:
    thickness: float
    front_face: List[Tuple[Tuple[float, float], Tuple[float, float]]]  # абсолютные координаты
    grain_direction: Tuple[float, float]
    origin_point: Tuple[float, float]  # левый нижний угол детали
    dimensions: Dict[str, float]
    holes: List[Hole]  # абсолютные координаты
    grooves: List[Groove]  # абсолютные координаты

def parse_hole_layer_name(layer_name: str) -> Tuple[float, float]:
    """Извлекает диаметр и глубину из имени слоя D{diameter}_DEPTH{depth}"""
    pattern = r'D(\d+(?:_\d+)?)_DEPTH(\d+(?:_\d+)?)'
    match = re.match(pattern, layer_name)
    if match:
        diameter = float(match.group(1).replace('_', '.'))
        depth = float(match.group(2).replace('_', '.'))
        return diameter, depth
    
    pattern_through = r'D(\d+(?:_\d+)?)_DEPTHF'
    match = re.match(pattern_through, layer_name)
    if match:
        diameter = float(match.group(1).replace('_', '.'))
        depth = -1
        return diameter, depth
    
    return None

def parse_groove_depth(layer_name: str) -> float:
    """Извлекает глубину из имени слоя PAZ_DEPTH{depth}"""
    pattern = r'PAZ_DEPTH(\d+_\d+)'  # обновленный паттерн
    match = re.match(pattern, layer_name)
    if match:
        depth = float(match.group(1).replace('_', '.'))
        return depth
    return None

def print_dxf_structure(doc):
    """Выводит структуру DXF файла, сгруппированную по слоям и блокам"""
    msp = doc.modelspace()
    layers_content = {}
    
    def process_entity(entity, insert_offset=(0,0)):
        layer = entity.dxf.layer
        if layer not in layers_content:
            layers_content[layer] = {
                'standalone': {
                    'circles': [],
                    'lines': set()
                },
                'blocks': {}
            }
        
        if entity.dxftype() == 'INSERT':
            block_name = entity.dxf.name
            block = doc.blocks[block_name]
            
            # Вычисляем точку вставки с учетом смещения
            current_insert = (
                entity.dxf.insert.x + insert_offset[0],
                entity.dxf.insert.y + insert_offset[1]
            )
            
            # Создаем новый блок или получаем существующий
            if block_name not in layers_content[layer]['blocks']:
                layers_content[layer]['blocks'][block_name] = {
                    'instances': [],
                    'circles': [],
                    'lines': set()
                }
            
            # Добавляем точку вставки блока
            layers_content[layer]['blocks'][block_name]['instances'].append(current_insert)
            
            # Собираем сущности блока
            for e in block:
                if e.dxftype() == 'INSERT':
                    process_entity(e, current_insert)
                elif e.dxftype() == 'LINE':
                    start = (round(e.dxf.start.x + current_insert[0], 1),
                            round(e.dxf.start.y + current_insert[1], 1))
                    end = (round(e.dxf.end.x + current_insert[0], 1),
                          round(e.dxf.end.y + current_insert[1], 1))
                    if start != end:  # пропускаем нулевые линии
                        layers_content[layer]['blocks'][block_name]['lines'].add((start, end))
                elif e.dxftype() == 'CIRCLE':
                    center = (round(e.dxf.center.x + current_insert[0], 1),
                            round(e.dxf.center.y + current_insert[1], 1))
                    layers_content[layer]['blocks'][block_name]['circles'].append({
                        'center': center,
                        'radius': round(e.dxf.radius, 1)
                    })
        
        elif entity.dxftype() == 'CIRCLE':
            center = (round(entity.dxf.center.x + insert_offset[0], 1),
                     round(entity.dxf.center.y + insert_offset[1], 1))
            layers_content[layer]['standalone']['circles'].append({
                'center': center,
                'radius': round(entity.dxf.radius, 1)
            })
        elif entity.dxftype() == 'LINE':
            start = (round(entity.dxf.start.x + insert_offset[0], 1),
                    round(entity.dxf.start.y + insert_offset[1], 1))
            end = (round(entity.dxf.end.x + insert_offset[0], 1),
                  round(entity.dxf.end.y + insert_offset[1], 1))
            if start != end:  # пропускаем нулевые линии
                layers_content[layer]['standalone']['lines'].add((start, end))
    
    # Обрабатываем все сущности
    for entity in msp:
        process_entity(entity)
    
    # Выводим структуру
    print("\nDXF Structure:")
    for layer in sorted(layers_content.keys()):
        content = layers_content[layer]
        has_content = (
            content['standalone']['circles'] or 
            content['standalone']['lines'] or 
            content['blocks']
        )
        if has_content:
            print(f"\n[{layer}]")
            
            # Выводим отдельные сущности
            standalone = content['standalone']
            if standalone['circles']:
                print(f"  Standalone circles: {len(standalone['circles'])}")
                for circle in standalone['circles']:
                    print(f"    center=({circle['center'][0]}, {circle['center'][1]}), r={circle['radius']}")
            
            if standalone['lines']:
                print(f"  Standalone lines: {len(standalone['lines'])}")
                for i, (start, end) in enumerate(list(standalone['lines'])[:3]):
                    print(f"    ({start[0]}, {start[1]}) → ({end[0]}, {end[1]})")
                if len(standalone['lines']) > 3:
                    print(f"    ... and {len(standalone['lines'])-3} more lines")
            
            # Выводим блоки
            if content['blocks']:
                print(f"  Blocks: {len(content['blocks'])}")
                for block_name, block in content['blocks'].items():
                    print(f"    Block {block_name}:")
                    print(f"      Instances: {len(block['instances'])}")
                    for i, pos in enumerate(block['instances'][:2]):
                        print(f"        at ({pos[0]}, {pos[1]})")
                    if len(block['instances']) > 2:
                        print(f"        ... and {len(block['instances'])-2} more")
                    
                    if block['circles']:
                        print(f"      Circles: {len(block['circles'])}")
                    if block['lines']:
                        print(f"      Lines: {len(block['lines'])}")
                        for i, (start, end) in enumerate(list(block['lines'])[:2]):
                            print(f"        ({start[0]}, {start[1]}) → ({end[0]}, {end[1]})")
                        if len(block['lines']) > 2:
                            print(f"        ... and {len(block['lines'])-2} more lines")

def read_dxf(filename: str) -> Panel:
    try:
        print(f"\nОткрываем файл: {filename}\n")
        doc = ezdxf.readfile(filename)
        print_dxf_structure(doc)
        
        msp = doc.modelspace()
        front_lines = set()
        label_lines = []
        holes = []
        grooves = []
        
        def process_entity(entity, insert_point=(0,0)):
            if entity.dxf.layer.startswith('D') and '_DEPTH' in entity.dxf.layer:
                hole_info = parse_hole_layer_name(entity.dxf.layer)
                if hole_info:
                    diameter, depth = hole_info
                    if entity.dxftype() == 'CIRCLE':
                        center = (
                            round(entity.dxf.center.x + insert_point[0], 6),
                            round(entity.dxf.center.y + insert_point[1], 6)
                        )
                        holes.append(Hole(center=center, diameter=diameter, depth=depth))
                        
            elif entity.dxf.layer == 'ABF_CUTTINGLINES':
                if entity.dxftype() == 'INSERT':
                    block = doc.blocks[entity.dxf.name]
                    new_insert_point = (
                        insert_point[0] + entity.dxf.insert.x,
                        insert_point[1] + entity.dxf.insert.y
                    )
                    for e in block:
                        process_entity(e, new_insert_point)
                        
                elif entity.dxftype() == 'LINE':
                    start = (
                        round(entity.dxf.start.x + insert_point[0], 6),
                        round(entity.dxf.start.y + insert_point[1], 6)
                    )
                    end = (
                        round(entity.dxf.end.x + insert_point[0], 6),
                        round(entity.dxf.end.y + insert_point[1], 6)
                    )
                    if start != end:
                        line = tuple(sorted([start, end]))
                        front_lines.add(line)
            
            elif entity.dxf.layer == 'ABF_LABEL':
                if entity.dxftype() == 'LINE':
                    start = (
                        round(entity.dxf.start.x + insert_point[0], 6),
                        round(entity.dxf.start.y + insert_point[1], 6)
                    )
                    end = (
                        round(entity.dxf.end.x + insert_point[0], 6),
                        round(entity.dxf.end.y + insert_point[1], 6)
                    )
                    if start != end:
                        label_lines.append((start, end))
            
            elif entity.dxftype() == 'INSERT':
                block = doc.blocks[entity.dxf.name]
                new_insert_point = (
                    insert_point[0] + entity.dxf.insert.x,
                    insert_point[1] + entity.dxf.insert.y
                )
                for e in block:
                    process_entity(e, new_insert_point)
        
        # Обрабатываем все сущности
        for entity in msp:
            process_entity(entity)
        
        # Преобразуем линии контура в список
        front_face = [(line[0], line[1]) for line in front_lines]
        
        # Находим стрелку направления текстуры
        # Обычно это самая длинная линия в слое ABF_LABEL
        grain_direction = (0, 1)  # по умолчанию вверх
        if label_lines:
            # Находим самую длинную линию (обычно это стрелка)
            def line_length(line):
                (x1, y1), (x2, y2) = line
                return ((x2-x1)**2 + (y2-y1)**2)**0.5
            
            arrow_line = max(label_lines, key=line_length)
            start, end = arrow_line
            
            # Вычисляем вектор направления
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = (dx*dx + dy*dy)**0.5
            if length > 0:
                grain_direction = (dx/length, dy/length)
        
        # Сначала найдем левую нижюю точку (origin)
        all_points = []
        for start, end in front_face:
            all_points.extend([start, end])
            
        if all_points:
            # Находим самую нижнюю из самых левых точек
            left_x = min(x for x, _ in all_points)
            left_points = [(x, y) for x, y in all_points if x == left_x]
            origin_point = min(left_points, key=lambda p: p[1])
        else:
            origin_point = (0, 0)
        
        # Теперь преобразуем координаты отверстий относительно origin_point
        transformed_holes = []
        for hole in holes:
            relative_center = (
                round(hole.center[0] - origin_point[0], 2),  # округляем до сотых
                round(hole.center[1] - origin_point[1], 2)   # округляем до сотых
            )
            transformed_holes.append(Hole(
                center=relative_center,
                diameter=hole.diameter,
                depth=hole.depth
            ))
        
        # После того как собрал все линии контура, вычисляем размер
        all_points = []
        for start, end in front_face:
            all_points.extend([start, end])
            
        if all_points:
            # Находим крайние точки
            min_x = min(x for x, _ in all_points)
            max_x = max(x for x, _ in all_points)
            min_y = min(y for _, y in all_points)
            max_y = max(y for _, y in all_points)
            
            # Вычисляем размеры
            width = abs(max_x - min_x)
            height = abs(max_y - min_y)
            
            dimensions = {
                "width": round(width, 2),  # ширина в мм
                "height": round(height, 2),  # высота в мм
                "thickness": 18.0  # толщина в мм (пока хардкод)
            }
            
            print("\nРазмеры панели:")
            print(f"- Ширина: {dimensions['width']} мм")
            print(f"- Высота: {dimensions['height']} мм")
            print(f"- Толщина: {dimensions['thickness']} мм")
        else:
            dimensions = {"width": 0, "height": 0, "thickness": 0}
        
        # Округляем размеры до сотх
        dimensions = {
            "width": round(dimensions["width"], 2),
            "height": round(dimensions["height"], 2),
            "thickness": round(dimensions["thickness"], 2)
        }
        
        return Panel(
            thickness=dimensions["thickness"],
            front_face=front_face,
            grain_direction=grain_direction,
            origin_point=origin_point,
            dimensions=dimensions,
            holes=transformed_holes,
            grooves=grooves  # Пока пустой список
        )
        
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return None

def panel_to_dict(panel: Panel) -> dict:
    """Конвертирует объект Panel в словарь для JSON с абсолютными координатами"""
    return {
        "dimensions": {
            "width": round(panel.dimensions["width"], 2),
            "height": round(panel.dimensions["height"], 2),
            "thickness": round(panel.dimensions["thickness"], 2)
        },
        "grain_direction": {
            "x": round(panel.grain_direction[0], 2),
            "y": round(panel.grain_direction[1], 2)
        },
        "origin_point": {
            "x": round(panel.origin_point[0], 2),
            "y": round(panel.origin_point[1], 2)
        },
        "holes": [
            {
                "center": {
                    "x": round(hole.center[0], 2),
                    "y": round(hole.center[1], 2)
                },
                "diameter": round(hole.diameter, 2),
                "depth": "through" if hole.depth == -1 else round(hole.depth, 2)
            }
            for hole in panel.holes
        ],
        "grooves": [
            {
                "start": {
                    "x": round(groove.start[0], 2),
                    "y": round(groove.start[1], 2)
                },
                "end": {
                    "x": round(groove.end[0], 2),
                    "y": round(groove.end[1], 2)
                },
                "width": round(groove.width, 2),
                "depth": round(groove.depth, 2)
            }
            for groove in panel.grooves
        ]
    }
