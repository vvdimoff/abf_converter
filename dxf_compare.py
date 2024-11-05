import ezdxf
import sys
from typing import Tuple, List, Dict

class DXFComparator:
    def __init__(self, file1: str, file2: str):
        """
        Инициализация компаратора с двумя DXF файлами
        file1: путь к первому файлу (панель без кромки)
        file2: путь ко второму файлу (панель с кромкой)
        """
        self.doc1 = ezdxf.readfile(file1)
        self.doc2 = ezdxf.readfile(file2)
        
    def compare_entities(self) -> None:
        """Сравнивает сущности в обоих файлах"""
        print("\nФайл 1:")
        self.analyze_edgebanding(self.doc1)
        print("\nФайл 2:")
        self.analyze_edgebanding(self.doc2)
        
        print("\nСравнение сущностей:")
        
        entities1 = self._get_all_entities(self.doc1)
        entities2 = self._get_all_entities(self.doc2)
        
        print(f"\nКоличество сущностей:")
        print(f"Файл 1: {len(entities1)}")
        print(f"Файл 2: {len(entities2)}")
        
        print("\nНовые сущности во втором файле:")
        for entity in entities2:
            if not self._entity_exists(entity, entities1):
                print(f"\nТип: {entity.dxftype()}")
                print(f"Слой: {entity.dxf.layer}")
                
                # Основные атрибуты
                for attr in ['color', 'linetype', 'lineweight', 'thickness']:
                    if hasattr(entity.dxf, attr):
                        print(f"{attr}: {getattr(entity.dxf, attr)}")
                
                # Специфичные атрибуты для разных типов сущностей
                if entity.dxftype() == 'POLYLINE':
                    print("Атрибуты полилинии:")
                    if hasattr(entity, 'vertices'):
                        print("  Вершины:")
                        for vertex in entity.vertices:
                            print(f"    {vertex.dxf.location}")
                    elif hasattr(entity, 'points'):
                        print("  Точки:")
                        for point in entity.points:
                            print(f"    {point}")
                    for attr in ['start_width', 'end_width', 'extrusion', 'mode']:
                        if hasattr(entity.dxf, attr):
                            print(f"  {attr}: {getattr(entity.dxf, attr)}")
                    if hasattr(entity.dxf, 'flags'):
                        print(f"  Флаги: {entity.dxf.flags}")
                    if hasattr(entity.dxf, 'elevation'):
                        print(f"  Высота: {entity.dxf.elevation}")
                    
                elif entity.dxftype() == 'INSERT':
                    print("Атрибуты вставки:")
                    print(f"  Имя блока: {entity.dxf.name}")
                    print(f"  Точка вставки: {entity.dxf.insert}")
                    print(f"  Масштаб: ({entity.dxf.xscale}, {entity.dxf.yscale}, {entity.dxf.zscale})")
                    print(f"  Поворот: {entity.dxf.rotation}")
                    
                    # Проверяем блок, на который ссылается вставка
                    if entity.dxf.name in self.doc2.blocks:
                        block = self.doc2.blocks[entity.dxf.name]
                        print(f"  Содержимое блока:")
                        for block_entity in block:
                            print(f"    - {block_entity.dxftype()} на слое {block_entity.dxf.layer}")
                
                # Проеряем владельца
                if hasattr(entity.dxf, 'owner'):
                    owner_handle = entity.dxf.owner
                    print(f"Владелец (handle): {owner_handle}")
                    
                print("-" * 50)

    def _get_all_entities(self, doc) -> List:
        """Получает все сущности из документа"""
        entities = []
        
        # Сущности из modelspace
        for entity in doc.modelspace():
            entities.append(entity)
        
        # Сущности из блоков
        for block in doc.blocks:
            for entity in block:
                entities.append(entity)
                
        return entities
    
    def _entity_exists(self, entity, entity_list) -> bool:
        """Проверяет, существует ли сущность в списке"""
        for e in entity_list:
            if self._entities_match(e, entity):
                return True
        return False
    
    def _entities_match(self, e1, e2) -> bool:
        """Проверяет, совпадают ли две сущности"""
        if e1.dxftype() != e2.dxftype():
            return False
            
        # Сраввиваем основные атрибуты
        attrs = ['layer', 'color', 'linetype']
        for attr in attrs:
            if hasattr(e1.dxf, attr) and hasattr(e2.dxf, attr):
                if getattr(e1.dxf, attr) != getattr(e2.dxf, attr):
                    return False
                    
        return True

    def analyze_dimensions(self, doc):
        """Анализирует размеры в слоях"""
        print("\nАнализ размеров:")
        
        def get_block_bounds(block):
            bounds = {'min_x': float('inf'), 'min_y': float('inf'),
                     'max_x': float('-inf'), 'max_y': float('-inf')}
            
            for entity in block:
                if entity.dxftype() == 'LINE':
                    # Проверяем только линии на z=0
                    if entity.dxf.start[2] == 0 and entity.dxf.end[2] == 0:
                        bounds['min_x'] = min(bounds['min_x'], entity.dxf.start[0], entity.dxf.end[0])
                        bounds['max_x'] = max(bounds['max_x'], entity.dxf.start[0], entity.dxf.end[0])
                        bounds['min_y'] = min(bounds['min_y'], entity.dxf.start[1], entity.dxf.end[1])
                        bounds['max_y'] = max(bounds['max_y'], entity.dxf.start[1], entity.dxf.end[1])
            return bounds
        
        # Ищем блок с линиями
        for block in doc.blocks:
            if block.name.startswith('_______'):
                bounds = get_block_bounds(block)
                width = abs(bounds['max_x'] - bounds['min_x'])
                length = abs(bounds['max_y'] - bounds['min_y'])
                print(f"\nРазмеры из блока {block.name}:")
                print(f"  Ширина: {width:.1f} мм")
                print(f"  Длина: {length:.1f} мм")

    def analyze_edgebanding(self, doc):
        """Анализирует все треугольники кромки"""
        print("\nТреугольники кромки:")
        for block in doc.blocks:
            if block.name.startswith('GROUP'):
                for entity in block:
                    if entity.dxf.layer == 'ABF_EDGEBANDING' and entity.dxftype() == 'POLYLINE':
                        vertices = list(entity.vertices)
                        tip = vertices[0].dxf.location
                        base1 = vertices[1].dxf.location
                        base2 = vertices[2].dxf.location
                        print(f"\nТреугольник в блоке {block.name}:")
                        print(f"  Вершина: ({tip[0]:.2f}, {tip[1]:.2f})")
                        print(f"  Ос��ование: ({base1[0]:.2f}, {base1[1]:.2f}) - ({base2[0]:.2f}, {base2[1]:.2f})")

    def get_block_bounds(self, block):
        """Получает границы блока"""
        bounds = {'min_x': float('inf'), 'min_y': float('inf'),
                 'max_x': float('-inf'), 'max_y': float('-inf')}
        
        for entity in block:
            if entity.dxftype() == 'LINE':
                # Проверяем только линии на z=0
                if entity.dxf.start[2] == 0 and entity.dxf.end[2] == 0:
                    bounds['min_x'] = min(bounds['min_x'], entity.dxf.start[0], entity.dxf.end[0])
                    bounds['max_x'] = max(bounds['max_x'], entity.dxf.start[0], entity.dxf.end[0])
                    bounds['min_y'] = min(bounds['min_y'], entity.dxf.start[1], entity.dxf.end[1])
                    bounds['max_y'] = max(bounds['max_y'], entity.dxf.start[1], entity.dxf.end[1])
        return bounds

    def analyze_panel(self, doc, name=""):
        """Анализирует панель"""
        print(f"\nАнализ панели {name}:")
        
        # Список всех слоев
        print("\nСлои в документе:")
        for layer in doc.layers:
            print(f"- {layer.dxf.name}")
        
        # Размеры из блока
        for block in doc.blocks:
            if block.name.startswith('_______'):
                bounds = self.get_block_bounds(block)
                width = abs(bounds['max_x'] - bounds['min_x'])
                length = abs(bounds['max_y'] - bounds['min_y'])
                print(f"\nРазмеры реза (из блока {block.name}):")
                print(f"  Ширина: {width:.1f} мм")
                print(f"  Длина: {length:.1f} мм")
        
        # Анализ содержимого блоков
        print("\nАнализ блоков:")
        for block in doc.blocks:
            if block.name.startswith('GROUP'):
                print(f"\nБлок {block.name}:")
                for entity in block:
                    if entity.dxf.layer == 'ABF_EDGEBANDING':
                        print(f"- {entity.dxftype()} в слое ABF_EDGEBANDING")
                        if entity.dxftype() == 'POLYLINE':
                            vertices = list(entity.vertices)
                            print(f"  Вершины ({len(vertices)}):")
                            for vertex in vertices:
                                print(f"        {vertex.dxf.location}")

    def compare_raw_files(self, doc1, doc2):
        """Сравнивает сырые данные DXF файлов"""
        print("\nСравнение файлов:")
        
        # Сравниваем слои
        layers1 = set(layer.dxf.name for layer in doc1.layers)
        layers2 = set(layer.dxf.name for layer in doc2.layers)
        
        print("\nРазница в слоях:")
        print("Добавлены:", layers2 - layers1)
        print("Удалены:", layers1 - layers2)
        
        # Сравниваем блоки
        blocks1 = {block.name: block for block in doc1.blocks if not block.name.startswith('*')}
        blocks2 = {block.name: block for block in doc2.blocks if not block.name.startswith('*')}
        
        print("\nРазница в блоках:")
        print("Добавлены:", set(blocks2.keys()) - set(blocks1.keys()))
        print("Удалены:", set(blocks1.keys()) - set(blocks2.keys()))
        
        # Сравниваем содержимое одинаковых блоков
        common_blocks = set(blocks1.keys()) & set(blocks2.keys())
        print("\nИзменения в общих блоках:")
        for name in common_blocks:
            block1 = blocks1[name]
            block2 = blocks2[name]
            
            entities1 = [(e.dxftype(), e.dxf.layer) for e in block1]
            entities2 = [(e.dxftype(), e.dxf.layer) for e in block2]
            
            if entities1 != entities2:
                print(f"\nБлок {name}:")
                print("  Файл 1:", entities1)
                print("  Файл 2:", entities2)
        
        # Детальный анализ блоков с размерами
        print("\nДетальный анализ блоков с размерами:")
        for doc, name in [(doc1, "Файл 1"), (doc2, "Файл 2")]:
            print(f"\n{name}:")
            for block in doc.blocks:
                if block.name.startswith('_______'):
                    print(f"\nБлок {block.name}:")
                    for entity in block:
                        print(f"- {entity.dxftype()} в слое {entity.dxf.layer}")
                        if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                            print(f"  start: {entity.dxf.start}")
                            print(f"  end: {entity.dxf.end}")
        
        # Детальный анализ GROUP блоков
        print("\nДетальный анализ GROUP блоков:")
        for doc, name in [(doc1, "Файл 1"), (doc2, "Файл 2")]:
            print(f"\n{name}:")
            for block in doc.blocks:
                if block.name.startswith('GROUP'):
                    print(f"\nБлок {block.name}:")
                    for entity in block:
                        if entity.dxf.layer == 'ABF_EDGEBANDING':
                            print(f"- {entity.dxftype()} в слое {entity.dxf.layer}")
                            if entity.dxftype() == 'POLYLINE':
                                vertices = list(entity.vertices)
                                print(f"  Вершины ({len(vertices)}):")
                                for vertex in vertices:
                                    print(f"    {vertex.dxf.location}")

    def compare_files(self):
        """Сравнивает оба файла"""
        self.compare_raw_files(self.doc1, self.doc2)

    def analyze_edgebanding_triangles(self, doc):
        """Анализирует все треугольники кромки"""
        print("\nАнализ треугольников кромки:")
        width = 861.92  # ширина панели
        height = 679.00  # высота панели
        
        for block in doc.blocks:
            if block.name.startswith('GROUP'):
                for entity in block:
                    if entity.dxf.layer == 'ABF_EDGEBANDING' and entity.dxftype() == 'POLYLINE':
                        vertices = list(entity.vertices)
                        tip = vertices[0].dxf.location
                        x, y = tip[0], tip[1]
                        
                        # Определяем сторону панели
                        if abs(x) < 20:  # левый край
                            side = "левый"
                            offset = abs(x)
                        elif abs(x + width) < 20:  # правый край
                            side = "правый"
                            offset = abs(x + width)
                        elif abs(y) < 20:  # нижний край
                            side = "нижний"
                            offset = abs(y)
                        elif abs(y - height) < 20:  # верхний край
                            side = "верхний"
                            offset = abs(y - height)
                        else:
                            side = "неизвестно"
                            offset = 0
                        
                        print(f"\nТреугольник в блоке {block.name}:")
                        print(f"  Сторона: {side}")
                        print(f"  Отступ от края: {offset:.2f} мм")

    def find_all_edgebanding(self, doc):
        """Ищет все треугольники кромки во всех блоках"""
        print("\nВсе треугольники кромки:")
        for block in doc.blocks:
            if block.name.startswith('GROUP'):
                for entity in block:
                    if entity.dxf.layer == 'ABF_EDGEBANDING' and entity.dxftype() == 'POLYLINE':
                        vertices = list(entity.vertices)
                        if len(vertices) == 4:  # треугольник (замкнутый)
                            tip = vertices[0].dxf.location
                            base1 = vertices[1].dxf.location
                            base2 = vertices[2].dxf.location
                            print(f"\nТреугольник в блоке {block.name}:")
                            print(f"  Вершина: ({tip[0]:.2f}, {tip[1]:.2f})")
                            print(f"  Основание: ({base1[0]:.2f}, {base1[1]:.2f}) - ({base2[0]:.2f}, {base2[1]:.2f})")

    def compare_edgebanding_triangles(self, doc1, doc2):
        """Сравнивает треугольники кромки в двух файлах"""
        print("\nСравнение треугольников кромки:")
        
        def find_triangles(doc):
            triangles = []
            for block in doc.blocks:
                if block.name.startswith('GROUP'):
                    for entity in block:
                        if entity.dxf.layer == 'ABF_EDGEBANDING' and entity.dxftype() == 'POLYLINE':
                            vertices = list(entity.vertices)
                            if len(vertices) == 4:
                                triangles.append({
                                    'block': block.name,
                                    'tip': vertices[0].dxf.location,
                                    'base1': vertices[1].dxf.location,
                                    'base2': vertices[2].dxf.location
                                })
            return triangles
        
        triangles1 = find_triangles(doc1)
        triangles2 = find_triangles(doc2)
        
        print("\nФайл 1 (кромка 1.0 мм):")
        for t in triangles1:
            print(f"\nБлок {t['block']}:")
            print(f"  Вершина: ({t['tip'][0]:.3f}, {t['tip'][1]:.3f})")
            print(f"  Основание: ({t['base1'][0]:.3f}, {t['base1'][1]:.3f}) - ({t['base2'][0]:.3f}, {t['base2'][1]:.3f})")
        
        print("\nФайл 2 (кромка 0.8 мм):")
        for t in triangles2:
            print(f"\nБлок {t['block']}:")
            print(f"  Вершина: ({t['tip'][0]:.3f}, {t['tip'][1]:.3f})")
            print(f"  Основание: ({t['base1'][0]:.3f}, {t['base1'][1]:.3f}) - ({t['base2'][0]:.3f}, {t['base2'][1]:.3f})")

    def compare_raw_dxf(self, doc1, doc2):
        """Детальное сравнение сырых DXF файлов"""
        print("\nДетальное сравнение DXF:")
        
        # Сравнение всех сущностей в каждом блоке
        for block_name in set(b.name for b in doc1.blocks) | set(b.name for b in doc2.blocks):
            block1 = doc1.blocks.get(block_name)
            block2 = doc2.blocks.get(block_name)
            
            if block1 and block2:
                entities1 = [(e.dxftype(), e.dxf.layer, getattr(e, 'dxf_attrib_exists', lambda x: False)('location') and e.dxf.location) for e in block1]
                entities2 = [(e.dxftype(), e.dxf.layer, getattr(e, 'dxf_attrib_exists', lambda x: False)('location') and e.dxf.location) for e in block2]
                
                if entities1 != entities2:
                    print(f"\nРазличия в блоке {block_name}:")
                    if len(entities1) != len(entities2):
                        print(f"  Разное количество элементов: {len(entities1)} vs {len(entities2)}")
                    
                    for i, (e1, e2) in enumerate(zip(entities1, entities2)):
                        if e1 != e2:
                            print(f"  Элемент {i}:")
                            print(f"    Файл 1: {e1}")
                            print(f"    Файл 2: {e2}")
        
        # Сравнение всех атрибутов в моделях
        print("\nСравнение атрибутов моделей:")
        for attr in dir(doc1.header):
            if not attr.startswith('_'):
                val1 = getattr(doc1.header, attr)
                val2 = getattr(doc2.header, attr)
                if val1 != val2:
                    print(f"  {attr}: {val1} -> {val2}")

def main():
    if len(sys.argv) != 3:
        print("Использование: python dxf_compare.py file1.dxf file2.dxf")
        sys.exit(1)
        
    file1, file2 = sys.argv[1], sys.argv[2]
    comparator = DXFComparator(file1, file2)
    comparator.compare_files()

if __name__ == "__main__":
    main() 