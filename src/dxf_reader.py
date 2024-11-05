import ezdxf
from typing import List, Tuple, Dict
from geometry import Hole, Groove

class DxfReader:
    STANDARD_OFFSET = 8.415  # Стандартный отступ кромки в мм

    def __init__(self, filename: str):
        self.filename = filename
        self.doc = None

    def read(self) -> List[Dict]:
        """Читает DXF файл и возвращает данные всех панелей"""
        self.doc = ezdxf.readfile(self.filename)
        return self.get_panels_data()

    def get_panels_data(self) -> List[Dict]:
        """Получает данные о всех панелях"""
        panels_data = []
        thickness_block = next(
            (block for block in self.doc.blocks if block.name == 'THICKNESS_18'), 
            None
        )
        
        if thickness_block:
            for panel in self._get_panel_blocks(thickness_block):
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
        """Анализирует отдельную панель"""
        panel_block = self.doc.blocks[panel.dxf.name]
        dimensions = self._get_panel_dimensions(panel_block)
        origin_point = (round(panel.dxf.insert.x, 1), round(panel.dxf.insert.y, 1))
        
        width = dimensions[0] if dimensions else None
        height = dimensions[1] if dimensions else None
        
        return {
            "name": panel.dxf.name,
            "size": {
                "width": width,
                "height": height,
                "thickness": 18.0
            },
            "origin_point": origin_point,
            "holes": self._get_holes(panel_block, origin_point) or [],
            "grooves": self._get_grooves(panel_block, origin_point) or [],
            "edges": self._get_edges(panel_block, origin_point, width, height) or [],
            "cutouts": self._get_cutouts(panel_block, origin_point) or []
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
        """Выводит структуру DXF файла"""
        # Анализ слоев
        for layer in self.doc.layers:
            print(f"\n[{layer.dxf.name}]")
            blocks_in_layer = []
            
            # Анализ блоков в слое
            for block in self.doc.blocks:
                if block.name.startswith('_'):  # Пропускаем служебные блоки
                    continue
                
                has_entities = False
                instances = []
                lines = []
                
                # Анализ содержимого блока
                for entity in block:
                    if entity.dxf.layer == layer.dxf.name:
                        has_entities = True
                        if entity.dxftype() == 'INSERT':
                            instances.append((
                                round(entity.dxf.insert.x, 1),
                                round(entity.dxf.insert.y, 1)
                            ))
                        elif entity.dxftype() == 'LINE':
                            lines.append((
                                (round(entity.dxf.start.x, 1), round(entity.dxf.start.y, 1)),
                                (round(entity.dxf.end.x, 1), round(entity.dxf.end.y, 1))
                            ))
                
                if has_entities:
                    blocks_in_layer.append({
                        'name': block.name,
                        'instances': instances,
                        'lines': lines
                    })
            
            if blocks_in_layer:
                print(f"  Blocks: {len(blocks_in_layer)}")
                for block in blocks_in_layer:
                    print(f"    Block {block['name']}:")
                    if block['instances']:
                        print(f"      Instances: {len(block['instances'])}")
                        for pos in block['instances'][:2]:  # Показываем только первые 2
                            print(f"        at ({pos[0]}, {pos[1]})")
                        if len(block['instances']) > 2:
                            print(f"        ... and {len(block['instances'])-2} more")
                    
                    if block['lines']:
                        print(f"      Lines: {len(block['lines'])}")
                        for start, end in block['lines'][:2]:  # Показываем только первые 2
                            print(f"        {start} → {end}")
                        if len(block['lines']) > 2:
                            print(f"        ... and {len(block['lines'])-2} more lines")

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
        """Выводит подробный анализ файла"""
        self.doc = ezdxf.readfile(self.filename)
        
        # Выводим структуру файла
        print("\nСтруктура DXF файла:")
        self._print_file_structure()
        
        # Анализируем панели
        panels_data = self.get_panels_data()
        print(f"\nНайдено панелей: {len(panels_data)}")
        
        for panel in panels_data:
            print(f"\nПанель: {panel['name']}")
            print(f"  Размеры: {panel['size']['width']}x{panel['size']['height']}x{panel['size']['thickness']} мм")
            print(f"  Точка вставки: {panel['origin_point']}")
            
            # Выводим информацию об элементах
            if panel['holes']:
                print(f"  Отверстия ({len(panel['holes'])}):")
                for hole in panel['holes']:
                    print(f"    - D{hole['diameter']} мм, глубина {hole['depth']} мм в точке {hole['center']}")
            
            if panel['grooves']:
                print(f"  Пазы ({len(panel['grooves'])}):")
                for groove in panel['grooves']:
                    print(f"    - {groove['width']}x{groove['depth']} мм от {groove['start']} до {groove['end']}")
            
            if panel['edges']:
                print(f"  Кромки ({len(panel['edges'])}):")
                for edge in panel['edges']:
                    print(f"    - Толщина {edge['thickness']} мм")

    def _get_edges(self, panel_block, origin_point, panel_width, panel_height):
        """Получает данные о кромках панели"""
        edges = []
        
        for entity in panel_block:
            if entity.dxftype() == 'INSERT' and entity.dxf.name.startswith('GROUP'):
                group_block = self.doc.blocks[entity.dxf.name]
                group_insert = (entity.dxf.insert.x, entity.dxf.insert.y)
                
                for e in group_block:
                    if e.dxf.layer == 'ABF_EDGEBANDING' and e.dxftype() == 'POLYLINE':
                        vertices = list(e.vertices)
                        if len(vertices) == 4:  # треугольник (замкнутый)
                            # Абсолютные координаты
                            tip_x = round(vertices[0].dxf.location[0] + group_insert[0] + origin_point[0], 1)
                            tip_y = round(vertices[0].dxf.location[1] + group_insert[1] + origin_point[1], 1)
                            base1_x = round(vertices[1].dxf.location[0] + group_insert[0] + origin_point[0], 1)
                            base1_y = round(vertices[1].dxf.location[1] + group_insert[1] + origin_point[1], 1)
                            base2_x = round(vertices[2].dxf.location[0] + group_insert[0] + origin_point[0], 1)
                            base2_y = round(vertices[2].dxf.location[1] + group_insert[1] + origin_point[1], 1)
                            
                            # Определяем сторону панели по абсолютным координатам
                            # Для отрицательных координат используем abs()
                            x, y = abs(tip_x), tip_y
                            if abs(x - panel_width) < 20:  # правый край
                                side = "right"
                            elif abs(x) < 20:  # левый край
                                side = "left"
                            elif abs(y) < 20:  # нижний край
                                side = "bottom"
                            elif abs(y - panel_height) < 20:  # верхний край
                                side = "top"
                            else:
                                side = "unknown"
                            
                            edges.append({
                                'thickness': 1.0,
                                'side': side,
                                'coordinates': {
                                    'tip': (tip_x, tip_y),
                                    'base1': (base1_x, base1_y),
                                    'base2': (base2_x, base2_y)
                                }
                            })
        
        return edges

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
                            depth=8.0   # стандартная глубина паза
                        ))
        
        return grooves

    def _get_cutouts(self, panel_block, origin_point) -> List[Dict]:
        """Получает данные о вырезах панели"""
        # Пока возвращаем пустой список, реализацию добавим позже
        return []

    # ... остальные вспомогательные методы (_get_holes, _get_grooves, _get_edges, etc.)
