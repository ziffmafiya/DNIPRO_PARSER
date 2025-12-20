#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрая отправка графиков в Telegram одной командой
"""
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent / "src"))

from telegram_notify import send_photo, send_message

def quick_send():
    """Быстро отправить последний общий график с статистикой"""
    images_dir = Path("out/images")
    
    # Ищем последний общий график
    today_images = list(images_dir.glob("*today*.png"))
    
    if not today_images:
        print("❌ Общий график не найден!")
        print("💡 Сначала сгенерируйте график: python src/gener_im_full.py")
        return
    
    # Берем самый новый файл
    latest_image = max(today_images, key=lambda f: f.stat().st_mtime)
    
    print(f"📤 Отправляю: {latest_image.name}")
    
    # Отправляем с полной статистикой
    caption = "🔌 <b>График отключений электроэнергии</b>\n"
    caption += "📍 Дніпро • ЦЕК\n"
    caption += "⏰ Актуальная информация"
    
    send_photo(str(latest_image), caption, with_stats=True)
    print("✅ График отправлен в Telegram!")

if __name__ == "__main__":
    quick_send()