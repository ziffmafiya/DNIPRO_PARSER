#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматический мониторинг обновлений графиков
Скрипт для запуска по расписанию (cron/задачи Windows)
"""

import sys
import os
import asyncio
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import config
from src.logger import log
from src.telegram_updates_monitor import monitor_updates
from src.html_renderer import HTMLRenderer

async def main():
    """Основная функция автоматического мониторинга"""
    log("🤖 Запуск автоматического мониторинга обновлений")
    log(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Проверяем обновления
        updates_found = await monitor_updates()
        
        if updates_found:
            log("🔄 Найдены обновления, перегенерируем изображения...")
            
            # Перегенерируем изображения
            try:
                json_path = config.get_json_path()
                renderer = HTMLRenderer(str(json_path))
                results = await renderer.generate_all_images("light")
                
                total_images = 0
                total_images += len(results.get('full', []))
                total_images += len(results.get('groups', []))
                for group_results in results.get('individual', {}).values():
                    total_images += len(group_results)
                
                log(f"✅ Перегенерация завершена - обновлено {total_images} файлов")
                renderer.cleanup_temp()
                
                # Здесь можно добавить отправку уведомлений
                # from src.telegram_notify import send_message
                # send_message("🔄 Графики обновлены автоматически")
                
            except Exception as e:
                log(f"❌ Ошибка перегенерации изображений: {e}")
                return False
        
        log("✅ Автоматический мониторинг завершен успешно")
        return True
        
    except Exception as e:
        log(f"❌ Ошибка автоматического мониторинга: {e}")
        import traceback
        log(traceback.format_exc())
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit_code = 0 if result else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("⚠️ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Фатальная ошибка: {e}")
        sys.exit(1)