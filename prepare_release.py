#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для підготовки релізу проекту DNIPRO_PARSER
Перевіряє готовність проекту до публікації на GitHub
"""

import os
import sys
from pathlib import Path
import subprocess
import json

def log(message, level="INFO"):
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
    print(f"{color}[{level}]{reset} {message}")

def check_file_exists(file_path, description):
    """Перевірка існування файлу"""
    if Path(file_path).exists():
        log(f"✅ {description}: {file_path}", "SUCCESS")
        return True
    else:
        log(f"❌ {description} не знайдено: {file_path}", "ERROR")
        return False

def check_directory_structure():
    """Перевірка структури проекту"""
    log("🔍 Перевірка структури проекту...", "INFO")
    
    required_files = [
        ("README.md", "Основний README"),
        ("requirements.txt", "Залежності Python"),
        ("LICENSE", "Ліцензія"),
        (".env.example", "Приклад конфігурації"),
        ("src/main.py", "Головний скрипт"),
        ("src/html_renderer.py", "HTML рендерер"),
        ("src/config.py", "Конфігурація"),
        ("generate_all_images.py", "Генератор зображень"),
        ("send_schedule.py", "Telegram відправка"),
        ("Makefile", "Makefile команди"),
        ("run.sh", "Bash скрипт"),
    ]
    
    required_dirs = [
        ("src/", "Папка з кодом"),
        ("templates/", "HTML шаблони"),
        ("output/", "Вихідні файли"),
        ("logs/", "Папка логів"),
        ("docs/", "Документація"),
        ("tests/", "Тести"),
        ("scripts/", "Скрипти"),
    ]
    
    html_templates = [
        ("templates/full-template.html", "Повний графік"),
        ("templates/emergency-template.html", "Аварійний графік"),
        ("templates/week-template.html", "Тижневий графік"),
        ("templates/groups-template.html", "Матриця груп"),
        ("templates/summary-item.html", "Картки"),
        ("templates/css/schedule-shared.css", "CSS стилі"),
        ("templates/js/schedule-shared.js", "JavaScript"),
    ]
    
    all_good = True
    
    # Перевірка файлів
    for file_path, description in required_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    # Перевірка папок
    for dir_path, description in required_dirs:
        if not Path(dir_path).is_dir():
            log(f"❌ {description} не знайдено: {dir_path}", "ERROR")
            all_good = False
        else:
            log(f"✅ {description}: {dir_path}", "SUCCESS")
    
    # Перевірка HTML шаблонів
    for template_path, description in html_templates:
        if not check_file_exists(template_path, description):
            all_good = False
    
    return all_good

def check_python_syntax():
    """Перевірка синтаксису Python файлів"""
    log("🐍 Перевірка синтаксису Python...", "INFO")
    
    python_files = [
        "src/main.py",
        "src/html_renderer.py",
        "src/config.py",
        "generate_all_images.py",
        "send_schedule.py",
        "tests/test_html_renderer.py",
    ]
    
    all_good = True
    
    for file_path in python_files:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), file_path, 'exec')
                log(f"✅ Синтаксис OK: {file_path}", "SUCCESS")
            except SyntaxError as e:
                log(f"❌ Помилка синтаксису в {file_path}: {e}", "ERROR")
                all_good = False
        else:
            log(f"⚠️ Файл не знайдено: {file_path}", "WARNING")
    
    return all_good

def check_dependencies():
    """Перевірка залежностей"""
    log("📦 Перевірка залежностей...", "INFO")
    
    try:
        import playwright
        log("✅ Playwright встановлено", "SUCCESS")
    except ImportError:
        log("❌ Playwright не встановлено", "ERROR")
        return False
    
    try:
        import requests
        log("✅ Requests встановлено", "SUCCESS")
    except ImportError:
        log("❌ Requests не встановлено", "ERROR")
        return False
    
    return True

def check_git_status():
    """Перевірка статусу Git"""
    log("📝 Перевірка Git статусу...", "INFO")
    
    try:
        # Перевірка чи є незакомічені зміни
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        if result.stdout.strip():
            log("⚠️ Є незакомічені зміни:", "WARNING")
            print(result.stdout)
            return False
        else:
            log("✅ Всі зміни закомічені", "SUCCESS")
            return True
            
    except subprocess.CalledProcessError:
        log("❌ Помилка при перевірці Git статусу", "ERROR")
        return False

def create_release_info():
    """Створення інформації про реліз"""
    log("📋 Створення інформації про реліз...", "INFO")
    
    version = "2.0.0"
    
    release_info = {
        "version": version,
        "name": f"v{version} - HTML Rendering System",
        "description": "Повна міграція на HTML/CSS систему рендерингу зображень",
        "features": [
            "HTML/CSS рендеринг замість Pillow",
            "5 типів зображень (повний, аварійний, тижневий, матриця, картки)",
            "Playwright рендеринг для високої якості",
            "Українські коментарі у всьому коді",
            "Покращена архітектура та організація коду"
        ],
        "breaking_changes": [
            "Видалена темна тема",
            "Старі Pillow генератори більше не підтримуються",
            "Зміна команд запуску"
        ],
        "migration": [
            "Встановіть Playwright: playwright install chromium",
            "Використовуйте python src/main.py --parse",
            "Перегляньте MIGRATION_GUIDE.md"
        ]
    }
    
    with open("release_info.json", "w", encoding="utf-8") as f:
        json.dump(release_info, f, ensure_ascii=False, indent=2)
    
    log("✅ Створено release_info.json", "SUCCESS")
    return True

def main():
    """Головна функція"""
    log("🚀 Підготовка релізу DNIPRO_PARSER v2.0.0", "INFO")
    log("=" * 50, "INFO")
    
    checks = [
        ("Структура проекту", check_directory_structure),
        ("Синтаксис Python", check_python_syntax),
        ("Залежності", check_dependencies),
        ("Git статус", check_git_status),
        ("Інформація про реліз", create_release_info),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        log(f"\n🔍 {check_name}...", "INFO")
        if not check_func():
            all_passed = False
    
    log("\n" + "=" * 50, "INFO")
    
    if all_passed:
        log("🎉 Проект готовий до релізу!", "SUCCESS")
        log("\n📋 Наступні кроки:", "INFO")
        log("1. git tag v2.0.0", "INFO")
        log("2. git push origin v2.0.0", "INFO")
        log("3. Створіть реліз на GitHub", "INFO")
        log("4. Завантажте release_info.json як опис релізу", "INFO")
        return 0
    else:
        log("❌ Проект не готовий до релізу. Виправте помилки вище.", "ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(main())