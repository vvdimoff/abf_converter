from PIL import Image, ImageDraw
from dxf_reader import Panel

def create_panel_image(panel: Panel) -> Image.Image:
    print(f"Создаем изображение панели")
    print(f"Линий контура: {len(panel.front_face)}")
    
    # Находим границы
    all_points = []
    for start, end in panel.front_face:
        all_points.extend([start, end])
    
    if not all_points:
        print("Нет точек для отображения")
        return Image.new('RGB', (800, 600), 'white')
    
    # Находим границы
    min_x = min(x for x, _ in all_points)
    max_x = max(x for x, _ in all_points)
    min_y = min(y for _, y in all_points)
    max_y = max(y for _, y in all_points)
    
    # Добавляем отступы
    padding = 50
    width = int(max_x - min_x + 2 * padding)
    height = int(max_y - min_y + 2 * padding)
    
    print(f"Границы изображения: X({min_x}, {max_x}), Y({min_y}, {max_y})")
    print(f"Размер изображения: {width}x{height}")
    
    # Создаем изображение
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    def transform(x, y):
        return (
            int(x - min_x + padding),
            int(height - (y - min_y + padding))
        )
    
    # Функция для рисования стрелки
    def draw_arrow(draw, start, end, color='red', width=2, arrow_size=15):
        # Рисуем основную линию
        draw.line([start, end], fill=color, width=width)
        
        # Вычисляем направление стрелки
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = (dx*dx + dy*dy)**0.5
        
        if length > 0:
            # Нормализуем направление
            dx, dy = dx/length, dy/length
            
            # Вычисляем точки наконечника стрелки
            right = (
                end[0] - arrow_size * (dx*0.866 + dy*0.5),
                end[1] - arrow_size * (-dx*0.5 + dy*0.866)
            )
            left = (
                end[0] - arrow_size * (dx*0.866 - dy*0.5),
                end[1] - arrow_size * (dx*0.5 + dy*0.866)
            )
            
            # Рисуем наконечник
            draw.line([end, right], fill=color, width=width)
            draw.line([end, left], fill=color, width=width)
    
    # Рисуем контур черным цветом
    for start, end in panel.front_face:
        draw.line([transform(*start), transform(*end)], fill='black', width=2)
    
    # Рисуем стрелку направления текстуры
    arrow_length = 80  # увеличим длину стрелки
    start_x = panel.origin_point[0] + 40  # немного правее левого края
    start_y = panel.origin_point[1] + 40  # немного выше нижнего края
    end_x = start_x + arrow_length * panel.grain_direction[0]
    end_y = start_y + arrow_length * panel.grain_direction[1]
    
    # Рисуем стрелку с наконечником
    draw_arrow(
        draw,
        transform(start_x, start_y),
        transform(end_x, end_y),
        color='red',
        width=2,
        arrow_size=15
    )
    
    # Отмечаем origin_point зеленым кружком
    dot_radius = 5
    origin = transform(*panel.origin_point)
    draw.ellipse([
        origin[0] - dot_radius, origin[1] - dot_radius,
        origin[0] + dot_radius, origin[1] + dot_radius
    ], fill='green')
    
    # Рисуем отверстия синими кружками
    for hole in panel.holes:
        center = transform(*hole.center)
        radius = 5  # фиксированный размер для отображения
        draw.ellipse([
            center[0] - radius, center[1] - radius,
            center[0] + radius, center[1] + radius
        ], outline='blue', width=2)
        # Добавляем текст с размерами
        draw.text(
            (center[0] + radius + 5, center[1] - radius),
            f"⌀{hole.diameter}x{hole.depth}",
            fill='blue'
        )
    
    return image
