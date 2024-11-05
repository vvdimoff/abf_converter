from dxf_analyzer import DXFAnalyzer
from panel_builder import PanelBuilder
import json

def main():
    filename = "panel2.dxf"
    
    # Анализируем DXF файл
    analyzer = DXFAnalyzer(filename)
    analyzer.analyze_file_structure()
    dxf_data = analyzer.analyze()
    
    # Выводим иерархию
    analyzer.print_hierarchy()
    
    # Выводим анализ специальных слоев
    analyzer.analyze_special_layers()
    
    # Добавляем анализ свойств
    analyzer.analyze_block_properties()
    
    # Создаем панель
    builder = PanelBuilder(dxf_data)
    panel = builder.build()
    
    # Выводим JSON
    print("\nJSON представление панели:")
    print(json.dumps(panel.to_dict(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()