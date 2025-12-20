#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для получения Chat ID из Telegram
"""
import requests
import json
from dotenv import load_dotenv
import os
from pathlib import Path

# Загружаем .env из корневой директории
BASE_DIR = Path(__file__).parent.absolute()
ENV_PATH = BASE_DIR / ".env"

print(f"🔍 Ищу .env файл: {ENV_PATH}")
if ENV_PATH.exists():
    print("✅ .env файл найден")
    load_dotenv(ENV_PATH)
else:
    print("❌ .env файл не найден")
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
print(f"🔑 BOT_TOKEN: {'найден' if BOT_TOKEN else 'не найден'}")

def get_chat_id():
    """Получить Chat ID из последних сообщений"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден в .env файле!")
        print("📝 Создайте .env файл на основе .env.example")
        return
    
    print(f"🤖 Используется токен: {BOT_TOKEN[:10]}...")
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        print(f"🌐 Запрос к: {url}")
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"Ответ: {response.text}")
            return
        
        data = response.json()
        
        if not data.get("ok"):
            print(f"❌ Ошибка Telegram API: {data.get('description', 'Неизвестная ошибка')}")
            return
        
        updates = data.get("result", [])
        
        if not updates:
            print("📭 Нет сообщений боту!")
            print("\n📋 Инструкция:")
            print("1. Найдите своего бота в Telegram")
            print("2. Напишите ему любое сообщение (например: 'Привет')")
            print("3. Запустите этот скрипт снова")
            return
        
        print(f"📨 Найдено {len(updates)} сообщений")
        print("\n" + "="*50)
        
        chat_ids = set()
        
        for update in updates:
            if "message" in update:
                message = update["message"]
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                chat_type = chat.get("type", "unknown")
                
                if chat_type == "private":
                    first_name = chat.get("first_name", "")
                    last_name = chat.get("last_name", "")
                    username = chat.get("username", "")
                    
                    print(f"👤 Личный чат:")
                    print(f"   ID: {chat_id}")
                    print(f"   Имя: {first_name} {last_name}".strip())
                    if username:
                        print(f"   Username: @{username}")
                    
                elif chat_type in ["group", "supergroup"]:
                    title = chat.get("title", "Без названия")
                    print(f"👥 Группа: {title}")
                    print(f"   ID: {chat_id}")
                
                elif chat_type == "channel":
                    title = chat.get("title", "Без названия")
                    print(f"📢 Канал: {title}")
                    print(f"   ID: {chat_id}")
                
                chat_ids.add(chat_id)
                print("-" * 30)
        
        if chat_ids:
            print(f"\n✅ Найдено {len(chat_ids)} уникальных чатов")
            print("\n📋 Для использования в .env файле:")
            for chat_id in sorted(chat_ids):
                print(f"ADMIN_CHAT_ID={chat_id}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

def test_bot_token():
    """Проверить валидность токена бота"""
    if not BOT_TOKEN:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"✅ Бот найден: @{bot_info.get('username', 'unknown')}")
                print(f"   Имя: {bot_info.get('first_name', 'Unknown')}")
                return True
        
        print(f"❌ Неверный токен бота")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка проверки токена: {e}")
        return False

if __name__ == "__main__":
    print("🔍 ПОИСК CHAT ID ДЛЯ TELEGRAM БОТА")
    print("=" * 50)
    
    # Проверяем токен
    if test_bot_token():
        print()
        get_chat_id()
    else:
        print("\n📝 Инструкция по получению токена:")
        print("1. Напишите @BotFather в Telegram")
        print("2. Отправьте команду /newbot")
        print("3. Следуйте инструкциям")
        print("4. Скопируйте токен в .env файл")