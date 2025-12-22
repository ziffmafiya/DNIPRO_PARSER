#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфігурація проекту DNIPRO_PARSER
Централізоване управління налаштуваннями та змінними оточення
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу
load_dotenv()

class Config:
    """Клас для управління конфігурацією проекту"""
    
    # Базові шляхи
    BASE_DIR = Path(__file__).parent.parent.absolute()
    SRC_DIR = BASE_DIR / "src"
    TEMPLATES_DIR = BASE_DIR / "templates"
    OUTPUT_DIR = BASE_DIR / "output"
    IMAGES_DIR = OUTPUT_DIR / "images"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Telegram конфігурація
    BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
    ADMIN_CHAT_ID: Optional[str] = os.getenv("ADMIN_CHAT_ID")
    
    # GitHub конфігурація (опціонально)
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO: Optional[str] = os.getenv("GITHUB_REPO")
    
    # Парсинг налаштування
    TELEGRAM_CHANNEL = "@cek_info"
    JSON_FILENAME = "Dneproblenergo.json"
    
    # Рендеринг налаштування
    RENDER_SCALE = 2.0  # Масштаб для високої якості
    RENDER_TIMEOUT = 30000  # Таймаут рендерингу в мс
    
    # Логування
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "3"))
    
    # Очищення файлів
    CLEANUP_DAYS = int(os.getenv("CLEANUP_DAYS", "5"))
    CLEANUP_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
    
    @classmethod
    def validate(cls) -> bool:
        """
        Перевірка обов'язкових налаштувань
        
        Returns:
            bool: True якщо всі обов'язкові налаштування присутні
        """
        required_vars = ["BOT_TOKEN", "ADMIN_CHAT_ID"]
        missing_vars = []
        
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Відсутні обов'язкові змінні оточення: {', '.join(missing_vars)}")
            print("💡 Створіть файл .env на основі .env.example")
            return False
        
        return True
    
    @classmethod
    def create_directories(cls) -> None:
        """Створення необхідних папок"""
        directories = [
            cls.OUTPUT_DIR,
            cls.IMAGES_DIR,
            cls.LOGS_DIR,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_json_path(cls) -> Path:
        """Отримати шлях до JSON файлу з даними"""
        return cls.OUTPUT_DIR / cls.JSON_FILENAME
    
    @classmethod
    def get_latest_json(cls) -> Optional[Path]:
        """Знайти останній JSON файл в папці output"""
        json_files = list(cls.OUTPUT_DIR.glob("*.json"))
        
        if not json_files:
            return None
        
        # Сортуємо за часом модифікації
        latest_json = max(json_files, key=lambda f: f.stat().st_mtime)
        return latest_json


# Глобальний екземпляр конфігурації
config = Config()

# Створюємо необхідні папки при імпорті
config.create_directories()