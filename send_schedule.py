#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для відправки графіків відключень в Telegram
Працює з новими HTML-генерованими зображеннями

Основні функції:
- Відправка всіх доступних графіків
- Відправка графіків для конкретної групи
- Відправка тільки статистики
- Показ списку доступних зображень
- Інтерактивне меню для вибору дій
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Додаємо src в шлях для імпорту модулів
sys.path.insert(0, str(Path(__file__).parent))

from src.telegram_notify import send_photo, send_message, send_stats_only, log
from src.config import config

def send_all_schedules():
    """Відправити всі доступні графіки в Telegram"""
    images_dir = config.IMAGES_DIR
    
    if not images_dir.exists():
        print("❌ Папка output/images не знайдена!")
        return
    
    # Паттерни для HTML-генерованих зображень (тільки світла тема)
    full_pattern = f"gpv-full-*.png"
    groups_today_pattern = f"gpv-all-groups-*.png"
    groups_tomorrow_pattern = f"gpv-all-groups-tomorrow-*.png"
    
    # Виключаємо темні зображення
    full_images = [img for img in images_dir.glob(full_pattern) if "-dark" not in img.name]
    groups_today_images = [img for img in images_dir.glob(groups_today_pattern) if "-dark" not in img.name]
    groups_tomorrow_images = [img for img in images_dir.glob(groups_tomorrow_pattern) if "-dark" not in img.name]
    
    print(f"🔍 Знайдено зображень:")
    print(f"   📊 Повних графіків: {len(full_images)}")
    print(f"   📅 Матриць груп (сьогодні): {len(groups_today_images)}")
    print(f"   📅 Матриць груп (завтра): {len(groups_tomorrow_images)}")
    
    # Відправляємо повний графік (сьогодні + тиждень)
    if full_images:
        latest_full = max(full_images, key=lambda f: f.stat().st_mtime)
        print(f"📤 Відправляю повний графік: {latest_full.name}")
        
        caption = f"📊 <b>Повний графік відключень</b> ☀️\n\n"
        caption += f"Сьогодні/завтра + тижневий прогноз"
        
        send_photo(str(latest_full), caption, with_stats=True)
    
    # Відправляємо матрицю груп на сьогодні
    if groups_today_images:
        latest_today = max(groups_today_images, key=lambda f: f.stat().st_mtime)
        print(f"📤 Відправляю матрицю груп (сьогодні): {latest_today.name}")
        
        caption = f"📊 <b>Всі групи на сьогодні</b> ☀️\n\n"
        caption += f"Матриця відключень по всіх групах"
        
        send_photo(str(latest_today), caption, with_stats=False)
    
    # Відправляємо матрицю груп на завтра (якщо є)
    if groups_tomorrow_images:
        latest_tomorrow = max(groups_tomorrow_images, key=lambda f: f.stat().st_mtime)
        print(f"📤 Відправляю матрицю груп (завтра): {latest_tomorrow.name}")
        
        caption = f"📊 <b>Всі групи на завтра</b> ☀️\n\n"
        caption += f"Матриця відключень по всіх групах"
        
        send_photo(str(latest_tomorrow), caption, with_stats=False)

def send_group_schedule(group_number):
    """
    Відправити графік для конкретної групи
    
    Args:
        group_number: Номер групи у форматі "1-1" (для GPV1.1)
    """
    images_dir = config.IMAGES_DIR
    
    # Шукаємо зображення для групи (тільки світлі)
    pattern = f"gpv-{group_number}-emergency-*.png"
    group_images = [img for img in images_dir.glob(pattern) if "-dark" not in img.name]
    
    if not group_images:
        print(f"❌ Не знайдено зображень для групи {group_number}")
        print(f"   Шукав за шаблоном: {pattern}")
        return
    
    # Беремо найновіше зображення
    latest_image = max(group_images, key=lambda f: f.stat().st_mtime)
    print(f"📤 Відправляю графік для групи {group_number}: {latest_image.name}")
    
    caption = f"📊 <b>Графік відключень - Група {group_number}</b> ☀️\n\n"
    caption += f"Детальний графік на 2 дні"
    
    send_photo(str(latest_image), caption, with_stats=False)

def send_statistics_only():
    """Відправити тільки статистику без зображень"""
    print("📊 Відправляю статистику...")
    send_stats_only()

def list_available_images():
    """Показати доступні зображення з детальною інформацією"""
    images_dir = config.IMAGES_DIR
    
    if not images_dir.exists():
        print("❌ Папка output/images не знайдена!")
        return
    
    images = list(images_dir.glob("*.png"))
    if not images:
        print("❌ Зображення не знайдені!")
        print("💡 Спочатку згенеруйте зображення:")
        print("   python generate_all_images.py")
        print("   або python test_html_renderer.py")
        return
    
    # Показуємо тільки світлі зображення
    light_images = [img for img in images if "-dark" not in img.name]
    
    print(f"📁 Знайдено {len(light_images)} зображень:")
    print("=" * 60)
    
    if light_images:
        print(f"\n☀️ Світлі ({len(light_images)} шт.):")
        print("-" * 40)
        
        # Групуємо за типами
        full_imgs = [img for img in light_images if "gpv-full" in img.name]
        groups_imgs = [img for img in light_images if "gpv-all-groups" in img.name]
        emergency_imgs = [img for img in light_images if "emergency" in img.name and "gpv-all" not in img.name]
        week_imgs = [img for img in light_images if "week" in img.name]
        summary_imgs = [img for img in light_images if "summary" in img.name]
        
        def show_subgroup(imgs, subtype):
            if imgs:
                print(f"  📊 {subtype}:")
                for img in sorted(imgs):
                    size_mb = img.stat().st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(img.stat().st_mtime, ZoneInfo("Europe/Kyiv"))
                    print(f"    📄 {img.name}")
                    print(f"       Розмір: {size_mb:.1f} МБ | Створено: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        show_subgroup(full_imgs, "Повні графіки")
        show_subgroup(groups_imgs, "Матриці груп")
        show_subgroup(emergency_imgs, "Аварійні графіки")
        show_subgroup(week_imgs, "Тижневі графіки")
        show_subgroup(summary_imgs, "Картки")

def main():
    """Головна функція з обробкою аргументів командного рядка"""
    print("📱 ВІДПРАВКА ГРАФІКІВ В TELEGRAM")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "all":
            send_all_schedules()
        elif command == "stats":
            send_statistics_only()
        elif command == "list":
            list_available_images()
        elif command.startswith("group"):
            if len(sys.argv) > 2:
                group_number = sys.argv[2]
                send_group_schedule(group_number)
            else:
                print("❌ Вкажіть номер групи: python send_schedule.py group 1-1")
        else:
            print(f"❌ Невідома команда: {command}")
            show_help()
    else:
        show_menu()

def show_help():
    """Показати довідку по доступних командах"""
    print("\n📋 Доступні команди:")
    print("python send_schedule.py all              - Відправити всі графіки")
    print("python send_schedule.py stats            - Відправити тільки статистику")
    print("python send_schedule.py group 1-1        - Відправити графік групи 1.1")
    print("python send_schedule.py list             - Показати доступні зображення")
    print("python send_schedule.py                  - Показати інтерактивне меню")

def show_menu():
    """Показати інтерактивне меню для вибору дій"""
    while True:
        print("\n📋 Виберіть дію:")
        print("1. ☀️  Відправити всі графіки")
        print("2. 📈  Відправити тільки статистику")
        print("3. 👥  Відправити графік групи")
        print("4. 📁  Показати доступні зображення")
        print("5. ❌  Вихід")
        
        try:
            choice = input("\n👉 Ваш вибір (1-5): ").strip()
            
            if choice == "1":
                send_all_schedules()
            elif choice == "2":
                send_statistics_only()
            elif choice == "3":
                group = input("👥 Введіть номер групи (наприклад: 1-1): ").strip()
                if group:
                    send_group_schedule(group)
                else:
                    print("❌ Номер групи не вказано")
            elif choice == "4":
                list_available_images()
            elif choice == "5":
                print("👋 До побачення!")
                break
            else:
                print("❌ Неправильний вибір. Спробуйте знову.")
                
        except KeyboardInterrupt:
            print("\n👋 До побачення!")
            break
        except Exception as e:
            print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    main()