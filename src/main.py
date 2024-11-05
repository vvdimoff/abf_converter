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
        
        for panel_data in panels_data:
            builder = PanelBuilder(panel_data)
            json_data = builder.build()
            print(json.dumps(json_data, indent=2))

if __name__ == "__main__":
    main()