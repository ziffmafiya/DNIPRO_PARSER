#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль логування з ротацією файлів для DNIPRO_PARSER
"""
import os
import logging
import logging.handlers
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import config

# Налаштування логування з конфігурації
LOG_LEVEL = config.LOG_LEVEL.upper()
MAX_LOG_SIZE = int(os.getenv("MAX_LOG_SIZE", "10")) * 1024 * 1024  # МБ в байти
BACKUP_COUNT = 7  # Зберігати 7 файлів (тиждень)
TIMEZONE = os.getenv("TIMEZONE", "Europe/Kyiv")

class UkrainianFormatter(logging.Formatter):
    """Форматер з українською локалізацією"""
    
    def formatTime(self, record, datefmt=None):
        """Форматувати час з українським часовим поясом"""
        dt = datetime.fromtimestamp(record.created, ZoneInfo(TIMEZONE))
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

def setup_logger(name: str, log_file: str = "full_log.log") -> logging.Logger:
    """
    Налаштувати логер з ротацією файлів
    
    Args:
        name: Назва логера
        log_file: Назва файлу логу
        
    Returns:
        Налаштований логер
    """
    logger = logging.getLogger(name)
    
    # Якщо логер вже налаштований, повертаємо його
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Ротаційний файловий хендлер
    log_path = config.LOGS_DIR / log_file
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    
    # Консольний хендлер
    console_handler = logging.StreamHandler()
    
    # Форматер
    formatter = UkrainianFormatter(
        fmt='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def cleanup_old_logs(days_to_keep: int = 7):
    """
    Видалити старі лог файли
    
    Args:
        days_to_keep: Скільки днів зберігати логи
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in config.LOGS_DIR.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                log_file.unlink()
                print(f"Видалено старий лог: {log_file}")
                
    except Exception as e:
        print(f"Помилка при очищенні логів: {e}")

def get_log_stats() -> dict:
    """
    Отримати статистику логів
    
    Returns:
        Словник зі статистикою
    """
    try:
        log_files = list(config.LOGS_DIR.glob("*.log*"))
        total_size = sum(f.stat().st_size for f in log_files)
        
        return {
            "files_count": len(log_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "log_dir": str(config.LOGS_DIR),
            "oldest_log": min(log_files, key=lambda f: f.stat().st_mtime).name if log_files else None,
            "newest_log": max(log_files, key=lambda f: f.stat().st_mtime).name if log_files else None
        }
    except Exception as e:
        return {"error": str(e)}

# Основний логер для проекту
main_logger = setup_logger("DNIPRO_PARSER")

# Функції для зворотної сумісності
def log(message: str, level: str = "INFO"):
    """Логувати повідомлення (для зворотної сумісності)"""
    getattr(main_logger, level.lower())(message)

def log_info(message: str):
    """Логувати інформаційне повідомлення"""
    main_logger.info(message)

def log_warning(message: str):
    """Логувати попередження"""
    main_logger.warning(message)

def log_error(message: str):
    """Логувати помилку"""
    main_logger.error(message)

def log_debug(message: str):
    """Логувати налагоджувальне повідомлення"""
    main_logger.debug(message)

# Автоматичне очищення старих логів при імпорті
if __name__ != "__main__":
    cleanup_old_logs()

# Тестування модуля
if __name__ == "__main__":
    # Тестові повідомлення
    log_info("Тест інформаційного повідомлення")
    log_warning("Тест попередження")
    log_error("Тест помилки")
    log_debug("Тест налагоджувального повідомлення")
    
    # Статистика
    stats = get_log_stats()
    print(f"Статистика логів: {stats}")
    
    # Очищення старих логів
    cleanup_old_logs(days_to_keep=7)