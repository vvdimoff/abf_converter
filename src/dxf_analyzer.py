import ezdxf
from typing import Dict, Any, List
from geometry import Hole, Groove  # Изменяем на абсолютный импорт без точки

class DXFAnalyzer:
    def __init__(self, filename: str):
        self.filename = filename
        self.doc = ezdxf.readfile(filename)
        self.layers_content = {}
    
    def analyze(self) -> Dict[str, Any]:
        """Анализирует DXF файл и возвращает структурированные данные"""
        self.layers_content = {}
        msp = self.doc.modelspace()
        
        def process_entity(entity, insert_offset=(0,0)):
            layer = entity.dxf.layer
            if layer not in self.layers_content:
                self.layers_content[layer] = {
                    'standalone': {
                        'circles': [],
                        'lines': set()
                    },
                    'blocks': {}
                }
            
            if entity.dxftype() == 'INSERT':
                self._process_insert(entity, insert_offset)
            elif entity.dxftype() == 'CIRCLE':
                self._process_circle(entity, layer, insert_offset)
            elif entity.dxftype() == 'LINE':
                self._process_line(entity, layer, insert_offset)
        
        for entity in msp:
            process_entity(entity)
        
        return self.layers_content
    
    def _process_insert(self, entity, insert_offset=(0,0)):
        """Обрабатывает вставку блока"""
        layer = entity.dxf.layer
        block_name = entity.dxf.name
        block = self.doc.blocks[block_name]
        
        # Инициализируем структуру для слоя
        if layer not in self.layers_content:
            self.layers_content[layer] = {
                'standalone': {'circles': [], 'lines': set()},
                'blocks': {}
            }
        
        # Получаем точку вставки с учетом смещения
        current_insert = (
            entity.dxf.insert.x + insert_offset[0],
            entity.dxf.insert.y + insert_offset[1]
        )
        
        # Обрабатываем содержимое блока
        for e in block:
            if e.dxftype() == 'INSERT':
                self._process_insert(e, current_insert)
            elif e.dxftype() == 'CIRCLE':
                self._process_circle(e, layer, current_insert)
            elif e.dxftype() == 'LINE':
                self._process_line(e, layer, current_insert)
    
    def _process_circle(self, entity, layer, offset):
        """Обрабатывает окружность"""
        center = (
            round(entity.dxf.center.x + offset[0], 1),
            round(entity.dxf.center.y + offset[1], 1)
        )
        
        if layer not in self.layers_content:
            self.layers_content[layer] = {
                'standalone': {'circles': [], 'lines': set()},
                'blocks': {}
            }
        
        self.layers_content[layer]['standalone']['circles'].append({
            'center': center,
            'radius': round(entity.dxf.radius, 1)
        })
    
    def _process_line(self, entity, layer, offset):
        """Обрабатывает линию"""
        start = (
            round(entity.dxf.start.x + offset[0], 1),
            round(entity.dxf.start.y + offset[1], 1)
        )
        end = (
            round(entity.dxf.end.x + offset[0], 1),
            round(entity.dxf.end.y + offset[1], 1)
        )
        
        if layer not in self.layers_content:
            self.layers_content[layer] = {
                'standalone': {'circles': [], 'lines': set()},
                'blocks': {}
            }
        
        if start != end:  # Пропускаем нулевые линии
            self.layers_content[layer]['standalone']['lines'].add((start, end))
    
    def _process_block_line(self, entity, layer, block_name, offset):
        """Обрабатывает линию внутри блока"""
        start = (
            round(entity.dxf.start.x + offset[0], 1),
            round(entity.dxf.start.y + offset[1], 1)
        )
        end = (
            round(entity.dxf.end.x + offset[0], 1),
            round(entity.dxf.end.y + offset[1], 1)
        )
        if start != end:
            self.layers_content[layer]['blocks'][block_name]['lines'].add((start, end))

    def _process_block_circle(self, entity, layer, block_name, offset):
        """Обрабатывает окружность внутри блока"""
        center = (
            round(entity.dxf.center.x + offset[0], 1),
            round(entity.dxf.center.y + offset[1], 1)
        )
        self.layers_content[layer]['blocks'][block_name]['circles'].append({
            'center': center,
            'radius': round(entity.dxf.radius, 1),
            'layer': entity.dxf.layer  # Добавляем слой окружности
        })
    
    def print_structure(self):
        """Выводит структуру DXF файла"""
        print(f"\nAnalyzing file: {self.filename}\n")
        print("DXF Structure:")
        
        for layer in sorted(self.layers_content.keys()):
            content = self.layers_content[layer]
            has_content = (
                content['standalone']['circles'] or 
                content['standalone']['lines'] or 
                content['blocks']
            )
            if has_content:
                print(f"\n[{layer}]")
                self._print_standalone_entities(content['standalone'])
                self._print_blocks(content['blocks'])
    
    def _print_standalone_entities(self, standalone):
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
    
    def _print_blocks(self, blocks):
        if blocks:
            print(f"  Blocks: {len(blocks)}")
            for block_name, block in blocks.items():
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
    
    def analyze_special_layers(self):
        """Анализирует специальные слои и блоки (отверстия и пазы)"""
        print("\nSpecial Elements Analysis:")
        
        # Анализ отверстий
        holes = []
        for layer_name, layer_content in self.layers_content.items():
            # Проверяем локи в слое
            for block_name, block in layer_content['blocks'].items():
                if block_name.startswith('GROUP'):
                    # Если в блоке есть окружности, это может быть отверстие
                    if block['circles']:
                        for circle in block['circles']:
                            holes.append(f"  Block {block_name}: "
                                       f"center=({circle['center'][0]:.1f}, {circle['center'][1]:.1f}), "
                                       f"r={circle['radius']:.1f}")
        
        if holes:
            print("\nHoles found in blocks:")
            for hole in sorted(holes):
                print(hole)
        else:
            print("\nNo holes found")
        
        # Анализ пазов
        grooves = []
        for layer_name, layer_content in self.layers_content.items():
            # Проверяем блоки в слое
            for block_name, block in layer_content['blocks'].items():
                if block_name.startswith('GROUP'):
                    # Если в боке есть линии, это может быть паз
                    if block['lines']:
                        lines_count = len(block['lines'])
                        if lines_count == 4:  # Типичный паз состоит из 4 линий
                            # Получаем точку ставки блока
                            insert_point = block['instances'][0] if block['instances'] else (0, 0)
                            grooves.append(f"  Block {block_name}: "
                                         f"at ({insert_point[0]:.1f}, {insert_point[1]:.1f}), "
                                         f"lines={lines_count}")
        
        if grooves:
            print("\nPotential grooves found in blocks:")
            for groove in sorted(grooves):
                print(groove)
        else:
            print("\nNo grooves found")
        
        # Анализ имен блоков
        print("\nBlock name analysis:")
        block_prefixes = set()
        for layer_name, layer_content in self.layers_content.items():
            for block_name in layer_content['blocks'].keys():
                prefix = block_name.split('_')[0] if '_' in block_name else block_name
                block_prefixes.add(prefix)
        
        print("Found block types:")
        for prefix in sorted(block_prefixes):
            print(f"  - {prefix}")
    
    def print_hierarchy(self):
        """Выводит иерархическое представление DXF файла"""
        print("\nDXF Hierarchy:")
        print("└── Layers")
        
        for layer_name in sorted(self.layers_content.keys()):
            layer = self.layers_content[layer_name]
            print(f"    ├── [{layer_name}]")
            
            # Выводим блоки в слое
            if layer['blocks']:
                print("    │   ├── Blocks")
                for block_name, block in layer['blocks'].items():
                    print(f"    │   │   ├─ {block_name}")
                    
                    # Block references
                    if block.get('block_references'):
                        print(f"    │   │   │   ├── References:")
                        for ref in sorted(block['block_references']):
                            print(f"    │   │   │   │   ├── {ref}")
                    
                    # Instances
                    if block['instances']:
                        print(f"    │   │   │   ├── Instances ({len(block['instances'])})")
                        for pos in block['instances'][:2]:
                            print(f"    │   │   │   │   ├── at ({pos[0]:.1f}, {pos[1]:.1f})")
                        if len(block['instances']) > 2:
                            print(f"    │   │   │   │   └── ... and {len(block['instances'])-2} more")
                    
                    # Circles in block
                    if block['circles']:
                        print(f"    │   │   │   ├── Circles ({len(block['circles'])})")
                        for circle in block['circles'][:2]:
                            print(f"    │   │   │      ├── center=({circle['center'][0]:.1f}, {circle['center'][1]:.1f}), r={circle['radius']:.1f}")
                        if len(block['circles']) > 2:
                            print(f"    │   │   │      └── ... and {len(block['circles'])-2} more")
                    
                    # Lines in block
                    if block['lines']:
                        print(f"    │   │   │   └── Lines ({len(block['lines'])})")
                        for start, end in list(block['lines'])[:2]:
                            print(f"    │   │   │       ├── ({start[0]:.1f}, {start[1]:.1f}) → ({end[0]:.1f}, {end[1]:.1f})")
                        if len(block['lines']) > 2:
                            print(f"    │   │   │       └── ... and {len(block['lines'])-2} more")
            
            # Выводим отдельные сущности в слое
            standalone = layer['standalone']
            if standalone['circles'] or standalone['lines']:
                print("    │   └── Standalone Entities")
                
                if standalone['circles']:
                    print(f"    │       ├── Circles ({len(standalone['circles'])})")
                    for circle in standalone['circles'][:2]:
                        print(f"    │       │   ├── center=({circle['center'][0]:.1f}, {circle['center'][1]:.1f}), r={circle['radius']:.1f}")
                    if len(standalone['circles']) > 2:
                        print(f"    │       │   └── ... and {len(standalone['circles'])-2} more")
                
                if standalone['lines']:
                    print(f"    │       └── Lines ({len(standalone['lines'])})")
                    for start, end in list(standalone['lines'])[:2]:
                        print(f"    │           ├── ({start[0]:.1f}, {start[1]:.1f}) → ({end[0]:.1f}, {end[1]:.1f})")
                    if len(standalone['lines']) > 2:
                        print(f"    │           └── ... and {len(standalone['lines'])-2} more")
    
    def analyze_block_names(self):
        """Анализирует имена блоков для определения их типов"""
        print("\nBlock Types Analysis:")
        
        block_types = {
            'GROUP': [],
            'PAZ': [],
            'DEPTH': [],
            'Other': []
        }
        
        for layer_name, layer_content in self.layers_content.items():
            for block_name in layer_content['blocks'].keys():
                if block_name.startswith('GROUP'):
                    block_types['GROUP'].append(block_name)
                elif 'PAZ' in block_name:
                    block_types['PAZ'].append(block_name)
                elif 'DEPTH' in block_name:
                    block_types['DEPTH'].append(block_name)
                else:
                    block_types['Other'].append(block_name)
        
        for type_name, blocks in block_types.items():
            if blocks:
                print(f"\n{type_name} blocks:")
                for block in sorted(blocks):
                    print(f"  - {block}")
    
    def analyze_block_properties(self):
        """Анализрует своства блоков и хх атрибуты"""
        print("\nDetailed Block Analysis:")
        
        for layer_name, layer_content in self.layers_content.items():
            print(f"\nLayer: [{layer_name}]")
            for block_name, block in layer_content.get('blocks', {}).items():
                print(f"\n  Block: {block_name}")
                
                # Выводим все свойства блока
                for prop_name, prop_value in block.items():
                    if prop_name not in ['lines', 'circles', 'instances']:
                        print(f"    {prop_name}: {prop_value}")
                
                # Анализируем блок на наличие атрибутов
                if hasattr(block, 'dxf'):
                    print("    DXF Attributes:")
                    for attr_name in dir(block.dxf):
                        if not attr_name.startswith('_'):
                            try:
                                value = getattr(block.dxf, attr_name)
                                if not callable(value):
                                    print(f"      {attr_name}: {value}")
                            except:
                                pass
                
                # Проверяем нличие вложенных блоков
                if 'block_references' in block:
                    print("    Block References:")
                    for ref in block['block_references']:
                        print(f"      - {ref}")
    
    def analyze_file_structure(self):
        """Анализирует структуру DXF файла"""
        print("\nАнализ структуры DXF файла:")
        
        # Аниз сов
        for layer in self.doc.layers:
            print(f"\nСлой: {layer.dxf.name}")
            print(f"  Цвет: {layer.dxf.color}")
            print(f"  Линтип: {layer.dxf.linetype}")
        
        # Анализ блоков
        print("\nАнализ блоков:")
        for block in self.doc.blocks:
            print(f"\nБлок: {block.name}")
            if block.name.startswith('_'):  # Пропускаем служебные блоки
                continue
                
            # Ищем родительский блок
            print("  Родительский блок:", end=" ")
            for parent in self.doc.blocks:
                for entity in parent:
                    if entity.dxftype() == 'INSERT' and entity.dxf.name == block.name:
                        print(parent.name)
                        break
            
            # нализируем содержимое блока
            for entity in block:
                if entity.dxftype() == 'INSERT':
                    print(f"  Вставка блока: {entity.dxf.name}")
                elif entity.dxftype() == 'LINE':
                    print(f"  Линия: {entity.dxf.start} -> {entity.dxf.end}")
        
        # Поиск и анализ панелей
        thickness_block = next(
            (block for block in self.doc.blocks if block.name == 'THICKNESS_18'), 
            None
        )
        
        if thickness_block:
            panel_blocks = [
                entity for entity in thickness_block 
                if entity.dxftype() == 'INSERT' and entity.dxf.name.startswith('_______')
            ]
            print(f"\nНайдено панелей: {len(panel_blocks)}")
            
            for panel in panel_blocks:
                print(f"\nПанель: {panel.dxf.name}")
                panel_block = self.doc.blocks[panel.dxf.name]
                
                # Получаем точку вставки панели
                insert_point = (panel.dxf.insert.x, panel.dxf.insert.y)
                
                # Анализируем размеры панели
                panel_dimensions = self._get_panel_dimensions(panel_block)
                if panel_dimensions:
                    print(f"  Размеры: {panel_dimensions[0]}x{panel_dimensions[1]} мм")
                    print(f"  Точка вставки: ({insert_point[0]:.1f}, {insert_point[1]:.1f})")
                
                # Инициализируем структуру для элементов панели
                panel_elements = {
                    'holes': [],
                    'grooves': [],
                    'groups': set()
                }
                
                # Собираем элементы панели
                for entity in panel_block:
                    if entity.dxftype() == 'INSERT':
                        if entity.dxf.name.startswith('GROUP'):
                            panel_elements['groups'].add(entity.dxf.name)
                            group_block = self.doc.blocks[entity.dxf.name]
                            
                            # Анализируем содержимое группы
                            for e in group_block:
                                if e.dxftype() == 'CIRCLE':
                                    layer = e.dxf.layer
                                    if 'DEPTH' in layer:
                                        center = (
                                            round(e.dxf.center.x + insert_point[0], 1),
                                            round(e.dxf.center.y + insert_point[1], 1)
                                        )
                                        panel_elements['holes'].append({
                                            'center': center,
                                            'radius': round(e.dxf.radius, 1),
                                            'layer': layer
                                        })
                                elif e.dxftype() == 'LINE' and e.dxf.layer == 'PAZ_DEPTH8_0':
                                    start = (
                                        round(e.dxf.start.x + insert_point[0], 1),
                                        round(e.dxf.start.y + insert_point[1], 1)
                                    )
                                    end = (
                                        round(e.dxf.end.x + insert_point[0], 1),
                                        round(e.dxf.end.y + insert_point[1], 1)
                                    )
                                    panel_elements['grooves'].append((start, end))
                
                # Анализируем отверстия
                holes_by_type = {}
                for hole in panel_elements['holes']:
                    hole_type = self._classify_hole(hole['layer'], hole['radius'])
                    if hole_type not in holes_by_type:
                        holes_by_type[hole_type] = []
                    holes_by_type[hole_type].append(hole)
                
                if holes_by_type:
                    print("  Отверстия по типам:")
                    for hole_type, holes in holes_by_type.items():
                        print(f"    {hole_type} ({len(holes)}):")
                        for hole in holes:
                            print(f"      - center={hole['center']}, r={hole['radius']}")
                
                if panel_elements['grooves']:
                    print(f"  Пазы ({len(panel_elements['grooves'])}):")
                    for groove in panel_elements['grooves']:
                        print(f"    - {groove[0]} → {groove[1]}")
                
                if panel_elements['groups']:
                    print(f"  группы и их содержимое:")
                    for group_name in sorted(panel_elements['groups']):
                        group_block = self.doc.blocks[group_name]
                        print(f"    {group_name}:")
                        
                        # Подсчитываем элементы в группе
                        circles = sum(1 for e in group_block if e.dxftype() == 'CIRCLE')
                        lines = sum(1 for e in group_block if e.dxftype() == 'LINE')
                        
                        if circles:
                            print(f"      - Окружностей: {circles}")
                        if lines:
                            print(f"      - Линий: {lines}")

    def _get_panel_dimensions(self, panel_block):
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
            width = round(max_x - min_x)
            height = round(max_y - min_y)
            return width, height
        return None

    def _classify_hole(self, layer, radius):
        """Классифицирует отверстие по слою и радиусу"""
        if 'D8_0_DEPTHF' in layer:
            return 'Сквозное отверстие D8'
        elif 'D5_0_DEPTH8_0' in layer:
            return 'Отверстие D5 глубиной 8мм'
        else:
            return f'Отверстие D{round(radius*2)} ({layer})'

    def _analyze_element_positions(self, holes, grooves):
        """Анализирует взаимное расположение элементов"""
        results = []
        
        # Анализ расположения отверстий
        if len(holes) > 1:
            for i in range(len(holes)-1):
                for j in range(i+1, len(holes)):
                    h1, h2 = holes[i], holes[j]
                    dx = h2['center'][0] - h1['center'][0]
                    dy = h2['center'][1] - h1['center'][1]
                    distance = round(((dx**2 + dy**2)**0.5), 1)
                    
                    if distance < 50:  # Близко расположенные отверстия
                        results.append(
                            f"Отверстия на расстоянии {distance}мм: "
                            f"({h1['center']}) и ({h2['center']})"
                        )
        
        # Анализ пазов
        if grooves:
            # Находим параллельные пазы
            for i in range(len(grooves)-1):
                for j in range(i+1, len(grooves)):
                    g1, g2 = grooves[i], grooves[j]
                    if self._are_parallel(g1, g2):
                        results.append(
                            f"Параллельные пазы: {g1} и {g2}"
                        )
        
        return results

    def get_panels_data(self):
        """Подготавливает данные о панелях для panel_builder"""
        panels_data = []
        
        thickness_block = next(
            (block for block in self.doc.blocks if block.name == 'THICKNESS_18'), 
            None
        )
        
        if thickness_block:
            panel_blocks = [
                entity for entity in thickness_block 
                if entity.dxftype() == 'INSERT' and entity.dxf.name.startswith('_______')
            ]
            
            for panel in panel_blocks:
                panel_block = self.doc.blocks[panel.dxf.name]
                dimensions = self._get_panel_dimensions(panel_block)
                origin_point = (round(panel.dxf.insert.x, 1), round(panel.dxf.insert.y, 1))
                
                panel_data = {
                    "name": panel.dxf.name,
                    "width": dimensions[0] if dimensions else None,
                    "height": dimensions[1] if dimensions else None,
                    "origin_point": origin_point,
                    "holes": [],
                    "grooves": []
                }
                
                # Собираем отверстия и пазы из групп
                for entity in panel_block:
                    if entity.dxftype() == 'INSERT' and entity.dxf.name.startswith('GROUP'):
                        group_block = self.doc.blocks[entity.dxf.name]
                        group_insert = (entity.dxf.insert.x, entity.dxf.insert.y)
                        
                        for e in group_block:
                            if e.dxftype() == 'CIRCLE' and 'DEPTH' in e.dxf.layer:
                                # Абсолютные координаты = координаты элемента + вставка группы + вставка панели
                                center_x = round(e.dxf.center.x + group_insert[0] + origin_point[0], 1)
                                center_y = round(e.dxf.center.y + group_insert[1] + origin_point[1], 1)
                                
                                panel_data["holes"].append({
                                    "center": (center_x, center_y),
                                    "radius": round(e.dxf.radius, 1),
                                    "layer": e.dxf.layer
                                })
                            elif e.dxftype() == 'LINE' and e.dxf.layer == 'PAZ_DEPTH8_0':
                                # Абсолютные координаты для пазов
                                start_x = round(e.dxf.start.x + group_insert[0] + origin_point[0], 1)
                                start_y = round(e.dxf.start.y + group_insert[1] + origin_point[1], 1)
                                end_x = round(e.dxf.end.x + group_insert[0] + origin_point[0], 1)
                                end_y = round(e.dxf.end.y + group_insert[1] + origin_point[1], 1)
                                
                                panel_data["grooves"].append({
                                    "start": (start_x, start_y),
                                    "end": (end_x, end_y)
                                })
                
                panels_data.append(panel_data)
        
        return panels_data