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
import src.telegram_updates_monitor as telegram_updates_monitor
from .schedule_updates_parser import update_schedule_from_message


def parse_args():
    parser = argparse.ArgumentParser(description="Run Dnipro Oblenergo parser")
    parser.add_argument("--parse", "-p", action="store_true", help="Запустити парсинг Telegram-каналу")
    parser.add_argument("--monitor", "-m", action="store_true", help="Моніторинг оновлень графіків")
    parser.add_argument("--update", "-u", type=str, help="Застосувати оновлення з тексту повідомлення")
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
    
    # ---- ОБНОВЛЕНИЕ ГРАФИКА ИЗ ТЕКСТА ----
    if args.update:
        log("📝 Применяю обновление графика из текста сообщения")
        try:
            success = update_schedule_from_message(args.update)
            if success:
                log("✔️ Обновление успешно применено")
                
                # Генерируем обновленные изображения
                async def regenerate_images():
                    try:
                        json_path = config.get_json_path()
                        log(f"▶️ Перегенерация изображений после обновления")
                        
                        from .html_renderer import HTMLRenderer
                        renderer = HTMLRenderer(str(json_path))
                        results = await renderer.generate_all_images("light")
                        
                        total_images = 0
                        total_images += len(results.get('full', []))
                        total_images += len(results.get('groups', []))
                        for group_results in results.get('individual', {}).values():
                            total_images += len(group_results)
                        
                        log(f"✔️ Перегенерация завершена - обновлено {total_images} файлов")
                        renderer.cleanup_temp()
                        return True
                        
                    except Exception as e:
                        log(f"❌ Ошибка перегенерации изображений: {e}")
                        return False
                
                if asyncio.run(regenerate_images()):
                    log("🎉 Обновление графика завершено успешно")
                    return True
                else:
                    return False
            else:
                log("⚠️ Обновление не было применено")
                return False
        except Exception as e:
            log(f"❌ Ошибка применения обновления: {e}")
            return False
    
    # ---- КОМБИНИРОВАННЫЙ РЕЖИМ: ПАРСИНГ + МОНИТОРИНГ ----
    if args.parse and args.monitor:
        log("🔄 Запускаю комбинированный режим: парсинг + мониторинг")
        
        # Сначала парсинг
        parse_success = False
        try:
            log("📱 Запускаю парсинг Telegram-каналу Дніпро ОЕ")
            result = asyncio.run(dnipro_telegram_parser.main())
            
            if result:
                log("✔️ Парсинг завершено успішно — JSON оновлено")
                parse_success = True
            else:
                log("ℹ️ Парсинг завершено — дані не змінились")
                parse_success = True
                
        except Exception as e:
            log(f"❌ Помилка при парсингу Telegram: {e}")
            import traceback
            log(traceback.format_exc())
            return False
        
        # Затем мониторинг обновлений
        updates_found = False
        if parse_success:
            try:
                log("🔍 Запускаю мониторинг обновлений графиков")
                result = asyncio.run(telegram_updates_monitor.main())
                
                if result:
                    log("✔️ Найдены и применены обновления графиков")
                    updates_found = True
                else:
                    log("ℹ️ Новых обновлений не найдено")
                    
            except Exception as e:
                log(f"❌ Ошибка мониторинга обновлений: {e}")
                import traceback
                log(traceback.format_exc())
                # Продолжаем выполнение даже если мониторинг не удался
        
        # Генерируем изображения ОДИН РАЗ в конце
        if parse_success:
            async def generate_images():
                try:
                    json_path = config.get_json_path()
                    if updates_found:
                        log(f"▶️ Генерация изображений после парсинга и обновлений")
                    else:
                        log(f"▶️ Генерация изображений после парсинга")
                    
                    from .html_renderer import HTMLRenderer
                    renderer = HTMLRenderer(str(json_path))
                    results = await renderer.generate_all_images("light")
                    
                    total_images = 0
                    total_images += len(results.get('full', []))
                    total_images += len(results.get('groups', []))
                    for group_results in results.get('individual', {}).values():
                        total_images += len(group_results)
                    
                    log(f"✔️ Генерация завершена - создано {total_images} файлов")
                    renderer.cleanup_temp()
                    return True
                    
                except Exception as e:
                    log(f"❌ Ошибка генерации изображений: {e}")
                    import traceback
                    log(traceback.format_exc())
                    return False
            
            if asyncio.run(generate_images()):
                log("🎉 Комбинированный режим завершен успешно")
                return True
            else:
                return False
        
        return False
    
    # ---- МОНИТОРИНГ ОБНОВЛЕНИЙ (ОТДЕЛЬНО) ----
    if args.monitor:
        log("🔍 Запускаю мониторинг обновлений графиков")
        try:
            result = asyncio.run(telegram_updates_monitor.main())
            
            if result:
                log("✔️ Найдены и применены обновления графиков")
                
                # Генерируем обновленные изображения
                async def regenerate_images():
                    try:
                        json_path = config.get_json_path()
                        log(f"▶️ Перегенерация изображений после обновлений")
                        
                        from .html_renderer import HTMLRenderer
                        renderer = HTMLRenderer(str(json_path))
                        results = await renderer.generate_all_images("light")
                        
                        total_images = 0
                        total_images += len(results.get('full', []))
                        total_images += len(results.get('groups', []))
                        for group_results in results.get('individual', {}).values():
                            total_images += len(group_results)
                        
                        log(f"✔️ Перегенерация завершена - обновлено {total_images} файлов")
                        renderer.cleanup_temp()
                        return True
                        
                    except Exception as e:
                        log(f"❌ Ошибка перегенерации изображений: {e}")
                        return False
                
                if asyncio.run(regenerate_images()):
                    log("🎉 Мониторинг и обновление завершены успешно")
                    return True
                else:
                    return False
            else:
                log("ℹ️ Новых обновлений не найдено")
                return True
                
        except Exception as e:
            log(f"❌ Ошибка мониторинга обновлений: {e}")
            import traceback
            log(traceback.format_exc())
            return False
    
    # ---- ПАРСИНГ TELEGRAM-КАНАЛУ (ОТДЕЛЬНО) ----
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
        log("ℹ️ Доступные команды:")
        log("   --parse (-p)    - Парсинг Telegram-каналу")
        log("   --monitor (-m)  - Мониторинг обновлений графиков")
        log("   --update (-u)   - Применить обновление из текста")
        log("   Примеры:")
        log("     python3 src/main.py --parse")
        log("     python3 src/main.py --monitor")
        log("     python3 src/main.py --parse --monitor  # Комбинированный режим")
        log('     python3 src/main.py --update "відключення підчерги 4.2 з 01:00 до 05:00"')


if __name__ == "__main__":
    main()
