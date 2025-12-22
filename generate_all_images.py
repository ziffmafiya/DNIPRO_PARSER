#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерація всіх типів зображень через HTML рендерер
Використовує новий підхід з HTML/CSS шаблонами замість Pillow

Цей скрипт:
- Знаходить останній JSON файл з даними
- Генерує всі типи зображень для всіх GPV груп
- Створює повні графіки, матриці груп та індивідуальні зображення
- Логує процес генерації
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Додаємо src в шлях для імпорту
sys.path.insert(0, str(Path(__file__).parent))

from src.html_renderer import HTMLRenderer
from src.config import config
from src.logger import log

def find_latest_json():
    """Знайти останній JSON файл в папці output/"""
    json_path = config.get_latest_json()
    
    if not json_path:
        raise FileNotFoundError("Не знайдено JSON файлів в папці output/")
    
    return str(json_path)

async def generate_all_themes(json_path: str):
    """Генерувати зображення тільки для світлої теми"""
    renderer = HTMLRenderer(json_path)
    
    try:
        results = {}
        
        # Тільки світла тема
        log("☀️ Генерую зображення світлої теми...")
        results['light'] = await renderer.generate_all_images("light")
        
        return results
        
    finally:
        # Очищуємо тимчасові файли
        renderer.cleanup_temp()

def count_generated_images(results):
    """Підрахувати кількість згенерованих зображень"""
    total = 0
    
    for theme_name, theme_results in results.items():
        theme_count = 0
        
        # Повні графіки
        theme_count += len(theme_results.get('full', []))
        
        # Матриці груп
        theme_count += len(theme_results.get('groups', []))
        
        # Індивідуальні зображення
        for group_results in theme_results.get('individual', {}).values():
            theme_count += len(group_results)
            
        log(f"   {theme_name.capitalize()}: {theme_count} зображень")
        total += theme_count
        
    return total

async def main():
    """
    Основна функція для генерації всіх зображень
    
    Цей процес:
    1. Знаходить останній JSON файл з даними відключень
    2. Перевіряє наявність всіх необхідних HTML шаблонів
    3. Генерує зображення тільки для світлої теми
    4. Підраховує та виводить статистику згенерованих файлів
    5. Показує команди для відправки в Telegram
    """
    log("🎨 Починаю генерацію всіх зображень через HTML рендерер")
    
    try:
        # Знаходимо останній JSON
        json_path = find_latest_json()
        log(f"📄 Використовується JSON: {json_path}")
        
        # Перевіряємо наявність шаблонів
        templates_dir = config.TEMPLATES_DIR
        if not templates_dir.exists():
            log("❌ Папка 'templates' з HTML шаблонами не знайдена!")
            sys.exit(1)
            
        required_templates = [
            "full-template.html",
            "emergency-template.html", 
            "week-template.html",
            "groups-template.html",
            "summary-item.html",
        ]
        
        required_resources = [
            "css/schedule-shared.css",
            "js/schedule-shared.js"
        ]
        
        missing_files = []
        for template in required_templates:
            if not (templates_dir / template).exists():
                missing_files.append(template)
                
        for resource in required_resources:
            if not (templates_dir / resource).exists():
                missing_files.append(resource)
                
        if missing_files:
            log(f"❌ Відсутні файли: {', '.join(missing_files)}")
            sys.exit(1)
            
        log("✅ Всі необхідні шаблони та ресурси знайдені")
        
        # Генеруємо зображення
        results = await generate_all_themes(json_path)
        
        # Підраховуємо результати
        log("=" * 60)
        log("📊 Результати генерації:")
        total_images = count_generated_images(results)
        
        log(f"🎉 Всього згенеровано: {total_images} зображень")
        log(f"📁 Зображення збережені в: {config.IMAGES_DIR}")
        
        # Показуємо команди для відправки
        log("\n💡 Для відправки в Telegram використовуйте:")
        log("   python send_schedule.py all              # Всі графіки")
        log("   python send_schedule.py group 1-1        # Конкретна група")
        log("   python send_schedule.py stats            # Тільки статистика")
        
    except Exception as e:
        log(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Перевіряємо наявність playwright
    try:
        import playwright
    except ImportError:
        log("❌ Playwright не встановлено!")
        log("   Встановіть: pip install playwright")
        log("   Потім: playwright install chromium")
        sys.exit(1)
        
    asyncio.run(main())