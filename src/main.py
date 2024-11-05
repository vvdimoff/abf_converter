import sys
import argparse
from dxf_analyzer import DXFAnalyzer
from panel_builder import PanelBuilder

def main():
    # Создаем парсер аргументов
    parser = argparse.ArgumentParser(description='DXF файл анализатор и конвертер')
    parser.add_argument('file', help='Путь к DXF файлу')
    parser.add_argument('-a', '--analyze', action='store_true', 
                       help='Показать подробный анализ файла')
    
    args = parser.parse_args()
    
    try:
        # Инициализируем анализатор
        analyzer = DXFAnalyzer(args.file)
        
        if args.analyze:
            # Выводим подробный анализ
            analyzer.analyze_file_structure()
        else:
            # Получаем данные о панелях
            panels_data = analyzer.get_panels_data()
            
            # Создаем и выводим JSON
            builder = PanelBuilder(panels_data)
            print(builder.to_json())
            
    except Exception as e:
        print(f"Ошибка при обработке файла: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()