import ezdxf
from typing import List, Tuple, Dict
from geometry import Hole, Groove

class DxfReader:
    STANDARD_OFFSET = 8.415  # Стандартный отступ кромки в мм

    def __init__(self, filename: str, debug: bool = False):
        """Инициализация чтения DXF файла"""
        self.filename = filename
        self.doc = ezdxf.readfile(filename)
        self.debug = debug
        if self.debug:
            print(f"\nОткрываем файл: {filename}")
            self._print_structure()  # Выводим структуру файла

    def _print_structure(self):
        """Выводит структуру DXF файла"""
        print("\nСтруктура DXF файла:")
        for block in self.doc.blocks:
            print(f"Блок: {block.name}")
            for entity in block:
                print(f"  - {entity.dxftype()} [layer: {entity.dxf.layer}]")
                if entity.dxftype() == 'INSERT':
                    try:
                        nested_block = self.doc.blocks[entity.dxf.name]
                        print(f"    Вложенный блок {entity.dxf.name}:")
                        for e in nested_block:
                            print(f"      - {e.dxftype()} [layer: {e.dxf.layer}]")
                    except Exception as err:
                        print(f"    Ошибка при доступе к блоку: {err}")

    def _debug_print(self, *args, **kwargs):
        """Вывод отладочной информации"""
        if self.debug:
            print("DEBUG:", *args, **kwargs)

    def read(self) -> List[Dict]:
        """Читает DXF файл и возвращает данные всех панелей"""
        self.doc = ezdxf.readfile(self.filename)
        return self.get_panels_data()

    def get_panels_data(self) -> List[Dict]:
        """Получает данные о всех панелях"""
        panels_data = []
        panel_blocks = set()  # для уникальных блоков
        
        # Соираем все блои-панели и их INSERT'ы из modelspace
        for entity in self.doc.modelspace():
            if entity.dxftype() == 'INSERT':
                block = self.doc.blocks[entity.dxf.name]
                for e in block:
                    if e.dxftype() == 'INSERT' and (
                        e.dxf.name.startswith('_______') or 
                        e.dxf.name.startswith('______')
                    ):
                        print(f"DEBUG: Found panel block: {e.dxf.name}")
                        panel_blocks.add(e)  # сохраняем сам INSERT
        
        # Анализируем каждую панель
        for panel in panel_blocks:
            print(f"DEBUG: Analyzing panel: {panel.dxf.name}")
            print(f"DEBUG: Insert point: ({panel.dxf.insert.x}, {panel.dxf.insert.y})")
            panel_data = self._analyze_panel(panel)
            if panel_data:
                panels_data.append(panel_data)
        
        return panels_data

    def _get_panel_blocks(self, thickness_block):
        """Находит все блоки панелей"""
        return [
            entity for entity in thickness_block 
            if entity.dxftype() == 'INSERT' and entity.dxf.name.startswith('_______')
        ]

    def _analyze_panel(self, panel) -> Dict:
        """Анализирует панель и собирает все данные"""
        panel_block = self.doc.blocks[panel.dxf.name]
        
        # Сначала находим контур
        contour = self._get_panel_contour(panel_block)
        
        # Затем ищем все вырезы
        cutouts = self._get_cutouts(panel_block, contour)
        
        return {
            "name": panel.dxf.name,
            "size": {
                "width": contour['width'],
                "height": contour['height'],
                "thickness": 18.0
            },
            "origin_point": (round(panel.dxf.insert.x, 1), round(panel.dxf.insert.y, 1)),
            "cutouts": cutouts,
            "holes": [],  # Добавляем пустые списки для остальных элементов
            "grooves": [],
            "edges": []
        }

    def _get_holes(self, panel_block, origin_point) -> List[Hole]:
        """Получает данные об отврстиях панели"""
        holes = []
        
        for entity in panel_block:
            if entity.dxftype() == 'INSERT' and entity.dxf.name.startswith('GROUP'):
                group_block = self.doc.blocks[entity.dxf.name]
                group_insert = (entity.dxf.insert.x, entity.dxf.insert.y)
                
                for e in group_block:
                    if e.dxftype() == 'CIRCLE' and 'DEPTH' in e.dxf.layer:
                        center_x = round(e.dxf.center.x + group_insert[0] + origin_point[0], 1)
                        center_y = round(e.dxf.center.y + group_insert[1] + origin_point[1], 1)
                        
                        holes.append(Hole(
                            center=(center_x, center_y),
                            diameter=round(e.dxf.radius * 2, 1),
                            depth=self._parse_hole_depth(e.dxf.layer)
                        ))
        
        return holes

    def _parse_hole_depth(self, layer):
        """Определяет глубину отверстия по слою"""
        if 'DEPTHF' in layer:
            return 18.0  # сквозное
        elif 'DEPTH' in layer:
            depth_str = layer.split('DEPTH')[1].split('_')[0]
            try:
                return float(depth_str)
            except ValueError:
                return 0.0
        return 0.0

    def _print_file_structure(self):
        """Выводит древовидную структуру DXF файла"""
        print("\nСтруктура DXF файла:")
        
        # Собираем уникальные блоки по слоям
        layers_blocks = {}
        
        for block in self.doc.blocks:
            # Пропускаем служебные блоки
            if block.name.startswith('*'): continue
            
            # Определяем слой блока по его содержимому
            block_layer = '0'  # слой по уолчанию
            for entity in block:
                if entity.dxf.layer != '0':
                    block_layer = entity.dxf.layer
                    break
            
            if block_layer not in layers_blocks:
                layers_blocks[block_layer] = set()
            layers_blocks[block_layer].add(block.name)
        
        # Выводим структуру
        for layer, blocks in layers_blocks.items():
            print(f"\n├── [{layer}]")
            for block_name in sorted(blocks):
                block = self.doc.blocks[block_name]
                print(f"│   └── Block {block_name}")
                
                # Показываем типы элементов в блоке (без повторов)
                entities = set()
                for entity in block:
                    if entity.dxftype() == 'LINE':
                        entities.add('Lines')
                    elif entity.dxftype() == 'INSERT':
                        entities.add(f"Insert: {entity.dxf.name}")
                    else:
                        entities.add(entity.dxftype())
                
                if entities:
                    for entity in sorted(entities):
                        print(f"│       └── {entity}")

    def _analyze_special_elements(self, panel_block, origin_point):
        """Анализирует специальные элементы панели (отверстия, пазы)"""
        elements = {
            'holes': [],
            'grooves': [],
            'edges': []
        }
        
        for entity in panel_block:
            if entity.dxftype() == 'INSERT' and entity.dxf.name.startswith('GROUP'):
                group_block = self.doc.blocks[entity.dxf.name]
                group_insert = (entity.dxf.insert.x, entity.dxf.insert.y)
                
                for e in group_block:
                    # Анализ отверстий
                    if e.dxftype() == 'CIRCLE' and 'DEPTH' in e.dxf.layer:
                        center_x = round(e.dxf.center.x + group_insert[0] + origin_point[0], 1)
                        center_y = round(e.dxf.center.y + group_insert[1] + origin_point[1], 1)
                        elements['holes'].append({
                            'center': (center_x, center_y),
                            'diameter': round(e.dxf.radius * 2, 1),
                            'depth': self._parse_hole_depth(e.dxf.layer)
                        })
                    
                    # Анализ пазов
                    elif e.dxftype() == 'LINE' and e.dxf.layer == 'PAZ_DEPTH8_0':
                        start_x = round(e.dxf.start.x + group_insert[0] + origin_point[0], 1)
                        start_y = round(e.dxf.start.y + group_insert[1] + origin_point[1], 1)
                        end_x = round(e.dxf.end.x + group_insert[0] + origin_point[0], 1)
                        end_y = round(e.dxf.end.y + group_insert[1] + origin_point[1], 1)
                        elements['grooves'].append({
                            'start': (start_x, start_y),
                            'end': (end_x, end_y),
                            'width': 8.0,
                            'depth': 8.0
                        })
                    
                    # Анализ кромок
                    elif e.dxftype() == 'POLYLINE' and e.dxf.layer == 'ABF_EDGEBANDING':
                        vertices = list(e.vertices)
                        if len(vertices) == 4:
                            elements['edges'].append(self._analyze_edge(e, group_insert, origin_point))
        
        return elements

    def _analyze_edge(self, entity, group_insert, origin_point):
        """Анализирует кромку"""
        vertices = list(entity.vertices)
        tip = vertices[0].dxf.location
        base1 = vertices[1].dxf.location
        base2 = vertices[2].dxf.location
        
        # Преобразуем в абсолютные координаты
        tip_x = round(tip[0] + group_insert[0] + origin_point[0], 1)
        tip_y = round(tip[1] + group_insert[1] + origin_point[1], 1)
        base1_x = round(base1[0] + group_insert[0] + origin_point[0], 1)
        base1_y = round(base1[1] + group_insert[1] + origin_point[1], 1)
        base2_x = round(base2[0] + group_insert[0] + origin_point[0], 1)
        base2_y = round(base2[1] + group_insert[1] + origin_point[1], 1)
        
        return {
            'thickness': round(self._calculate_edge_thickness(tip_x), 1),
            'coordinates': {
                'tip': (tip_x, tip_y),
                'base1': (base1_x, base1_y),
                'base2': (base2_x, base2_y)
            }
        }

    def _parse_hole_depth(self, layer):
        """Определяет глубину отверстия по слою"""
        if 'DEPTHF' in layer:
            return 18.0  # сквозное
        elif 'DEPTH' in layer:
            depth_str = layer.split('DEPTH')[1].split('_')[0]
            try:
                return float(depth_str)
            except ValueError:
                return 0.0
        return 0.0

    def analyze_and_log(self):
        """Анализирует и выводит информацию о панелях"""
        panels_data = self.get_panels_data()
        
        print(f"\nНайдено панелей: {len(panels_data)}")
        
        for panel in panels_data:
            print(f"\nПанель: {panel['name']}")
            print(f"  Размеры: {panel['size']['width']}x{panel['size']['height']}x{panel['size']['thickness']} мм")
            print(f"  Точка вставки: {panel['origin_point']}")
            
            if panel.get('cutouts'):
                print("  Вырезы:")
                for cutout in panel['cutouts']:
                    edge_info = f" ({cutout['edge']})" if 'edge' in cutout else ""
                    print(f"    - {cutout['type']}{edge_info}:")
                    print(f"      Размер: {cutout['size']['x']}x{cutout['size']['y']} мм")
                    print(f"      Позиция: {cutout['position']['x']}, {cutout['position']['y']}")

    def _get_edges(self, panel_block) -> List[Dict]:
        """Получает данные о кромках"""
        edges = []
        
        self._debug_print("\nПоиск кромок:")
        
        # Ищем блок GROUP34_1 (там обычно кромки)
        for entity in panel_block:
            if entity.dxftype() == 'INSERT' and entity.dxf.name == 'GROUP34_1':
                block = self.doc.blocks[entity.dxf.name]
                
                for e in block:
                    if e.dxf.layer == 'ABF_EDGEBANDING':
                        if e.dxftype() == 'POLYLINE':
                            points = []
                            for vertex in e.vertices:
                                x = round(abs(vertex.dxf.location[0]), 2)
                                y = round(vertex.dxf.location[1], 2)
                                points.append((x, y))
                            
                            if len(points) >= 2:
                                edge = {
                                    'start': points[0],
                                    'end': points[-1],
                                    'points': points
                                }
                                edges.append(edge)
                                self._debug_print(f"Найдена кромка: {edge}")
        
        return edges

    def _get_cutouts(self, panel_block, contour) -> List[Dict]:
        """Находит все вырезы на панели"""
        cutouts = []
        tolerance = 1.0  # допуск для определения края
        min_size = 5.0   # минимальный размер выреза
        
        self._debug_print("\nПоиск вырезов в панели:")
        self._debug_print(f"Размеры контура: {contour['width']}x{contour['height']}")
        
        # Временное хранилище для проверки дубликатов
        seen_cutouts = set()
        
        for entity in panel_block:
            if entity.dxftype() == 'INSERT':
                try:
                    block = self.doc.blocks[entity.dxf.name]
                    for e in block:
                        if e.dxf.layer == 'ABF_EDGEBANDING':
                            points = []
                            
                            # Получаем точки в зависимости от типа полилинии
                            if hasattr(e, 'vertices'):
                                for vertex in e.vertices:
                                    # Нормализуем координаты относительно панели
                                    x = round(abs(vertex.dxf.location[0] + entity.dxf.insert.x), 2)
                                    y = round(vertex.dxf.location[1] + entity.dxf.insert.y, 2)
                                    points.append((x, y))
                            elif hasattr(e, 'get_points'):
                                for point in e.get_points():
                                    x = round(abs(point[0] + entity.dxf.insert.x), 2)
                                    y = round(point[1] + entity.dxf.insert.y, 2)
                                    points.append((x, y))
                            
                            if points:
                                # Определяем размеры
                                x_coords = [p[0] for p in points]
                                y_coords = [p[1] for p in points]
                                min_x, max_x = min(x_coords), max(x_coords)
                                min_y, max_y = min(y_coords), max(y_coords)
                                size_x = round(max_x - min_x, 2)
                                size_y = round(max_y - min_y, 2)
                                
                                # Проверяем размер
                                if size_x > min_size or size_y > min_size:
                                    # Нормализуем координаты относительно размеров панели
                                    normalized_x = round(min_x - contour.get('origin_x', 0), 2)
                                    normalized_y = round(min_y - contour.get('origin_y', 0), 2)
                                    
                                    # Определяем тип выреза
                                    is_edge = (
                                        normalized_x <= tolerance or  # левый край
                                        normalized_x + size_x >= contour['width'] - tolerance or  # правый край
                                        normalized_y <= tolerance or  # нижний край
                                        normalized_y + size_y >= contour['height'] - tolerance  # верхний край
                                    )
                                    
                                    # Создаем ключ для проверки дубликатов
                                    cutout_key = f"{size_x}_{size_y}_{normalized_x}_{normalized_y}"
                                    
                                    if cutout_key not in seen_cutouts:
                                        cutout = {
                                            'type': 'edge' if is_edge else 'inner',
                                            'size': {'x': size_x, 'y': size_y},
                                            'position': {
                                                'x': normalized_x,
                                                'y': normalized_y
                                            }
                                        }
                                        
                                        # Определяем положение для краевых вырезов
                                        if is_edge:
                                            if normalized_x <= tolerance:
                                                cutout['edge'] = 'left'
                                            elif normalized_x + size_x >= contour['width'] - tolerance:
                                                cutout['edge'] = 'right'
                                            elif normalized_y <= tolerance:
                                                cutout['edge'] = 'bottom'
                                            else:
                                                cutout['edge'] = 'top'
                                        
                                        cutouts.append(cutout)
                                        seen_cutouts.add(cutout_key)
                
                except Exception as err:
                    self._debug_print(f"Ошибка при обработке блока: {err}")
        
        return cutouts

    def _get_panel_dimensions(self, panel_block) -> Tuple[float, float]:
        """Определяет размеры панели по крайним точкам"""
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for entity in panel_block:
            if entity.dxftype() == 'LINE':
                points = [(entity.dxf.start.x, entity.dxf.start.y),
                         (entity.dxf.end.x, entity.dxf.end.y)]
                for x, y in points:
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
        
        if min_x != float('inf'):
            width = round(max_x - min_x, 1)
            height = round(max_y - min_y, 1)
            return width, height
        return None, None

    def _get_grooves(self, panel_block, origin_point) -> List[Groove]:
        """Получает данные о пазах панели"""
        grooves = []
        
        for entity in panel_block:
            if entity.dxftype() == 'INSERT' and entity.dxf.name.startswith('GROUP'):
                group_block = self.doc.blocks[entity.dxf.name]
                group_insert = (entity.dxf.insert.x, entity.dxf.insert.y)
                
                for e in group_block:
                    if e.dxftype() == 'LINE' and e.dxf.layer == 'PAZ_DEPTH8_0':
                        start_x = round(e.dxf.start.x + group_insert[0] + origin_point[0], 1)
                        start_y = round(e.dxf.start.y + group_insert[1] + origin_point[1], 1)
                        end_x = round(e.dxf.end.x + group_insert[0] + origin_point[0], 1)
                        end_y = round(e.dxf.end.y + group_insert[1] + origin_point[1], 1)
                        
                        grooves.append(Groove(
                            start=(start_x, start_y),
                            end=(end_x, end_y),
                            width=8.0,  # стандартная ширина паза
                            depth=8.0   # стандатная глубина паза
                        ))
        
        return grooves

    def _get_edge_cutouts(self, panel_block, panel_outline) -> List[Dict]:
        """Находит вырезы по краям панели"""
        cutouts = []
        tolerance = 0.1  # допуск для соединения линий
        
        # Собираем все короткие линии
        short_lines = []
        for entity in panel_block:
            if entity.dxftype() == 'LINE':
                start = (round(abs(entity.dxf.start[0]), 2), round(entity.dxf.start[1], 2))
                end = (round(abs(entity.dxf.end[0]), 2), round(entity.dxf.end[1], 2))
                length = ((end[0]-start[0])**2 + (end[1]-start[1])**2)**0.5
                
                # Если линия короче основных сторон панели
                if length < min([line['length'] for line in panel_outline]):
                    short_lines.append({'start': start, 'end': end, 'length': length})
        
        # Объединяем поледовательные линии
        connected_lines = []
        current_line = None
        
        for line in sorted(short_lines, key=lambda x: (x['start'][0], x['start'][1])):
            if not current_line:
                current_line = line
                continue
            
            # Если конец текущей линии совпадает с началом следующей
            if (abs(current_line['end'][0] - line['start'][0]) <= tolerance and
                abs(current_line['end'][1] - line['start'][1]) <= tolerance):
                # Объединяем линии
                current_line = {
                    'start': current_line['start'],
                    'end': line['end'],
                    'length': current_line['length'] + line['length']
                }
            else:
                connected_lines.append(current_line)
                current_line = line
        
        if current_line:
            connected_lines.append(current_line)
        
        # Определяем радиусы скругления
        for i in range(len(connected_lines)-1):
            line1 = connected_lines[i]
            line2 = connected_lines[i+1]
            
            # Если линии перпендикулярны
            v1 = (line1['end'][0]-line1['start'][0], line1['end'][1]-line1['start'][1])
            v2 = (line2['end'][0]-line2['start'][0], line2['end'][1]-line2['start'][1])
            if abs(v1[0]*v2[0] + v1[1]*v2[1]) <= tolerance:  # скалярное произведение близко к 0
                radius = min(line1['length'], line2['length']) / 2
                cutouts.append({
                    'type': 'edge',
                    'start': line1['start'],
                    'corner': line1['end'],
                    'end': line2['end'],
                    'radius': round(radius, 2)
                })
        
        return cutouts

    def _get_panel_outline(self, panel_block) -> List[List[float]]:
        """Находит осноной прямоугольник панели по самым длинным линиям"""
        lines = []
        
        for entity in panel_block:
            if entity.dxftype() == 'LINE':
                start = (round(abs(entity.dxf.start[0]), 2), round(entity.dxf.start[1], 2))
                end = (round(abs(entity.dxf.end[0]), 2), round(entity.dxf.end[1], 2))
                length = ((end[0]-start[0])**2 + (end[1]-start[1])**2)**0.5
                lines.append({'start': start, 'end': end, 'length': length})
        
        # Сортируем по длине и берем 4 самые длинные линии
        longest_lines = sorted(lines, key=lambda x: x['length'], reverse=True)[:4]
        return longest_lines

    def _get_inner_cutouts(self, panel_block, panel_outline) -> List[Dict]:
        """Находит вырезы внутри панели"""
        cutouts = []
        
        # Находим замкнутые полилинии внутри панели
        for entity in panel_block:
            if entity.dxftype() in ['POLYLINE', 'LWPOLYLINE']:
                points = []
                if hasattr(entity, 'vertices'):
                    points = [(round(abs(v.dxf.location[0]), 2), round(v.dxf.location[1], 2)) 
                             for v in entity.vertices]
                elif hasattr(entity, 'get_points'):
                    points = [(round(abs(p[0]), 2), round(p[1], 2)) 
                             for p in entity.get_points()]
                
                if points and len(points) > 2:
                    # Проверяем, что все точки внутри панели
                    panel_bounds = {
                        'min_x': min(l['start'][0] for l in panel_outline),
                        'max_x': max(l['end'][0] for l in panel_outline),
                        'min_y': min(l['start'][1] for l in panel_outline),
                        'max_y': max(l['end'][1] for l in panel_outline)
                    }
                    
                    is_inner = all(
                        panel_bounds['min_x'] < p[0] < panel_bounds['max_x'] and
                        panel_bounds['min_y'] < p[1] < panel_bounds['max_y']
                        for p in points
                    )
                    
                    if is_inner:
                        cutouts.append({
                            'type': 'inner',
                            'points': points
                        })
        
        return cutouts

    def _get_panel_contour(self, panel_block) -> Dict:
        """Находит основной контур панели"""
        lines = []
        
        self._debug_print("\nПоиск контура панели:")
        
        # Ищем блок с контуром (обычно в GROUP33_1 в слое ABF_CUTTINGLINES)
        for entity in panel_block:
            if entity.dxftype() == 'INSERT':
                self._debug_print(f"Проверяем блок: {entity.dxf.name}")
                block = self.doc.blocks[entity.dxf.name]
                
                for e in block:
                    self._debug_print(f"Сущность: {e.dxftype()} в слое {e.dxf.layer}")
                    
                    # Ищем в слое ABF_CUTTINGLINES
                    if e.dxf.layer == 'ABF_CUTTINGLINES':
                        if e.dxftype() == 'POLYLINE':
                            self._debug_print("Найдена полилиния контура")
                            # Собираем все точки полилинии
                            points = []
                            for vertex in e.vertices:
                                x = round(abs(vertex.dxf.location[0]), 2)
                                y = round(vertex.dxf.location[1], 2)
                                points.append((x, y))
                            
                            # Создаем линии из точек
                            for i in range(len(points)):
                                start = points[i]
                                end = points[(i + 1) % len(points)]  # закольцовываем на первую точку
                                length = ((end[0]-start[0])**2 + (end[1]-start[1])**2)**0.5
                                lines.append({
                                    'start': start,
                                    'end': end,
                                    'length': round(length, 2)
                                })
                                self._debug_print(f"Добавлена линия контура: {start} -> {end}")
        
        if not lines:
            raise ValueError("Не найден контур панели!")
            
        # Находим размеры панели
        x_coords = [p[0] for line in lines for p in [line['start'], line['end']]]
        y_coords = [p[1] for line in lines for p in [line['start'], line['end']]]
        
        width = round(max(x_coords) - min(x_coords), 2)
        height = round(max(y_coords) - min(y_coords), 2)
        
        self._debug_print(f"Найден контур: {width}x{height}")
        return {'width': width, 'height': height, 'lines': lines}

    # ... остальые вспомогательные методы (_get_holes, _get_grooves, _get_edges, etc.)
