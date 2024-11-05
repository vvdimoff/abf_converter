import sys
import json
from dxf_reader import DxfReader
from panel_builder import PanelBuilder

def main():
    if len(sys.argv) < 2:
        print("Укажите путь к DXF файлу")
        return

    reader = DxfReader(sys.argv[1])
    
    # Режим анализа с флагом -a
    if len(sys.argv) > 2 and sys.argv[2] == '-a':
        print(f"\nОткрываем файл: {sys.argv[1]}")
        reader.analyze_and_log()
    else:
        # Обычный режим - создание JSON
        panels_data = reader.read()
        
        for panel in panels_data:
            print_panel_info(panel)

def print_panel_info(panel_data):
    """Выводит краткую информацию о панели"""
    print(f"\nПанель {panel_data['name']}:")
    print(f"  {panel_data['size']['width']}x{panel_data['size']['height']}x{panel_data['size']['thickness']} мм")
    
    if panel_data['cutouts']:
        print("  Вырезы:")
        for cutout in panel_data['cutouts']:
            print(f"    - Точки: {cutout['entry_points']}")
            if cutout['radius']:
                print(f"      Радиус: {cutout['radius']} мм")

if __name__ == "__main__":
    main()