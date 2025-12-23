#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для очистки старых зображень графіків
Видаляє зображення старше заданої кількості днів
"""

import os
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

def log(message: str, level: str = "INFO"):
    """Логування з кольорами"""
    colors = {
        "INFO": "\033[94m",  # Синій
        "SUCCESS": "\033[92m",  # Зелений
        "WARNING": "\033[93m",  # Жовтий
        "ERROR": "\033[91m",  # Червоний
        "RESET": "\033[0m"  # Скидання
    }
    
    color = colors.get(level, colors["INFO"])
    reset = colors["RESET"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{color}[{level}]{reset} {timestamp} {message}")

def extract_date_from_filename(filename: str) -> str:
    """
    Витягує дату з імені файлу
    Формат: gpv-*-YYYYMMDD-HHMMSS.png
    """
    match = re.search(r'-(\d{8})-', filename)
    return match.group(1) if match else None

def cleanup_old_images(images_dir: str, keep_days: int = 3, dry_run: bool = False):
    """
    Очищає старі зображення
    
    Args:
        images_dir: Шлях до папки з зображеннями
        keep_days: Скільки днів зберігати (за замовчуванням 3)
        dry_run: Тільки показати що буде видалено, не видаляти
    """
    images_path = Path(images_dir)
    
    if not images_path.exists():
        log(f"❌ Папка не знайдена: {images_dir}", "ERROR")
        return
    
    log(f"🔍 Сканую папку: {images_dir}", "INFO")
    
    # Отримуємо дати для збереження
    today = datetime.now()
    keep_dates = []
    
    for i in range(keep_days):
        date = today - timedelta(days=i)
        keep_dates.append(date.strftime("%Y%m%d"))
    
    log(f"📅 Зберігаю зображення за дати: {', '.join(keep_dates)}", "INFO")
    
    # Знаходимо всі PNG файли
    png_files = list(images_path.glob("*.png"))
    log(f"📊 Знайдено зображень: {len(png_files)}", "INFO")
    
    if not png_files:
        log("ℹ️ Зображення не знайдені", "INFO")
        return
    
    deleted_count = 0
    kept_count = 0
    
    for file_path in png_files:
        filename = file_path.name
        file_date = extract_date_from_filename(filename)
        
        if not file_date:
            log(f"⚠️ Не можу витягти дату з файлу: {filename}", "WARNING")
            kept_count += 1
            continue
        
        if file_date not in keep_dates:
            if dry_run:
                log(f"🗑️ [DRY RUN] Буде видалено: {filename} (дата: {file_date})", "WARNING")
            else:
                try:
                    file_path.unlink()
                    log(f"🗑️ Видалено: {filename} (дата: {file_date})", "SUCCESS")
                except Exception as e:
                    log(f"❌ Помилка видалення {filename}: {e}", "ERROR")
                    kept_count += 1
                    continue
            deleted_count += 1
        else:
            kept_count += 1
    
    log("=" * 50, "INFO")
    log(f"📊 Результати очистки:", "INFO")
    log(f"  🗑️ Видалено: {deleted_count}", "SUCCESS" if deleted_count > 0 else "INFO")
    log(f"  💾 Збережено: {kept_count}", "INFO")
    
    if dry_run and deleted_count > 0:
        log("ℹ️ Це був тестовий запуск. Для реального видалення запустіть без --dry-run", "INFO")

def main():
    """Головна функція"""
    parser = argparse.ArgumentParser(
        description="Очистка старих зображень графіків",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Приклади використання:
  python scripts/cleanup_old_images.py                    # Очистити зображення старше 3 днів
  python scripts/cleanup_old_images.py --days 5          # Зберегти тільки за останні 5 днів
  python scripts/cleanup_old_images.py --dry-run         # Показати що буде видалено
  python scripts/cleanup_old_images.py --dir custom/     # Вказати іншу папку
        """
    )
    
    parser.add_argument(
        "--dir", 
        default="output/images",
        help="Шлях до папки з зображеннями (за замовчуванням: output/images)"
    )
    
    parser.add_argument(
        "--days", 
        type=int, 
        default=3,
        help="Скільки днів зберігати зображення (за замовчуванням: 3)"
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Тестовий режим - показати що буде видалено, але не видаляти"
    )
    
    args = parser.parse_args()
    
    log("🧹 Запуск очистки старих зображень", "INFO")
    log(f"📁 Папка: {args.dir}", "INFO")
    log(f"📅 Зберігати днів: {args.days}", "INFO")
    log(f"🔍 Режим: {'Тестовий' if args.dry_run else 'Реальний'}", "INFO")
    log("=" * 50, "INFO")
    
    cleanup_old_images(args.dir, args.days, args.dry_run)

if __name__ == "__main__":
    main()