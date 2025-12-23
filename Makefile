# Makefile для DNIPRO_PARSER
# Упрощает выполнение основных команд проекта

.PHONY: help install setup test run parse generate send clean lint format

# Показать справку
help:
	@echo "🔌 DNIPRO_PARSER - Команды для управления проектом"
	@echo ""
	@echo "📦 Установка и настройка:"
	@echo "  make install    - Установить зависимости"
	@echo "  make setup      - Настроить окружение (Playwright)"
	@echo ""
	@echo "🚀 Основные команды:"
	@echo "  make run        - Полный цикл (парсинг + генерация)"
	@echo "  make parse      - Только парсинг Telegram"
	@echo "  make generate   - Только генерация изображений"
	@echo "  make send       - Отправить в Telegram"
	@echo ""
	@echo "🧪 Тестирование:"
	@echo "  make test       - Запустить тесты"
	@echo "  make lint       - Проверить код"
	@echo ""
	@echo "🧹 Очистка:"
	@echo "  make clean           - Очистить временные файлы"
	@echo "  make cleanup-images  - Удалить старые изображения"
	@echo "  make cleanup-images-dry - Показать что будет удалено"
	@echo ""
	@echo "📋 Информация:"
	@echo "  make status     - Показать статус проекта"

# Установка зависимостей
install:
	@echo "📦 Установка зависимостей..."
	pip install -r requirements.txt

# Настройка окружения
setup: install
	@echo "🔧 Настройка Playwright..."
	playwright install chromium
	@echo "📁 Создание папок..."
	python -c "from src.config import config; config.create_directories()"
	@echo "✅ Настройка завершена"

# Полный цикл
run:
	@echo "🚀 Запуск полного цикла..."
	python -m src.main --parse

# Только парсинг
parse:
	@echo "📱 Парсинг Telegram канала..."
	python -m src.dnipro_telegram_parser

# Только генерация
generate:
	@echo "🖼️ Генерация изображений..."
	python generate_all_images.py

# Отправка в Telegram
send:
	@echo "📤 Отправка в Telegram..."
	python send_schedule.py all

# Интерактивное меню отправки
send-menu:
	@echo "📋 Интерактивное меню..."
	python send_schedule.py

# Тестирование
test:
	@echo "🧪 Запуск тестов..."
	python -m pytest tests/ -v
	python tests/test_html_renderer.py
	python tests/test_centering.py

# Проверка кода
lint:
	@echo "🔍 Проверка кода..."
	python -m flake8 src/ --max-line-length=100
	python -m mypy src/ --ignore-missing-imports

# Форматирование кода
format:
	@echo "✨ Форматирование кода..."
	python -m black src/ --line-length=100
	python -m isort src/

# Очистка временных файлов
clean:
	@echo "🧹 Очистка временных файлов..."
	rm -rf temp_render/
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Очистка старых изображений
cleanup-images:
	@echo "🗑️ Очистка старых изображений..."
	python scripts/cleanup_old_images.py

# Тестовая очистка (показать что будет удалено)
cleanup-images-dry:
	@echo "🔍 Тестовая очистка изображений..."
	python scripts/cleanup_old_images.py --dry-run

# Статус проекта
status:
	@echo "📊 Статус проекта DNIPRO_PARSER:"
	@echo ""
	@echo "📁 Структура папок:"
	@ls -la | grep "^d"
	@echo ""
	@echo "📄 JSON файлы:"
	@ls -la output/*.json 2>/dev/null || echo "  Нет JSON файлов"
	@echo ""
	@echo "🖼️ Изображения:"
	@ls -la output/images/*.png 2>/dev/null | wc -l | xargs echo "  Количество PNG файлов:"
	@echo ""
	@echo "📝 Логи:"
	@ls -la logs/*.log 2>/dev/null || echo "  Нет лог файлов"

# Быстрые команды
quick-send:
	@echo "⚡ Быстрая отправка..."
	python scripts/quick_send.py

get-chat-id:
	@echo "🆔 Получение Chat ID..."
	python scripts/get_chat_id.py

# Подготовка к релизу
release-check:
	@echo "🚀 Проверка готовности к релизу..."
	python prepare_release.py

# Показать версию
version:
	@echo "📋 Версия проекта:"
	@cat VERSION

# По умолчанию показываем справку
.DEFAULT_GOAL := help