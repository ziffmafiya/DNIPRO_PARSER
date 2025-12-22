#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт установки и настройки HTML рендерера
"""

import subprocess
import sys
import os
from pathlib import Path

def log(message, level="INFO"):
    """Логирование с цветами"""
    colors = {
        "INFO": "\033[94m",    # Синий
        "SUCCESS": "\033[92m", # Зеленый
        "WARNING": "\033[93m", # Желтый
        "ERROR": "\033[91m",   # Красный
        "RESET": "\033[0m"     # Сброс
    }
    
    color = colors.get(level, colors["INFO"])
    reset = colors["RESET"]
    print(f"{color}[{level}]{reset} {message}")

def run_command(cmd, description):
    """Выполнить команду с логированием"""
    log(f"Выполняю: {description}")
    log(f"Команда: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        log(f"✅ {description} - успешно", "SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ {description} - ошибка", "ERROR")
        log(f"Код ошибки: {e.returncode}", "ERROR")
        if e.stdout:
            log(f"Вывод: {e.stdout}", "WARNING")
        if e.stderr:
            log(f"Ошибка: {e.stderr}", "ERROR")
        return False
    except FileNotFoundError:
        log(f"❌ Команда не найдена: {cmd[0]}", "ERROR")
        return False

def check_python_version():
    """Проверить версию Python"""
    log("Проверяю версию Python...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        log(f"❌ Требуется Python 3.8+, найден {version.major}.{version.minor}", "ERROR")
        return False
    
    log(f"✅ Python {version.major}.{version.minor}.{version.micro} - подходит", "SUCCESS")
    return True

def install_requirements():
    """Установить зависимости из requirements.txt"""
    log("Устанавливаю зависимости Python...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        log("❌ Файл requirements.txt не найден", "ERROR")
        return False
    
    return run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        "Установка зависимостей Python"
    )

def install_playwright():
    """Установить Playwright и браузеры"""
    log("Устанавливаю Playwright...")
    
    # Установка Playwright
    if not run_command(
        [sys.executable, "-m", "pip", "install", "playwright"],
        "Установка Playwright"
    ):
        return False
    
    # Установка браузера Chromium
    return run_command(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        "Установка Chromium для Playwright"
    )

def check_templates():
    """Проверить наличие HTML шаблонов"""
    log("Проверяю HTML шаблоны...")
    
    templates_dir = Path("исходники")
    if not templates_dir.exists():
        log("❌ Папка 'исходники' не найдена", "ERROR")
        log("   Убедитесь, что папка с HTML шаблонами существует", "WARNING")
        return False
    
    required_files = [
        "full-template.html",
        "emergency-template.html",
        "week-template.html", 
        "groups-template.html",
        "summary-item.html",
        "schedule-shared.css",
        "schedule-shared.js"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = templates_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        log(f"❌ Отсутствуют файлы: {', '.join(missing_files)}", "ERROR")
        return False
    
    # Проверяем SVG иконки
    svg_files = list(templates_dir.glob("*.svg"))
    log(f"✅ Найдено SVG иконок: {len(svg_files)}", "SUCCESS")
    
    log("✅ Все необходимые шаблоны найдены", "SUCCESS")
    return True

def check_json_data():
    """Проверить наличие JSON данных"""
    log("Проверяю JSON данные...")
    
    json_dir = Path("out")
    if not json_dir.exists():
        log("⚠️ Папка 'out' не найдена - будет создана автоматически", "WARNING")
        return True
    
    json_files = list(json_dir.glob("*.json"))
    if not json_files:
        log("⚠️ JSON файлы не найдены в папке 'out'", "WARNING")
        log("   Сначала запустите парсер: python src/main.py --parse", "WARNING")
        return True
    
    latest_json = max(json_files, key=lambda f: f.stat().st_mtime)
    log(f"✅ Найден JSON файл: {latest_json.name}", "SUCCESS")
    return True

def create_directories():
    """Создать необходимые папки"""
    log("Создаю необходимые папки...")
    
    directories = [
        "out",
        "out/images", 
        "logs",
        "temp_render"
    ]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            log(f"✅ Создана папка: {dir_name}", "SUCCESS")
        else:
            log(f"✅ Папка существует: {dir_name}", "SUCCESS")
    
    return True

def test_html_renderer():
    """Тестировать HTML рендерер"""
    log("Тестирую HTML рендерер...")
    
    # Проверяем, что можно импортировать модуль
    try:
        sys.path.insert(0, str(Path("src")))
        from html_renderer import HTMLRenderer
        log("✅ Модуль html_renderer импортирован успешно", "SUCCESS")
    except ImportError as e:
        log(f"❌ Ошибка импорта html_renderer: {e}", "ERROR")
        return False
    
    # Проверяем наличие JSON для теста
    json_dir = Path("out")
    json_files = list(json_dir.glob("*.json"))
    
    if not json_files:
        log("⚠️ Нет JSON файлов для тестирования", "WARNING")
        log("   Запустите сначала: python src/main.py --parse", "WARNING")
        return True
    
    log("✅ HTML рендерер готов к использованию", "SUCCESS")
    return True

def main():
    """Основная функция установки"""
    log("🚀 УСТАНОВКА HTML РЕНДЕРЕРА ДЛЯ DNIPRO_PARSER", "INFO")
    log("=" * 60, "INFO")
    
    steps = [
        ("Проверка версии Python", check_python_version),
        ("Установка зависимостей Python", install_requirements),
        ("Установка Playwright", install_playwright),
        ("Проверка HTML шаблонов", check_templates),
        ("Проверка JSON данных", check_json_data),
        ("Создание папок", create_directories),
        ("Тестирование рендерера", test_html_renderer)
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        log(f"\n📋 Шаг: {step_name}", "INFO")
        log("-" * 40, "INFO")
        
        if step_func():
            success_count += 1
        else:
            log(f"❌ Шаг '{step_name}' завершился с ошибкой", "ERROR")
            
            # Для критических шагов прерываем установку
            if step_func in [check_python_version, install_playwright]:
                log("🛑 Критическая ошибка - установка прервана", "ERROR")
                sys.exit(1)
    
    # Итоги
    log("\n" + "=" * 60, "INFO")
    log("📊 РЕЗУЛЬТАТЫ УСТАНОВКИ", "INFO")
    log("=" * 60, "INFO")
    
    log(f"Выполнено шагов: {success_count}/{len(steps)}", "INFO")
    
    if success_count == len(steps):
        log("🎉 Установка завершена успешно!", "SUCCESS")
        log("\n💡 Следующие шаги:", "INFO")
        log("1. Запустите парсер: python src/main.py --parse", "INFO")
        log("2. Тестируйте рендерер: python test_html_renderer.py", "INFO")
        log("3. Генерируйте изображения: python generate_all_images.py", "INFO")
        log("4. Отправляйте в Telegram: python send_schedule.py all", "INFO")
    else:
        log("⚠️ Установка завершена с предупреждениями", "WARNING")
        log("Проверьте логи выше и исправьте ошибки", "WARNING")

if __name__ == "__main__":
    main()