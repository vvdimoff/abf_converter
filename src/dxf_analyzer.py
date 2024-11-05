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
    
    def _process_insert(self, entity, insert_offset=(0, 0)):
        """Обрабатывает вставку блока"""
        layer = entity.dxf.layer
        block_name = entity.dxf.name
        block = self.doc.blocks[block_name]
        
        # Инициализируем структуру для слоя, если её нет
        if layer not in self.layers_content:
            self.layers_content[layer] = {
                'standalone': {'circles': [], 'lines': set()},
                'blocks': {}
            }
        
        # Инициализируем структуру для блока, если её нет
        if block_name not in self.layers_content[layer]['blocks']:
            self.layers_content[layer]['blocks'][block_name] = {
                'instances': [],
                'circles': [],
                'lines': set(),
                'block_references': set(),
                'xdata': {}  # Добавляем xdata
            }
        
        # Сохраняем позицию вставки
        current_insert = (
            entity.dxf.insert.x + insert_offset[0],
            entity.dxf.insert.y + insert_offset[1]
        )
        self.layers_content[layer]['blocks'][block_name]['instances'].append(current_insert)
        
        # Сохраняем xdata если есть
        if hasattr(entity, 'xdata'):
            self.layers_content[layer]['blocks'][block_name]['xdata'] = entity.xdata
        
        # Обрабатываем содержимое блока
        for e in block:
            if e.dxftype() == 'INSERT':
                # Сохраняем ссылку на вложенный блок
                ref_name = e.dxf.name
                self.layers_content[layer]['blocks'][block_name]['block_references'].add(ref_name)
                
                # Проверяем атрибуты вставки
                if hasattr(e, 'attribs'):
                    for attrib in e.attribs:
                        if attrib.dxf.tag == 'HOLE_TYPE':
                            if 'special_refs' not in self.layers_content[layer]['blocks'][block_name]:
                                self.layers_content[layer]['blocks'][block_name]['special_refs'] = set()
                            self.layers_content[layer]['blocks'][block_name]['special_refs'].add(attrib.dxf.text)
                
                # роверяем расширенные данные
                if hasattr(e, 'xdata') and e.xdata:
                    for app_name, xdata_items in e.xdata.items():
                        for item in xdata_items:
                            if isinstance(item, str) and ('D' in item and '_DEPTH' in item):
                                if 'special_refs' not in self.layers_content[layer]['blocks'][block_name]:
                                    self.layers_content[layer]['blocks'][block_name]['special_refs'] = set()
                                self.layers_content[layer]['blocks'][block_name]['special_refs'].add(item)
                
                # Обрабатываем вложенный блок
                self._process_insert(e, current_insert)
            elif e.dxftype() == 'ATTRIB':
                # Сохраняем атрибуты блока
                self.layers_content[layer]['blocks'][block_name]['block_references'].add(e.dxf.text)
            elif e.dxftype() == 'LINE':
                self._process_block_line(e, layer, block_name, current_insert)
            elif e.dxftype() == 'CIRCLE':
                self._process_block_circle(e, layer, block_name, current_insert)
    
    def _process_circle(self, entity, layer, offset):
        center = (
            round(entity.dxf.center.x + offset[0], 1),
            round(entity.dxf.center.y + offset[1], 1)
        )
        self.layers_content[layer]['standalone']['circles'].append({
            'center': center,
            'radius': round(entity.dxf.radius, 1)
        })
    
    def _process_line(self, entity, layer, offset):
        start = (
            round(entity.dxf.start.x + offset[0], 1),
            round(entity.dxf.start.y + offset[1], 1)
        )
        end = (
            round(entity.dxf.end.x + offset[0], 1),
            round(entity.dxf.end.y + offset[1], 1)
        )
        if start != end:
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
            # Проверяем блоки в слое
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
                    # Если в блоке есть линии, это может быть паз
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
                            print(f"    │   │   │   │   ├── center=({circle['center'][0]:.1f}, {circle['center'][1]:.1f}), r={circle['radius']:.1f}")
                        if len(block['circles']) > 2:
                            print(f"    │   │   │   │   └── ... and {len(block['circles'])-2} more")
                    
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
        """Анализирует своства блоков и хх атрибуты"""
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
                
                # Проверяем наличие вложенных блоков
                if 'block_references' in block:
                    print("    Block References:")
                    for ref in block['block_references']:
                        print(f"      - {ref}")
    
    def analyze_file_structure(self):
        """Анализирует полную структуру DXF файла"""
        print("\nDetailed Block Analysis:")
        
        # Анализируем конкретные блоки с отверстиями
        hole_blocks = ['GROUP2_1', 'GROUP9_1']
        for block_name in hole_blocks:
            if block_name in self.doc.blocks:
                block = self.doc.blocks[block_name]
                print(f"\nAnalyzing block: {block_name}")
                
                # Анализируем каждую сущность в блоке
                for entity in block:
                    print(f"\n  Entity type: {entity.dxftype()}")
                    
                    # Выводим все атрибуты сущности
                    if hasattr(entity, 'dxf'):
                        print("  DXF attributes:")
                        for attr_name in dir(entity.dxf):
                            if not attr_name.startswith('_'):
                                try:
                                    value = getattr(entity.dxf, attr_name)
                                    if not callable(value):
                                        print(f"    {attr_name}: {value}")
                                except:
                                    pass
                    
                    # Проверяем на вложенные блоки
                    if entity.dxftype() == 'INSERT':
                        print(f"  Referenced block: {entity.dxf.name}")
                        # Анализируем атрибуты влоенного блока
                        if hasattr(entity, 'attribs'):
                            print("  Attributes:")
                            for attrib in entity.attribs:
                                print(f"    {attrib.dxf.tag}: {attrib.dxf.text}")
                    
                    # Проверяем на текст
                    if entity.dxftype() in ['TEXT', 'MTEXT', 'ATTRIB']:
                        print(f"  Text content: {entity.dxf.text}")
                    
                    # Проверяем на расширенные данные
                    if hasattr(entity, 'xdata') and entity.xdata:
                        print("  Extended Data:")
                        for app_name, xdata in entity.xdata.items():
                            print(f"    {app_name}: {xdata}")
    
    def _find_holes(self) -> List[Hole]:
        """Находит отверстия в блоках GROUP* по слою окружности"""
        holes = []
        
        for layer_content in self.layers_content.values():
            for block_name, block in layer_content.get('blocks', {}).items():
                if not block_name.startswith('GROUP'):
                    continue
                    
                # Проверяем есть ли окружности в блоке
                if block['circles']:
                    for circle in block['circles']:
                        # Получаем слой окружности
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
                            except (ValueError, IndexError):
                                print(f"Warning: Could not parse hole layer: {circle_layer}")
        
        return holes