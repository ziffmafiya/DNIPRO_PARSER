import argparse
import os
import asyncio
import json
from zoneinfo import ZoneInfo
from datetime import datetime
from pathlib import Path

# Імпорти модулів проекту
from .config import config
from .logger import log
from .telegram_notify import send_error, send_message, send_photo
from .utils import clean_old_files, clean_log
import src.dnipro_telegram_parser as dnipro_telegram_parser


def parse_args():
    parser = argparse.ArgumentParser(description="Run Dnipro Oblenergo parser")
    parser.add_argument("--parse", "-p", action="store_true", help="Запустити парсинг Telegram-каналу")
    return parser.parse_args()


def main():
    """Головна функція для запуску повного циклу парсингу та генерації"""
    # Видаляємо зображення старше 5 днів у кількох папках
    folders = ["in", "DEBUG_IMAGES"]
    deleted_total = 0

    for folder in folders:
        deleted = clean_old_files(folder, config.CLEANUP_DAYS, config.CLEANUP_EXTENSIONS)
        count = len(deleted)
        deleted_total += count

        if count > 0:
            log(f"🗑️ Видалено {count} старих файлів у папці: {folder}")

    if deleted_total > 0:
        log(f"📦 Разом видалено {deleted_total} старих файлів у вибраних папках")

    # Чистимо лог від даних старше 3 днів
    log_file = config.LOGS_DIR / "full_log.log"
    removed = clean_log(str(log_file), days=config.LOG_RETENTION_DAYS)
    if removed is not None:
        if removed > 0:
            log(f"🧹 Логи очищено — видалено {removed} старих рядків")
    else:
        log("⚠️ Файла логів ще не існує — очищення пропущено")
    
    args = parse_args()
    
    # ---- ПАРСИНГ TELEGRAM-КАНАЛУ ----
    if args.parse:
        log("📱 Запускаю парсинг Telegram-каналу Дніпро ОЕ")
        try:
            result = asyncio.run(dnipro_telegram_parser.main())
            
            if result:
                log("✔️ Парсинг завершено успішно — JSON оновлено")
                
                # ---- ГЕНЕРАЦІЯ ЗОБРАЖЕНЬ (НОВА HTML СИСТЕМА) ----
                async def generate_images():
                    try:
                        json_path = config.get_json_path()
                        log(f"▶️ Запускаю генерацію зображень через HTML рендерер з {json_path}")
                        
                        # Імпортуємо новий HTML рендерер
                        from .html_renderer import HTMLRenderer
                        
                        # Створюємо рендерер та генеруємо всі зображення
                        renderer = HTMLRenderer(str(json_path))
                        results = await renderer.generate_all_images("light")
                        
                        # Підраховуємо згенеровані зображення
                        total_images = 0
                        total_images += len(results.get('full', []))
                        total_images += len(results.get('groups', []))
                        for group_results in results.get('individual', {}).values():
                            total_images += len(group_results)
                        
                        log(f"✔️ Генерація HTML зображень завершена - створено {total_images} файлів")
                        
                        # Очищуємо тимчасові файли
                        renderer.cleanup_temp()
                        return True
                        
                    except Exception as e:
                        log(f"❌ Помилка при генерації HTML зображень: {e}")
                        import traceback
                        log(traceback.format_exc())
                        return False
                
                # Запускаємо генерацію зображень
                if not asyncio.run(generate_images()):
                    return False

                # ---- ЗАПУСК UPLOAD GitHub (ВІДКЛЮЧЕНО ДЛЯ GITHUB ACTIONS) ----
                # try:
                #     log("▶️ Запускаю завантаження даних на GitHub")
                #     upload_to_github.run_upload()
                #     log("✔️ Завантаження на GitHub успішно завершене")
                # except Exception as e:
                #     log(f"❌ Помилка при завантаженні на GitHub: {e}")
                #     # send_error(f"❌ Помилка при завантаженні на GitHub: {e}") # ВІДКЛЮЧЕНО
                #     return False
                
                # ---- ВІДПРАВКА ФОТО В TELEGRAM (ВІДКЛЮЧЕНО) ----
                # try:
                #     # Читаємо JSON для перевірки дат
                #     with open(json_path, "r", encoding="utf-8") as f:
                #         data = json.load(f)
                #     
                #     # Отримуємо сьогоднішню дату в timestamp
                #     today_ts = data.get("fact", {}).get("today")
                #     
                #     # Отримуємо всі дати з графіками
                #     schedules = data.get("fact", {}).get("data", {})
                #     schedule_timestamps = [int(ts) for ts in schedules.keys()]
                #     
                #     # Визначаємо яке фото відправляти
                #     if len(schedule_timestamps) >= 2:
                #         # Є дві дати (сьогодні + завтра)
                #         photo_path = "output/images/gpv-all-tomorrow.png"
                #         caption = "🔄 <b>Дніпрообленерго</b>\nГрафік на завтра\n#Дніпрообленерго"
                #         log("📸 Відправляю графік на ЗАВТРА (є 2 дати)")
                #     else:
                #         # Тільки одна дата (сьогодні)
                #         photo_path = "output/images/gpv-all-today.png"
                #         caption = "🔄 <b>Дніпрообленерго</b>\nГрафік на сьогодні\n#Дніпрообленерго"
                #         log("📸 Відправляю графік на СЬОГОДНІ (1 дата)")
                #     
                #     # Перевіряємо чи файл існує
                #     if os.path.exists(photo_path):
                #         send_photo(photo_path, caption)
                #         log(f"✔️ Фото відправлено: {photo_path}")
                #     else:
                #         log(f"⚠️ Файл не знайдено: {photo_path}")
                #         # send_error(f"⚠️ Файл не знайдено: {photo_path}") # ВІДКЛЮЧЕНО
                #         
                # except Exception as e:
                #     log(f"❌ Помилка при відправці фото: {e}")
                #     # send_error(f"❌ Помилка при відправці фото: {e}") # ВІДКЛЮЧЕНО
                
                log("🎉 Повний цикл оновлення завершено успішно")
                return True
            else:
                log("ℹ️ Парсинг завершено — дані не змінились, оновлення не потрібне")
                return True
                
        except Exception as e:
            log(f"❌ Помилка при парсингу Telegram: {e}")
            # send_error(f"❌ Помилка при парсингу Telegram: {e}") # ВІДКЛЮЧЕНО
            import traceback
            log(traceback.format_exc())
            return False
    else:
        log("ℹ️ Використайте --parse (-p) для запуску парсингу Telegram-каналу")
        log("   Приклад: python3 src/main.py --parse")


if __name__ == "__main__":
    main()
