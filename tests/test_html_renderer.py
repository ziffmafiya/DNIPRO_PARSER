#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовий скрипт для перевірки HTML рендерера
Генерує кілька тестових зображень для перевірки роботи системи

Цей скрипт:
- Знаходить JSON файл з даними
- Тестує генерацію різних типів зображень
- Перевіряє доступні GPV групи
- Створює тестові зображення для перевірки якості
"""

import asyncio
import sys
from pathlib import Path

# Додаємо src в шлях
sys.path.insert(0, str(Path(__file__).parent / "src"))

from html_renderer import HTMLRenderer

async def test_single_render():
    """Тест генерації одного зображення"""
    
    # Знаходимо JSON файл
    json_dir = Path("out")
    json_files = list(json_dir.glob("*.json"))
    
    if not json_files:
        print("❌ JSON файли не знайдені в папці out/")
        return
        
    json_path = str(max(json_files, key=lambda f: f.stat().st_mtime))
    print(f"📄 Використовується JSON: {json_path}")
    
    # Створюємо рендерер
    renderer = HTMLRenderer(json_path)
    
    try:
        # Отримуємо доступні групи
        groups = renderer._get_available_groups()
        if not groups:
            print("❌ Немає доступних GPV груп")
            return
            
        print(f"📊 Знайдено груп: {groups}")
        
        # Тестуємо різні типи рендерингу
        test_group = groups[0]
        print(f"🧪 Тестую з групою: {test_group}")
        
        # 1. Аварійний графік
        print("\n1️⃣ Генерую аварійний графік...")
        emergency_light = await renderer.generate_emergency_schedule(test_group, "light")
        print(f"✅ Створено: {emergency_light}")
        
        # 2. Картка
        print("\n2️⃣ Генерую картку...")
        summary = await renderer.generate_summary_card(test_group, "light")
        print(f"✅ Створено: {summary}")
        
        # 3. Матриця груп
        print("\n3️⃣ Генерую матрицю груп...")
        groups_matrix = await renderer.generate_groups_matrix("today", "light")
        print(f"✅ Створено: {groups_matrix}")
        
        print("\n🎉 Тест завершено успішно!")
        print(f"📁 Перевірте папку: {Path('out/images').absolute()}")
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        renderer.cleanup_temp()

if __name__ == "__main__":
    print("🧪 Тестирование HTML рендерера")
    print("=" * 50)
    
    # Проверяем зависимости
    try:
        import playwright
        print("✅ Playwright установлен")
    except ImportError:
        print("❌ Playwright не установлен!")
        print("   Установите: pip install playwright")
        print("   Затем: playwright install chromium")
        sys.exit(1)
    
    # Проверяем шаблоны
    templates_dir = Path("исходники")
    if not templates_dir.exists():
        print("❌ Папка 'исходники' не найдена!")
        sys.exit(1)
        
    print("✅ Папка шаблонов найдена")
    
    # Запускаем тест
    asyncio.run(test_single_render())