#!/bin/bash
# Единый скрипт запуска DNIPRO_PARSER
# Поддерживает различные режимы работы

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция логирования
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python3 не найден!"
        exit 1
    fi
    
    log "Python версия: $(python3 --version)"
}

# Проверка зависимостей
check_dependencies() {
    log "Проверка зависимостей..."
    
    if ! python3 -c "import playwright" 2>/dev/null; then
        error "Playwright не установлен!"
        echo "Установите: pip install playwright && playwright install chromium"
        exit 1
    fi
    
    if ! python3 -c "import requests" 2>/dev/null; then
        error "Requests не установлен!"
        echo "Установите: pip install -r requirements.txt"
        exit 1
    fi
    
    success "Все зависимости установлены"
}

# Проверка конфигурации
check_config() {
    if [ ! -f ".env" ]; then
        warning "Файл .env не найден!"
        echo "Создайте файл .env на основе .env.example"
        return 1
    fi
    
    # Проверяем обязательные переменные
    if ! grep -q "BOT_TOKEN=" .env || ! grep -q "ADMIN_CHAT_ID=" .env; then
        warning "Не все обязательные переменные настроены в .env"
        return 1
    fi
    
    success "Конфигурация в порядке"
}

# Создание необходимых папок
create_directories() {
    log "Создание необходимых папок..."
    mkdir -p output/images
    mkdir -p logs
    mkdir -p temp_render
    success "Папки созданы"
}

# Полный цикл
run_full() {
    log "🚀 Запуск полного цикла (парсинг + генерация)"
    python3 -m src.main --parse
}

# Только парсинг
run_parse() {
    log "📱 Запуск парсинга Telegram канала"
    python3 -m src.dnipro_telegram_parser
}

# Только генерация
run_generate() {
    log "🖼️ Запуск генерации изображений"
    python3 generate_all_images.py
}

# Отправка в Telegram
run_send() {
    log "📤 Отправка в Telegram"
    if [ "$1" = "menu" ]; then
        python3 send_schedule.py
    else
        python3 send_schedule.py all
    fi
}

# Тестирование
run_test() {
    log "🧪 Запуск тестов"
    python3 tests/test_html_renderer.py
    python3 tests/test_centering.py
}

# Очистка
run_clean() {
    log "🧹 Очистка временных файлов"
    rm -rf temp_render/
    rm -rf __pycache__/
    rm -rf src/__pycache__/
    find . -name "*.pyc" -delete
    find . -name "*.pyo" -delete
    success "Очистка завершена"
}

# Показать статус
show_status() {
    log "📊 Статус проекта DNIPRO_PARSER"
    echo ""
    
    echo "📁 Структура проекта:"
    ls -la | grep "^d" | head -10
    echo ""
    
    echo "📄 JSON файлы:"
    if ls output/*.json 1> /dev/null 2>&1; then
        ls -la output/*.json
    else
        echo "  Нет JSON файлов"
    fi
    echo ""
    
    echo "🖼️ Изображения:"
    if ls output/images/*.png 1> /dev/null 2>&1; then
        echo "  Количество PNG файлов: $(ls output/images/*.png | wc -l)"
        echo "  Последнее изображение: $(ls -t output/images/*.png | head -1)"
    else
        echo "  Нет изображений"
    fi
    echo ""
    
    echo "📝 Логи:"
    if ls logs/*.log 1> /dev/null 2>&1; then
        ls -la logs/*.log
    else
        echo "  Нет лог файлов"
    fi
}

# Справка
show_help() {
    echo "🔌 DNIPRO_PARSER - Скрипт запуска"
    echo ""
    echo "Использование: $0 [команда]"
    echo ""
    echo "Команды:"
    echo "  full, run       - Полный цикл (парсинг + генерация)"
    echo "  parse          - Только парсинг Telegram"
    echo "  generate       - Только генерация изображений"
    echo "  send           - Отправить все в Telegram"
    echo "  send-menu      - Интерактивное меню отправки"
    echo "  test           - Запустить тесты"
    echo "  clean          - Очистить временные файлы"
    echo "  status         - Показать статус проекта"
    echo "  setup          - Первоначальная настройка"
    echo "  help           - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 full        # Полный цикл"
    echo "  $0 parse       # Только парсинг"
    echo "  $0 send        # Отправка в Telegram"
}

# Первоначальная настройка
setup() {
    log "🔧 Первоначальная настройка проекта"
    
    # Установка зависимостей
    log "Установка Python зависимостей..."
    pip3 install -r requirements.txt
    
    # Установка Playwright
    log "Установка Playwright браузеров..."
    playwright install chromium
    
    # Создание папок
    create_directories
    
    # Проверка конфигурации
    if [ ! -f ".env" ]; then
        log "Создание файла .env из примера..."
        cp .env.example .env
        warning "Отредактируйте файл .env и добавьте ваши токены!"
    fi
    
    success "Настройка завершена!"
    echo ""
    echo "Следующие шаги:"
    echo "1. Отредактируйте файл .env"
    echo "2. Запустите: $0 full"
}

# Основная логика
main() {
    # Проверки окружения
    check_python
    create_directories
    
    case "${1:-help}" in
        "full"|"run")
            check_dependencies
            check_config || warning "Проблемы с конфигурацией, но продолжаем..."
            run_full
            ;;
        "parse")
            check_dependencies
            check_config || warning "Проблемы с конфигурацией, но продолжаем..."
            run_parse
            ;;
        "generate")
            check_dependencies
            run_generate
            ;;
        "send")
            check_dependencies
            check_config || { error "Настройте .env файл для Telegram!"; exit 1; }
            run_send
            ;;
        "send-menu")
            check_dependencies
            check_config || { error "Настройте .env файл для Telegram!"; exit 1; }
            run_send menu
            ;;
        "test")
            check_dependencies
            run_test
            ;;
        "clean")
            run_clean
            ;;
        "status")
            show_status
            ;;
        "setup")
            setup
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Запуск
main "$@"