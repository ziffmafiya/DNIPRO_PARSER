#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для відправки графіків відключень в Telegram
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Додаємо src в шлях для імпорту модулів
sys.path.append(str(Path(__file__).parent / "src"))

from telegram_notify import send_photo, send_message, send_stats_only, log

def send_all_schedules(theme="light"):
    """Відправити всі доступні графіки"""
    images_dir = Path("out/images")
    
    if not images_dir.exists():
        print("❌ Папка out/images не знайдена!")
        return
    
    # Формуємо суфікси для пошуку
    theme_suffix = "-dark" if theme == "dark" else ""
    
    # Шукаємо зображення з урахуванням теми
    today_pattern = f"*today*{theme_suffix}*.png"
    tomorrow_pattern = f"*tomorrow*{theme_suffix}*.png"
    group_pattern = f"gpv-*-emergency{theme_suffix}-*.png"
    
    today_images = list(images_dir.glob(today_pattern))
    tomorrow_images = list(images_dir.glob(tomorrow_pattern))
    group_images = list(images_dir.glob(group_pattern))
    
    theme_name = "темные" if theme == "dark" else "светлые"
    
    print(f"🔍 Найдено {theme_name} изображений:")
    print(f"   📅 Сегодня: {len(today_images)}")
    print(f"   📅 Завтра: {len(tomorrow_images)}")
    print(f"   👥 По группам: {len(group_images)}")
    
    # Відправляємо загальний графік на сьогодні
    if today_images:
        latest_today = max(today_images, key=lambda f: f.stat().st_mtime)
        print(f"📤 Отправляю общий график: {latest_today.name}")
        
        theme_emoji = "🌙" if theme == "dark" else "☀️"
        
        caption = f"📊 <b>График отключений на сегодня</b> {theme_emoji}\n\n"
        caption += f"Все группы на одном изображении ({theme_name})"
        
        send_photo(str(latest_today), caption, with_stats=True)
    
    # Відправляємо графік на завтра (якщо є)
    if tomorrow_images:
        latest_tomorrow = max(tomorrow_images, key=lambda f: f.stat().st_mtime)
        print(f"📤 Отправляю график на завтра: {latest_tomorrow.name}")
        
        theme_emoji = "🌙" if theme == "dark" else "☀️"
        
        caption = f"📊 <b>График отключений на завтра</b> {theme_emoji}\n\n"
        caption += f"Все группы на одном изображении ({theme_name})"
        
        send_photo(str(latest_tomorrow), caption, with_stats=False)

def send_group_schedule(group_number, theme="light"):
    """Відправити графік для конкретної групи"""
    images_dir = Path("out/images")
    
    # Формуємо суфікси для пошуку
    theme_suffix = "-dark" if theme == "dark" else ""
    
    # Шукаємо зображення для групи з урахуванням теми
    pattern = f"gpv-{group_number}-emergency{theme_suffix}-*.png"
    group_images = list(images_dir.glob(pattern))
    
    if not group_images:
        print(f"❌ Не найдено изображений для группы {group_number}")
        print(f"   Искал по шаблону: {pattern}")
        return
    
    # Беремо найновіше зображення
    latest_image = max(group_images, key=lambda f: f.stat().st_mtime)
    print(f"📤 Отправляю график для группы {group_number}: {latest_image.name}")
    
    theme_name = "темная" if theme == "dark" else "светлая"
    theme_emoji = "🌙" if theme == "dark" else "☀️"
    
    caption = f"📊 <b>График отключений - Группа {group_number}</b> {theme_emoji}\n\n"
    caption += f"Детальный график на 2 дня ({theme_name} тема)"
    
    send_photo(str(latest_image), caption, with_stats=False)

def send_statistics_only():
    """Відправити тільки статистику без зображень"""
    print("📊 Отправляю статистику...")
    send_stats_only()

def list_available_images():
    """Показати доступні зображення"""
    images_dir = Path("out/images")
    
    if not images_dir.exists():
        print("❌ Папка out/images не найдена!")
        return
    
    images = list(images_dir.glob("*.png"))
    if not images:
        print("❌ Изображения не найдены!")
        print("💡 Сначала сгенерируйте изображения:")
        print("   python src/gener_im_full.py")
        print("   python src/gener_im_1_G.py")
        print("   python src/gener_im_dark.py")
        return
    
    # Групуємо зображення за типами
    light_images = [img for img in images if "-dark" not in img.name]
    dark_images = [img for img in images if "-dark" in img.name]
    
    print(f"📁 Найдено {len(images)} изображений:")
    print("=" * 60)
    
    def show_image_group(images, title, emoji):
        if images:
            print(f"\n{emoji} {title} ({len(images)} шт.):")
            print("-" * 40)
            for img in sorted(images):
                size_mb = img.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(img.stat().st_mtime, ZoneInfo("Europe/Kyiv"))
                print(f"📄 {img.name}")
                print(f"   Размер: {size_mb:.1f} МБ | Создан: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    show_image_group(light_images, "Светлые", "☀️")
    show_image_group(dark_images, "Темные", "🌙")

def main():
    """Головна функція з меню"""
    print("📱 ОТПРАВКА ГРАФИКОВ В TELEGRAM")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        # Парсимо додаткові параметри
        theme = "light"
        
        if "--dark" in sys.argv:
            theme = "dark"
        
        if command == "all":
            send_all_schedules(theme)
        elif command == "stats":
            send_statistics_only()
        elif command == "list":
            list_available_images()
        elif command.startswith("group"):
            if len(sys.argv) > 2:
                group_number = sys.argv[2]
                send_group_schedule(group_number, theme)
            else:
                print("❌ Укажите номер группы: python send_schedule.py group 1-1")
        else:
            print(f"❌ Неизвестная команда: {command}")
            show_help()
    else:
        show_menu()

def show_help():
    """Показати довідку по командах"""
    print("\n📋 Доступные команды:")
    print("python send_schedule.py all              - Отправить все графики (светлые)")
    print("python send_schedule.py all --dark       - Отправить все графики (темные)")
    print("python send_schedule.py stats            - Отправить только статистику")
    print("python send_schedule.py group 1-1        - Отправить график группы 1.1 (светлый)")
    print("python send_schedule.py group 1-1 --dark - Отправить график группы 1.1 (темный)")
    print("python send_schedule.py list             - Показать доступные изображения")
    print("python send_schedule.py                  - Показать интерактивное меню")

def show_menu():
    """Показати інтерактивне меню"""
    while True:
        print("\n📋 Выберите действие:")
        print("1. ☀️  Отправить все графики (светлые)")
        print("2. 🌙  Отправить все графики (темные)")
        print("3. 📈  Отправить только статистику")
        print("4. 👥  Отправить график группы")
        print("5. 📁  Показать доступные изображения")
        print("6. ❌  Выход")
        
        try:
            choice = input("\n👉 Ваш выбор (1-6): ").strip()
            
            if choice == "1":
                send_all_schedules("light")
            elif choice == "2":
                send_all_schedules("dark")
            elif choice == "3":
                send_statistics_only()
            elif choice == "4":
                group = input("👥 Введите номер группы (например: 1-1): ").strip()
                if group:
                    print("\n🎨 Выберите тему:")
                    print("1. ☀️  Светлая")
                    print("2. 🌙  Темная")
                    
                    theme_choice = input("👉 Ваш выбор (1-2): ").strip()
                    
                    if theme_choice == "1":
                        send_group_schedule(group, "light")
                    elif theme_choice == "2":
                        send_group_schedule(group, "dark")
                    else:
                        print("❌ Неверный выбор темы")
                else:
                    print("❌ Номер группы не указан")
            elif choice == "5":
                list_available_images()
            elif choice == "6":
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
                
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()