#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор зображень з темною темою для DNIPRO_PARSER
Базується на gener_im_1_G.py та gener_im_full.py
"""
import os
import sys
import argparse
from pathlib import Path

# Додаємо поточну директорію в шлях
sys.path.append(str(Path(__file__).parent))

# Імпортуємо оригінальні модулі
from gener_im_1_G import ImageRenderer as OriginalRenderer, DataProcessor, FontManager, log
from gener_im_full import render_single_date as original_render_single_date, get_dates_to_generate, log as log_full

# Темна конфігурація
class DarkTheme:
    """Темна тема для зображень"""
    
    # Розміри (такі ж як в оригіналі)
    CELL_W = 44
    CELL_H = 36
    LEFT_COL_W = 160
    SPACING = 60
    HEADER_SPACING = 45
    LEGEND_H = 80
    HOUR_ROW_H = 70
    HEADER_H = 34
    RIGHT_TITLE_PADDING = 12
    RIGHT_TITLE_RADIUS = 20
    RIGHT_TITLE_EXTRA_H = 10
    
    # Шрифти
    TITLE_FONT_PATH = "C:/Windows/Fonts/segoeui.ttf"
    FONT_PATH = "C:/Windows/Fonts/segoeui.ttf"
    if not os.path.exists(TITLE_FONT_PATH):
        TITLE_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    TITLE_FONT_SIZE = 36
    HOUR_FONT_SIZE = 15
    DATE_FONT_SIZE = 20
    SMALL_FONT_SIZE = 16
    LEGEND_FONT_SIZE = 16
    
    # Покращені темні кольори з кращим контрастом
    BG = (18, 18, 18)                   # Глибокий чорний фон
    TABLE_BG = (33, 33, 33)             # Темно-сірий фон таблиці
    GRID_COLOR = (120, 120, 120)        # Світліші лінії для кращої видимості
    TEXT_COLOR = (255, 255, 255)        # Чисто білий текст
    HIGHLIGHT_COLOR = (0, 0, 0)         # Чорний текст для виділення
    HIGHLIGHT_BG = (255, 193, 7)        # Яскравий жовтий фон
    HIGHLIGHT_BORDER = (255, 255, 255)  # Біла рамка
    OUTAGE_COLOR = (244, 67, 54)        # Яскравий червоний (немає світла)
    POSSIBLE_COLOR = (255, 193, 7)      # Яскравий жовтий (можливе відключення)
    AVAILABLE_COLOR = (76, 175, 80)     # Яскравий зелений (є світло)
    HEADER_BG = (44, 44, 44)            # Темно-сірий заголовок
    FOOTER_COLOR = (200, 200, 200)      # Світло-сірий футер
    LEGEND_BG = (28, 28, 28)            # Темно-сірий фон легенди
    
    # Інше
    TIMEZONE = "Europe/Kyiv"
    OUTPUT_SCALE = 3

def apply_dark_theme_to_full_generator():
    """Застосувати темну тему до повного генератора"""
    import gener_im_full as full_gen
    
    # Замінюємо кольори
    full_gen.BG = DarkTheme.BG
    full_gen.TABLE_BG = DarkTheme.TABLE_BG
    full_gen.GRID_COLOR = DarkTheme.GRID_COLOR
    full_gen.TEXT_COLOR = DarkTheme.TEXT_COLOR
    full_gen.OUTAGE_COLOR = DarkTheme.OUTAGE_COLOR
    full_gen.POSSIBLE_COLOR = DarkTheme.POSSIBLE_COLOR
    full_gen.AVAILABLE_COLOR = DarkTheme.AVAILABLE_COLOR
    full_gen.HEADER_BG = DarkTheme.HEADER_BG
    full_gen.FOOTER_COLOR = DarkTheme.FOOTER_COLOR

def generate_dark_individual_images(json_path: str):
    """Генерувати темні зображення для окремих груп"""
    processor = DataProcessor()
    data = processor.load_json_data(json_path)
    groups = processor.get_groups_from_data(data)
    
    for group in groups:
        log(f"▶ Генерую темне зображення для {group}…")
        
        # Створюємо рендерер з темною темою
        renderer = DarkImageRenderer(data, Path(json_path), group)
        renderer.render()

def generate_dark_full_images(json_path: str):
    """Генерувати темні повні зображення"""
    # Застосовуємо темну тему
    apply_dark_theme_to_full_generator()
    
    # Імпортуємо після застосування теми
    from gener_im_full import render, load_latest_json
    
    log_full("▶️ Генерую темні повні зображення")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
        
        render(data, Path(json_path))
        log_full("✅ Темні повні зображення згенеровано")
        
    except Exception as e:
        log_full(f"❌ Помилка генерації темних зображень: {e}")
        raise

class DarkImageRenderer:
    """Рендерер з темною темою"""
    
    def __init__(self, data: dict, json_path: Path, group_name: str):
        self.data = data
        self.json_path = json_path
        self.group_name = group_name
        self.font_manager = FontManager()
        self.processor = DataProcessor()
    
    def render(self):
        """Рендерити зображення з темною темою"""
        try:
            day_keys = self.processor.get_dates_for_display(self.data)
            
            # Створення зображення
            img = self._create_base_image(day_keys)
            draw = self._get_draw(img)
            
            # Малювання компонентів з темною темою
            self._draw_header(draw)
            self._draw_hours_header(draw, day_keys)
            self._draw_dates_column(draw, day_keys)
            self._draw_data_cells(draw, day_keys)
            self._draw_grid(draw, day_keys)
            self._draw_legend(draw, day_keys)
            self._draw_footer(draw)
            
            # Збереження
            self._save_image(img)
            
        except Exception as e:
            log(f"Помилка рендерингу темного зображення для групи {self.group_name}: {e}")
            raise
    
    def _create_base_image(self, day_keys: list):
        """Створити базове зображення"""
        from PIL import Image
        
        n_hours = 24
        n_rows = len(day_keys)
        
        width = (DarkTheme.SPACING * 2 + DarkTheme.LEFT_COL_W + 
                n_hours * DarkTheme.CELL_W)
        height = (DarkTheme.SPACING * 2 + DarkTheme.HEADER_H + 
                 DarkTheme.HOUR_ROW_H + n_rows * DarkTheme.CELL_H + 
                 DarkTheme.LEGEND_H + 40 + DarkTheme.HEADER_SPACING)
        
        return Image.new("RGB", (width, height), DarkTheme.BG)
    
    def _get_draw(self, img):
        """Отримати об'єкт для малювання"""
        from PIL import ImageDraw
        return ImageDraw.Draw(img)
    
    def _draw_header(self, draw):
        """Малювати заголовок"""
        font_title = self.font_manager.get_font(DarkTheme.TITLE_FONT_SIZE, bold=True)
        
        # Лівий заголовок
        left_title = "Графік відключень:"
        draw.text((DarkTheme.SPACING, DarkTheme.SPACING), left_title, 
                 fill=DarkTheme.TEXT_COLOR, font=font_title)
        
        # Правий заголовок з темним фоном
        self._draw_right_header(draw, font_title)
    
    def _draw_right_header(self, draw, font):
        """Малювати правий заголовок"""
        right_title = f"Черга {self.group_name.replace('GPV', '')}"
        bbox_right = draw.textbbox((0, 0), right_title, font=font)
        w_right = bbox_right[2] - bbox_right[0]
        h_right = bbox_right[3] - bbox_right[1]
        
        # Фон
        x0_bg = (DarkTheme.SPACING * 2 + DarkTheme.LEFT_COL_W + 24 * DarkTheme.CELL_W - 
                DarkTheme.SPACING - w_right - 2 * DarkTheme.RIGHT_TITLE_PADDING)
        y0_bg = DarkTheme.SPACING
        x1_bg = DarkTheme.SPACING * 2 + DarkTheme.LEFT_COL_W + 24 * DarkTheme.CELL_W - DarkTheme.SPACING
        y1_bg = DarkTheme.SPACING + h_right + DarkTheme.RIGHT_TITLE_EXTRA_H
        
        draw.rounded_rectangle([x0_bg, y0_bg, x1_bg, y1_bg], 
                             radius=DarkTheme.RIGHT_TITLE_RADIUS, 
                             fill=DarkTheme.HIGHLIGHT_BG, 
                             outline=DarkTheme.HIGHLIGHT_BORDER, 
                             width=2)
        
        # Текст
        center_x = x0_bg + (x1_bg - x0_bg) / 2
        center_y = y0_bg + (y1_bg - y0_bg) / 2
        draw.text((center_x, center_y), right_title, 
                 fill=DarkTheme.HIGHLIGHT_COLOR, font=font, anchor="mm")
    
    def _draw_hours_header(self, draw, day_keys):
        """Малювати рядок з годинами"""
        n_rows = len(day_keys)
        table_x0 = DarkTheme.SPACING
        table_y0 = (DarkTheme.SPACING + DarkTheme.HEADER_H + 
                   DarkTheme.HOUR_ROW_H + DarkTheme.HEADER_SPACING)
        
        hour_y0 = DarkTheme.SPACING + DarkTheme.HEADER_H + DarkTheme.HEADER_SPACING
        hour_y1 = hour_y0 + DarkTheme.HOUR_ROW_H
        
        font_hour = self.font_manager.get_font(DarkTheme.HOUR_FONT_SIZE)
        
        for h in range(24):
            x0 = table_x0 + DarkTheme.LEFT_COL_W + h * DarkTheme.CELL_W
            x1 = x0 + DarkTheme.CELL_W
            draw.rectangle([x0, hour_y0, x1, hour_y1], 
                          fill=DarkTheme.HEADER_BG, outline=DarkTheme.GRID_COLOR)
            
            # Формат часу в одну строку
            next_hour = (h + 1) % 24
            hour_text = f"{h:02d}-{next_hour:02d}"
            
            bbox = draw.textbbox((0, 0), hour_text, font=font_hour)
            w_text = bbox[2] - bbox[0]
            h_text = bbox[3] - bbox[1]
            
            # Центрируем текст
            text_x = x0 + (DarkTheme.CELL_W - w_text) / 2
            text_y = hour_y0 + (DarkTheme.HOUR_ROW_H - h_text) / 2
            
            draw.text((text_x, text_y), hour_text, fill=DarkTheme.TEXT_COLOR, font=font_hour)
    
    def _draw_dates_column(self, draw, day_keys):
        """Малювати колонку з датами"""
        table_x0 = DarkTheme.SPACING
        table_y0 = (DarkTheme.SPACING + DarkTheme.HEADER_H + 
                   DarkTheme.HOUR_ROW_H + DarkTheme.HEADER_SPACING)
        
        # Заголовок
        draw.rectangle([table_x0, table_y0 - DarkTheme.HOUR_ROW_H, 
                       table_x0 + DarkTheme.LEFT_COL_W, table_y0], 
                      fill=DarkTheme.HEADER_BG, outline=DarkTheme.GRID_COLOR)
        
        font_date = self.font_manager.get_font(DarkTheme.DATE_FONT_SIZE)
        header_text = "Дата"
        bbox_header = draw.textbbox((0, 0), header_text, font=font_date)
        w_header = bbox_header[2] - bbox_header[0]
        h_header = bbox_header[3] - bbox_header[1]
        
        draw.text((table_x0 + (DarkTheme.LEFT_COL_W - w_header) / 2,
                  table_y0 - DarkTheme.HOUR_ROW_H + (DarkTheme.HOUR_ROW_H - h_header) / 2),
                 header_text, fill=DarkTheme.TEXT_COLOR, font=font_date)
        
        # Дати
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        for r, day_key in enumerate(day_keys):
            y0 = table_y0 + r * DarkTheme.CELL_H
            draw.rectangle([table_x0, y0, table_x0 + DarkTheme.LEFT_COL_W, y0 + DarkTheme.CELL_H], 
                          fill=DarkTheme.TABLE_BG, outline=DarkTheme.GRID_COLOR)
            
            dt = datetime.fromtimestamp(int(day_key), ZoneInfo(DarkTheme.TIMEZONE))
            date_label = f"{dt.day} грудня"
            bbox = draw.textbbox((0, 0), date_label, font=font_date)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            
            draw.text((table_x0 + (DarkTheme.LEFT_COL_W - w) / 2, 
                      y0 + (DarkTheme.CELL_H - h) / 2), 
                     date_label, fill=DarkTheme.TEXT_COLOR, font=font_date)
    
    def _draw_data_cells(self, draw, day_keys):
        """Малювати клітинки з даними"""
        table_x0 = DarkTheme.SPACING
        table_y0 = (DarkTheme.SPACING + DarkTheme.HEADER_H + 
                   DarkTheme.HOUR_ROW_H + DarkTheme.HEADER_SPACING)
        
        fact = self.data.get("fact", {})
        
        for r, day_key in enumerate(day_keys):
            y0 = table_y0 + r * DarkTheme.CELL_H
            day_map = fact["data"][day_key]
            gp_hours = day_map.get(self.group_name, {})
            
            for h in range(24):
                h_key = str(h+1)
                state = gp_hours.get(h_key, "yes")
                
                x0 = table_x0 + DarkTheme.LEFT_COL_W + h * DarkTheme.CELL_W
                x1 = x0 + DarkTheme.CELL_W
                
                # Отримуємо колір для стану
                color = self._get_color_for_state(state)
                
                draw.rectangle([x0, y0, x1, y0 + DarkTheme.CELL_H], 
                              fill=color, outline=DarkTheme.GRID_COLOR)
    
    def _draw_grid(self, draw, day_keys):
        """Малювати сітку"""
        n_rows = len(day_keys)
        table_x0 = DarkTheme.SPACING
        table_y0 = (DarkTheme.SPACING + DarkTheme.HEADER_H + 
                   DarkTheme.HOUR_ROW_H + DarkTheme.HEADER_SPACING)
        table_x1 = table_x0 + DarkTheme.LEFT_COL_W + 24 * DarkTheme.CELL_W
        table_y1 = table_y0 + n_rows * DarkTheme.CELL_H
        
        # Вертикальні лінії
        for i in range(25):
            x = table_x0 + DarkTheme.LEFT_COL_W + i * DarkTheme.CELL_W
            draw.line([(x, table_y0 - DarkTheme.HOUR_ROW_H), (x, table_y1)], 
                     fill=DarkTheme.GRID_COLOR)
        
        # Горизонтальні лінії
        for r in range(n_rows + 1):
            y = table_y0 + r * DarkTheme.CELL_H
            draw.line([(table_x0, y), (table_x1, y)], 
                     fill=DarkTheme.GRID_COLOR)
    
    def _draw_legend(self, draw, day_keys):
        """Малювати легенду"""
        n_rows = len(day_keys)
        table_y1 = (DarkTheme.SPACING + DarkTheme.HEADER_H + 
                   DarkTheme.HOUR_ROW_H + DarkTheme.HEADER_SPACING + 
                   n_rows * DarkTheme.CELL_H)
        
        legend_states = ["yes", "no", "maybe"]
        legend_items = []
        for state in legend_states:
            color = self._get_color_for_state(state)
            description = self._get_description_for_state(state)
            legend_items.append((color, description, state))
        
        legend_y = table_y1 + 15
        box_size = 20
        gap = 20
        x_cursor = DarkTheme.SPACING
        
        font_legend = self.font_manager.get_font(DarkTheme.LEGEND_FONT_SIZE)
        
        # Рамка легенди
        legend_padding = 10
        total_width = 0
        for col, text, state in legend_items:
            text_bbox = draw.textbbox((0, 0), text, font=font_legend)
            w_text = text_bbox[2] - text_bbox[0]
            total_width += box_size + 6 + w_text + gap
        total_width -= gap
        
        legend_box_x0 = x_cursor - legend_padding
        legend_box_y0 = legend_y - legend_padding
        legend_box_x1 = x_cursor + total_width + legend_padding
        legend_box_y1 = legend_y + box_size + legend_padding
        
        # Темна рамка легенди
        draw.rounded_rectangle([legend_box_x0, legend_box_y0, legend_box_x1, legend_box_y1], 
                             radius=8, fill=DarkTheme.LEGEND_BG, outline=DarkTheme.GRID_COLOR, width=2)
        
        for col, text, state in legend_items:
            text_bbox = draw.textbbox((0, 0), text, font=font_legend)
            w_text = text_bbox[2] - text_bbox[0]
            block_w = box_size + 6 + w_text
            
            # Квадрат з рамкою
            draw.rectangle([x_cursor, legend_y, x_cursor + box_size, legend_y + box_size], 
                          fill=col, outline=DarkTheme.GRID_COLOR, width=2)
            
            # Текст
            text_x = x_cursor + box_size + 6
            text_y = legend_y + box_size // 2
            
            draw.text((text_x, text_y), text, fill=DarkTheme.TEXT_COLOR, font=font_legend, anchor="lm")
            x_cursor += block_w + gap
    
    def _draw_footer(self, draw):
        """Малювати футер"""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        fact = self.data.get("fact", {})
        pub_text = (fact.get("update") or 
                   self.data.get("lastUpdated") or 
                   datetime.now(ZoneInfo(DarkTheme.TIMEZONE)).strftime("%d.%m.%Y"))
        
        pub_label = f"Опубліковано {pub_text}"
        font_small = self.font_manager.get_font(DarkTheme.SMALL_FONT_SIZE)
        bbox_pub = draw.textbbox((0, 0), pub_label, font=font_small)
        w_pub = bbox_pub[2] - bbox_pub[0]
        
        width = DarkTheme.SPACING * 2 + DarkTheme.LEFT_COL_W + 24 * DarkTheme.CELL_W
        legend_bottom = (DarkTheme.SPACING + DarkTheme.HEADER_H + DarkTheme.HOUR_ROW_H + 
                        DarkTheme.HEADER_SPACING + len(self.processor.get_dates_for_display(self.data)) * DarkTheme.CELL_H + 
                        DarkTheme.LEGEND_H)
        
        draw.text((width - w_pub - DarkTheme.SPACING, legend_bottom - 20), 
                 pub_label, fill=DarkTheme.FOOTER_COLOR, font=font_small)
    
    def _save_image(self, img):
        """Зберегти зображення"""
        from PIL import Image
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        safe_group_name = self.group_name.replace('GPV', '').replace('.', '-')
        current_date = datetime.now(ZoneInfo(DarkTheme.TIMEZONE)).strftime("%Y-%m-%d")
        
        # Базова директорія
        BASE = Path(__file__).parent.parent.absolute()
        OUT_DIR = BASE / "out/images"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        
        out_name = OUT_DIR / f"gpv-{safe_group_name}-emergency-dark-{current_date}.png"
        
        img_resized = img.resize((img.width * DarkTheme.OUTPUT_SCALE, 
                                img.height * DarkTheme.OUTPUT_SCALE), 
                               resample=Image.LANCZOS)
        img_resized.save(out_name, optimize=True)
        log(f"Збережено темне зображення: {out_name}")
    
    def _get_color_for_state(self, state: str) -> tuple:
        """Отримати колір для стану"""
        color_map = {
            "yes": DarkTheme.AVAILABLE_COLOR,
            "no": DarkTheme.OUTAGE_COLOR,
            "maybe": DarkTheme.POSSIBLE_COLOR,
            "first": DarkTheme.OUTAGE_COLOR,
            "second": DarkTheme.OUTAGE_COLOR,
            "mfirst": DarkTheme.POSSIBLE_COLOR,
            "msecond": DarkTheme.POSSIBLE_COLOR
        }
        return color_map.get(state, DarkTheme.AVAILABLE_COLOR)
    
    def _get_description_for_state(self, state: str) -> str:
        """Отримати опис стану"""
        preset = self.data.get("preset", {})
        time_type = preset.get("time_type", {})
        descriptions = {
            "yes": "Світло є",
            "no": "Світла немає", 
            "maybe": "Можливе відключення",
            "first": "Світла не буде перші 30 хв.",
            "second": "Світла не буде другі 30 хв.",
            "mfirst": "Світла можливо не буде перші 30 хв.",
            "msecond": "Світла можливо не буде другі 30 хв."
        }
        return time_type.get(state, descriptions.get(state, "Невідомий стан"))

def main():
    """Головна функція"""
    parser = argparse.ArgumentParser(description="Генерація темних зображень")
    parser.add_argument("--type", choices=["individual", "full", "both"], default="both",
                       help="Тип зображень для генерації")
    parser.add_argument("--json", help="Шлях до JSON файлу")
    
    args = parser.parse_args()
    
    # Знаходимо JSON файл
    if args.json:
        json_path = args.json
    else:
        BASE = Path(__file__).parent.parent.absolute()
        JSON_DIR = BASE / "out"
        json_files = sorted(JSON_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not json_files:
            log("❌ JSON файли не знайдено")
            sys.exit(1)
        json_path = str(json_files[0])
    
    log(f"🌙 Генерую темні зображення з {json_path}")
    
    try:
        if args.type in ["individual", "both"]:
            generate_dark_individual_images(json_path)
        
        if args.type in ["full", "both"]:
            generate_dark_full_images(json_path)
        
        log("✅ Темні зображення згенеровано успішно")
        
    except Exception as e:
        log(f"❌ Помилка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()