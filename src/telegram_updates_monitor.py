#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мониторинг обновлений графиков в Telegram канале
Отслеживает новые сообщения об изменениях в графиках отключений
"""

import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
from pathlib import Path

from .config import config
from .logger import log
from .schedule_updates_parser import is_update_message, update_schedule_from_message

TZ = ZoneInfo("Europe/Kyiv")
URL = "https://t.me/s/cek_info"

# Файл для хранения последнего обработанного сообщения
LAST_MESSAGE_FILE = config.OUTPUT_DIR / "last_processed_message.json"


async def fetch_recent_posts(limit: int = 20) -> list:
    """Загружает последние посты из Telegram канала"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            log(f"🌐 Загружаю последние посты из {URL}...")
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector(".tgme_widget_message", timeout=30000)
            
            # Ждем дополнительно для рендеринга контента
            await page.wait_for_timeout(3000)
            
            # Находим все посты
            posts = await page.query_selector_all(".tgme_widget_message")
            log(f"✔️ Найдено {len(posts)} постов на странице")
            
            recent_posts = []
            
            # Берем только последние посты (limit штук)
            for post in posts[:limit]:
                try:
                    # Получаем ID поста
                    post_id = None
                    post_link = await post.query_selector("a.tgme_widget_message_date")
                    if post_link:
                        href = await post_link.get_attribute("href")
                        if href:
                            post_id = href.split("/")[-1]
                    
                    # Получаем текст поста
                    text_element = await post.query_selector(".tgme_widget_message_text")
                    if not text_element:
                        continue
                    
                    post_text = await text_element.inner_text()
                    
                    # Получаем дату поста
                    date_element = await post.query_selector(".tgme_widget_message_date time")
                    post_date_str = None
                    if date_element:
                        post_date_str = await date_element.get_attribute("datetime")
                    
                    recent_posts.append({
                        'id': post_id,
                        'text': post_text,
                        'date': post_date_str
                    })
                    
                except Exception as e:
                    log(f"⚠️ Ошибка обработки поста: {e}")
                    continue
            
            log(f"✔️ Обработано {len(recent_posts)} постов")
            
        finally:
            await browser.close()
            
        return recent_posts


def load_last_processed_message() -> dict:
    """Загружает информацию о последнем обработанном сообщении"""
    if not LAST_MESSAGE_FILE.exists():
        return {"last_id": None, "last_date": None}
    
    try:
        with open(LAST_MESSAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"⚠️ Ошибка чтения файла последнего сообщения: {e}")
        return {"last_id": None, "last_date": None}


def save_last_processed_message(post_id: str, post_date: str):
    """Сохраняет информацию о последнем обработанном сообщении"""
    try:
        data = {
            "last_id": post_id,
            "last_date": post_date,
            "processed_at": datetime.now(TZ).isoformat()
        }
        with open(LAST_MESSAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"⚠️ Ошибка сохранения файла последнего сообщения: {e}")


def is_newer_post(post_date: str, last_date: str) -> bool:
    """Проверяет, является ли пост более новым чем последний обработанный"""
    if not last_date:
        return True
    
    try:
        post_dt = datetime.fromisoformat(post_date.replace("Z", "+00:00"))
        last_dt = datetime.fromisoformat(last_date.replace("Z", "+00:00"))
        return post_dt > last_dt
    except Exception as e:
        log(f"⚠️ Ошибка сравнения дат: {e}")
        return True


async def monitor_updates() -> bool:
    """
    Мониторит обновления в Telegram канале и применяет их к графику
    
    Returns:
        bool: True если были найдены и применены обновления
    """
    log("🔍 Начинаю мониторинг обновлений графиков...")
    
    # Загружаем последние посты
    try:
        posts = await fetch_recent_posts(limit=10)  # Проверяем последние 10 постов
    except Exception as e:
        log(f"❌ Ошибка загрузки постов: {e}")
        return False
    
    if not posts:
        log("⚠️ Не найдено постов для обработки")
        return False
    
    # Загружаем информацию о последнем обработанном сообщении
    last_processed = load_last_processed_message()
    last_id = last_processed.get("last_id")
    last_date = last_processed.get("last_date")
    
    log(f"📋 Последнее обработанное сообщение: ID={last_id}, дата={last_date}")
    
    updates_applied = False
    latest_processed_id = last_id
    latest_processed_date = last_date
    
    # Обрабатываем посты в обратном порядке (от старых к новым)
    for post in reversed(posts):
        post_id = post.get("id")
        post_date = post.get("date")
        post_text = post.get("text", "")
        
        # Пропускаем если это не новый пост
        if post_id == last_id:
            log(f"⏭️ Пост {post_id} уже был обработан")
            continue
        
        if not is_newer_post(post_date, last_date):
            log(f"⏭️ Пост {post_id} старше последнего обработанного")
            continue
        
        # Проверяем, является ли это сообщением об обновлении
        if not is_update_message(post_text):
            log(f"⏭️ Пост {post_id} не содержит обновлений графика")
            # Обновляем последний обработанный пост даже если он не содержит обновлений
            latest_processed_id = post_id
            latest_processed_date = post_date
            continue
        
        log(f"🔄 Найдено сообщение об обновлении графика: {post_id}")
        log(f"📝 Текст: {post_text[:200]}...")
        
        # Применяем обновление
        try:
            success = update_schedule_from_message(post_text)
            if success:
                log(f"✅ Обновление из поста {post_id} успешно применено")
                updates_applied = True
            else:
                log(f"⚠️ Не удалось применить обновление из поста {post_id}")
        except Exception as e:
            log(f"❌ Ошибка применения обновления из поста {post_id}: {e}")
        
        # Обновляем последний обработанный пост
        latest_processed_id = post_id
        latest_processed_date = post_date
    
    # Сохраняем информацию о последнем обработанном сообщении
    if latest_processed_id != last_id:
        save_last_processed_message(latest_processed_id, latest_processed_date)
        log(f"💾 Обновлен последний обработанный пост: {latest_processed_id}")
    
    if updates_applied:
        log("🎉 Обновления графиков успешно применены!")
        return True
    else:
        log("ℹ️ Новых обновлений графиков не найдено")
        return False


async def main():
    """Основная функция для запуска мониторинга"""
    try:
        result = await monitor_updates()
        return result
    except Exception as e:
        log(f"❌ Ошибка мониторинга обновлений: {e}")
        import traceback
        log(traceback.format_exc())
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            log("🎉 Мониторинг завершен успешно")
        else:
            log("ℹ️ Мониторинг завершен без обновлений")
    except KeyboardInterrupt:
        log("⚠️ Прервано пользователем")
    except Exception as e:
        log(f"❌ Фатальная ошибка: {e}")
        import traceback
        log(traceback.format_exc())