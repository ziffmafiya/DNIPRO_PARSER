#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Швидка відправка графіків в Telegram однією командою
"""
import sys
from pathlib import Path

# Додаємо src в шлях
sys.path.append(str(Path(__file__).parent / "src"))

from telegram_notify import send_photo, send_message

def quick_send():
    """Швидко відправити останній загальний графік зі статистикою"""
    images_dir = Path("out/images")
    
    # Шукаємо останній загальний графік
    today_images = list(images_dir.glob("*today*.png"))
    
    if not today_images:
        print("❌ Загальний графік не знайдено!")
        print("💡 Спочатку згенеруйте графік: python src/gener_im_full.py")
        return
    
    # Беремо найновіший файл
    latest_image = max(today_images, key=lambda f: f.stat().st_mtime)
    
    print(f"📤 Відправляю: {latest_image.name}")
    
    # Отправляем с полной статистикой
    caption = "🔌 <b>График отключений электроэнергии</b>\n"
    caption += "📍 Дніпро • ЦЕК\n"
    caption += "⏰ Актуальная информация"
    
    send_photo(str(latest_image), caption, with_stats=True)
    print("✅ График отправлен в Telegram!")

if __name__ == "__main__":
    quick_send()