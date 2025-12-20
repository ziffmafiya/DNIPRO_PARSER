#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для генерації всіх типів зображень одразу
Генерує: звичайні та темні версії
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

def log(message):
    """Логування з timestamp"""
    timestamp = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} [generate_all] {message}")

def run_generator(script_name, args=None):
    """Запустити генератор зображень"""
    cmd = ["python", f"src/{script_name}"]
    if args:
        cmd.extend(args)
    
    log(f"🔄 Запускаю {script_name}...")
    try:
        # Просто запускаємо без захоплення виводу
        result = subprocess.run(cmd)
        if result.returncode == 0:
            log(f"✅ {script_name} завершено успішно")
            return True
        else:
            log(f"❌ Помилка в {script_name} (код: {result.returncode})")
            return False
    except Exception as e:
        log(f"❌ Помилка запуску {script_name}: {e}")
        return False

def main():
    """Головна функція"""
    log("🚀 Початок генерації всіх типів зображень")
    
    # Перевіряємо наявність JSON файлів
    json_dir = Path("out")
    json_files = list(json_dir.glob("*.json"))
    
    if not json_files:
        log("❌ JSON файли не знайдено в папці out/")
        sys.exit(1)
    
    latest_json = max(json_files, key=lambda f: f.stat().st_mtime)
    log(f"📄 Використовую JSON: {latest_json}")
    
    success_count = 0
    total_generators = 4  # Зменшено з 6 до 4
    
    # 1. Звичайні зображення для груп
    if run_generator("gener_im_1_G.py"):
        success_count += 1
    
    # 2. Повні зображення
    if run_generator("gener_im_full.py"):
        success_count += 1
    
    # 3. Темні зображення для груп
    if run_generator("gener_im_dark.py", ["--type", "individual"]):
        success_count += 1
    
    # 4. Темні повні зображення
    if run_generator("gener_im_dark.py", ["--type", "full"]):
        success_count += 1
    
    # Підсумок
    log("=" * 60)
    log(f"📊 Результат: {success_count}/{total_generators} генераторів завершено успішно")
    
    if success_count == total_generators:
        log("🎉 Всі зображення згенеровано успішно!")
        
        # Показуємо статистику
        images_dir = Path("out/images")
        if images_dir.exists():
            images = list(images_dir.glob("*.png"))
            log(f"📁 Всього зображень: {len(images)}")
            
            # Групуємо по типах
            light_images = len([img for img in images if "-dark" not in img.name])
            dark_images = len([img for img in images if "-dark" in img.name])
            
            log(f"   ☀️  Світлі: {light_images}")
            log(f"   🌙  Темні: {dark_images}")
        
        log("💡 Для відправки в Telegram використовуйте:")
        log("   python send_schedule.py all        # Світлі")
        log("   python send_schedule.py all --dark # Темні")
        
    else:
        log("⚠️ Деякі генератори завершилися з помилками")
        sys.exit(1)

if __name__ == "__main__":
    main()