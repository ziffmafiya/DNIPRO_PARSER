#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Швидкий тест центрування номера групи в жовтому овалі
Перевіряє правильність відображення номерів груп у жовтих бейджах

Цей скрипт:
- Генерує картки для різних груп
- Перевіряє центрування тексту в жовтих овалах
- Допомагає виявити проблеми з CSS стилями
"""

import asyncio
import sys
from pathlib import Path

# Додаємо src в шлях
sys.path.insert(0, str(Path(__file__).parent / "src"))

from html_renderer import HTMLRenderer

async def test_centering():
    """Тест центрування для різних груп"""
    
    json_path = "out/Dneproblenergo.json"
    renderer = HTMLRenderer(json_path)
    
    try:
        # Тестуємо різні групи для перевірки центрування
        test_groups = ['GPV1.1', 'GPV2.2', 'GPV6.1']
        
        print("🧪 Тестую центрування номерів груп...")
        
        for group in test_groups:
            print(f"\n📋 Генерую картку для {group}...")
            
            # Генеруємо картку (summary) - там найкраще видно центрування
            result = await renderer.generate_summary_card(group, "light")
            print(f"✅ Створена: {Path(result).name}")
            
        print(f"\n🎉 Тест завершено!")
        print(f"📁 Перевірте зображення в папці: {Path('out/images').absolute()}")
        print("💡 Зверніть увагу на центрування номерів в жовтих овалах")
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        renderer.cleanup_temp()

if __name__ == "__main__":
    asyncio.run(test_centering())