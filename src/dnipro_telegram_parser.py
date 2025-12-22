#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Parser for Dnipro Oblenergo (Telegram)

import asyncio
import re
import json
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
import os

TZ = ZoneInfo("Europe/Kyiv")
URL = "https://t.me/s/cek_info"
OUTPUT_FILE = "output/Dneproblenergo.json"

LOG_DIR = "logs"
FULL_LOG_FILE = os.path.join(LOG_DIR, "full_log.log")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs("output", exist_ok=True)

# Ключові слова для пошуку постів з графіками
KEYWORDS = [
    "графіки погодинних відключень",
    "ГПВ", 
    "години відсутності електропостачання",
    "будуть діяти графіки",
    "планові роботи",
    "відключення електропостачання",
    "графік відключень",
    "застосовуватимуться відключення наступних черг",
    "відключення наступних черг",
    "черга:"
]


def log(message: str):
    timestamp = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} [dnipro_parser] {message}"
    print(line)
    with open(FULL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def time_to_hour(hhmm: str) -> float:
    hh, mm = map(int, hhmm.split(":"))
    return hh + (mm / 60.0)


def is_schedule_post(text: str) -> bool:
    """Перевіряє чи містить текст ключові слова про графіки"""
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS)


async def fetch_posts() -> list:
    """Завантажує пости з Telegram та фільтрує їх за ключовими словами"""
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
            log(f"🌐 Завантажую {URL}...")
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector(".tgme_widget_message", timeout=30000)
            
            # Чекаємо додатково для рендерингу контенту
            await page.wait_for_timeout(3000)
            
            # Знаходимо всі пости
            posts = await page.query_selector_all(".tgme_widget_message")
            log(f"✔️ Знайдено {len(posts)} постів на сторінці")
            
            filtered_posts = []
            
            for post in posts:
                try:
                    # Отримуємо текст поста
                    text_element = await post.query_selector(".tgme_widget_message_text")
                    if not text_element:
                        continue
                    
                    post_text = await text_element.inner_text()
                    
                    # Перевіряємо чи це пост з графіком
                    if not is_schedule_post(post_text):
                        continue
                    
                    # Отримуємо дату поста
                    date_element = await post.query_selector(".tgme_widget_message_date time")
                    post_date_str = None
                    if date_element:
                        post_date_str = await date_element.get_attribute("datetime")
                    
                    filtered_posts.append({
                        'text': post_text,
                        'date': post_date_str
                    })
                    
                except Exception as e:
                    log(f"⚠️ Помилка обробки поста: {e}")
                    continue
            
            log(f"✔️ Знайдено {len(filtered_posts)} постів з графіками")
            
        finally:
            await browser.close()
            
        return filtered_posts


def put_interval(result: dict, group_id: str, t1: float, t2: float) -> None:
    """Отмечает интервал отключения в результате"""
    # Убираем сдвиг на +1 час, так как в ЦЕК время указано корректно
    # t1 += 1.0
    # t2 += 1.0
    
    for hour in range(1, 25):
        h_start = float(hour - 1)  # час 1 = 0:00-1:00
        h_mid = h_start + 0.5
        h_end = h_start + 1.0

        first_off = (t1 < h_mid and t2 > h_start)
        second_off = (t1 < h_end and t2 > h_mid)

        if not first_off and not second_off:
            continue

        key = str(hour)

        if first_off and second_off:
            result[group_id][key] = "no"
        elif first_off:
            result[group_id][key] = "first"
        elif second_off:
            result[group_id][key] = "second"


def extract_date_from_post(text: str, debug: bool = False) -> str:
    """Витягує дату з тексту поста для формату ЦЕК"""
    months = {
        'січня': '01', 'лютого': '02', 'березня': '03', 'квітня': '04',
        'травня': '05', 'червня': '06', 'липня': '07', 'серпня': '08',
        'вересня': '09', 'жовтня': '10', 'листопада': '11', 'грудня': '12'
    }
    
    # Спроба 1: Шукаємо дату в форматі "19 ГРУДНЯ" (як у прикладі ЦЕК)
    date_pattern_caps = r'(\d{1,2})\s+(' + '|'.join([m.upper() for m in months.keys()]) + r')'
    
    matches = list(re.finditer(date_pattern_caps, text, re.IGNORECASE))
    
    if debug and matches:
        log(f"   🔍 Знайдено {len(matches)} збігів з великими літерами")
    
    for idx, match in enumerate(matches, 1):
        day_num = match.group(1)
        month_name = match.group(2).lower()
        
        if debug:
            log(f"   📍 Збіг {idx}: '{day_num} {month_name}'")
        
        day = day_num.zfill(2)
        month = months.get(month_name)
        
        if month:
            date_str = f"{day}.{month}.{datetime.now(TZ).year}"
            if debug:
                log(f"   ✅ Знайдено дату: {date_str}")
            return date_str
    
    # Спроба 2: Шукаємо "у [день_тижня], [число] [місяць]"
    date_pattern_with_day = r'у\s+([\wʼ\']+),\s+(\d{1,2})\s+(' + '|'.join(months.keys()) + r')'
    
    matches = list(re.finditer(date_pattern_with_day, text, re.IGNORECASE))
    
    if debug and matches:
        log(f"   🔍 Знайдено {len(matches)} збігів з днем тижня")
    
    for idx, match in enumerate(matches, 1):
        day_of_week = match.group(1).lower()
        day_num = match.group(2)
        month_name = match.group(3).lower()
        
        if debug:
            log(f"   📍 Збіг {idx}: 'у {day_of_week}, {day_num} {month_name}'")
        
        # Перевіряємо що це дійсно день тижня
        days_of_week = [
            'понеділок', 'вівторок', 'середу', 'четвер', 'п\'ятницю', 'пʼятницю', 'суботу', 'неділю',
            'понеділка', 'вівторка', 'середи', 'четверга', 'п\'ятниці', 'пʼятниці', 'суботи', 'неділі'
        ]
        
        if day_of_week in days_of_week:
            if debug:
                log(f"   ✅ '{day_of_week}' - це день тижня!")
            
            day = day_num.zfill(2)
            month = months.get(month_name)
            
            if month:
                date_str = f"{day}.{month}.{datetime.now(TZ).year}"
                return date_str
    
    # Спроба 3: Шукаємо просто "[число] [місяць]" без дня тижня
    date_pattern_simple = r'(\d{1,2})\s+(' + '|'.join(months.keys()) + r')'
    
    matches_simple = list(re.finditer(date_pattern_simple, text, re.IGNORECASE))
    
    if debug and matches_simple:
        log(f"   🔍 Знайдено {len(matches_simple)} збігів без дня тижня")
    
    for idx, match in enumerate(matches_simple, 1):
        day_num = match.group(1)
        month_name = match.group(2).lower()
        
        if debug:
            log(f"   📍 Збіг {idx}: '{day_num} {month_name}'")
        
        day = day_num.zfill(2)
        month = months.get(month_name)
        
        if month:
            date_str = f"{day}.{month}.{datetime.now(TZ).year}"
            if debug:
                log(f"   ✅ Знайдено дату: {date_str}")
            return date_str
    
    return None


def parse_schedule_from_text(text: str) -> dict:
    """Парсить графік відключень з тексту для формату ЦЕК Дніпро"""
    result = {}
    
    # Ищем все группы и их позиции в тексте
    group_pattern = r'📌\s*(\d+\.\d+)\s*черг[аи]:'
    group_matches = list(re.finditer(group_pattern, text))
    
    if not group_matches:
        return result
    
    # Обрабатываем каждую группу
    for i, group_match in enumerate(group_matches):
        group_num = group_match.group(1)
        group_id = f"GPV{group_num}"
        
        # Инициализируем группу - по умолчанию везде есть свет
        result[group_id] = {str(h): "yes" for h in range(1, 25)}
        
        # Определяем границы текста для этой группы
        start_pos = group_match.end()
        if i + 1 < len(group_matches):
            # Есть следующая группа - берем текст до неё
            end_pos = group_matches[i + 1].start()
        else:
            # Последняя группа - берем до конца или до предупреждения
            warning_match = re.search(r'Попереджаємо', text[start_pos:])
            if warning_match:
                end_pos = start_pos + warning_match.start()
            else:
                end_pos = len(text)
        
        # Извлекаем текст для этой группы
        group_text = text[start_pos:end_pos]
        
        # Ищем все интервалы в тексте группы
        intervals = re.findall(r'з\s+(\d{1,2}:\d{2})\s+до\s+(\d{1,2}:\d{2})', group_text)
        
        for start_time, end_time in intervals:
            try:
                # Конвертируем время в часы (float)
                t1 = time_to_hour(start_time)
                t2 = time_to_hour(end_time)
                
                # Обрабатываем случай когда время переходит через полночь
                if t2 <= t1:  # например, з 23:30 до 02:30
                    # Разбиваем на два интервала: до полуночи и после полуночи
                    put_interval(result, group_id, t1, 24.0)  # до полуночи
                    put_interval(result, group_id, 0.0, t2)   # после полуночи
                else:
                    put_interval(result, group_id, t1, t2)
                    
            except Exception as e:
                log(f"⚠️ Помилка парсингу інтервалу {start_time}-{end_time}: {e}")
                continue
    
    return result


async def main():
    log("⏳ Завантажую Telegram-канал...")
    posts = await fetch_posts()
    
    if not posts:
        log("❌ Не знайдено постів з графіками")
        return False

    today = datetime.now(TZ).date()
    tomorrow = today + timedelta(days=1)
    today_str = today.strftime("%d.%m.%Y")
    tomorrow_str = tomorrow.strftime("%d.%m.%Y")

    results_for_all_dates = {}
    processed_dates = set()

    log(f"🔍 Обробка {len(posts)} постів...")
    
    for idx, post in enumerate(posts, 1):
        try:
            # Витягуємо дату з тексту (з debug для останніх постів)
            debug = (idx >= 10)
            date_str = extract_date_from_post(post['text'], debug=debug)
            
            if not date_str:
                # Debug: показуємо перші 300 символів тексту поста
                if idx >= 10:  # Тільки для останніх постів
                    log(f"📄 Пост {idx}: не знайдено дати в тексті")
                    log(f"   Початок тексту: {post['text'][:300]}")
                else:
                    log(f"📄 Пост {idx}: не знайдено дати в тексті")
                continue
            
            # Пропускаємо якщо не today/tomorrow
            if date_str not in (today_str, tomorrow_str):
                log(f"⏭️ Пост {idx}: {date_str} (не сьогодні/завтра)")
                continue
            
            # Пропускаємо якщо вже оброблено
            if date_str in processed_dates:
                log(f"ℹ️ Пост {idx}: {date_str} — вже оброблено")
                continue
            
            log(f"📅 Пост {idx}: обробляю графік для {date_str}")
            
            # Парсимо графік
            result = parse_schedule_from_text(post['text'])
            
            if not result:
                log(f"⚠️ Пост {idx}: не знайдено графіків у тексті")
                continue
            
            # Час оновлення - беремо поточний час
            current_time = datetime.now(TZ).strftime("%H:%M")
            log(f"🕒 Час оновлення: {current_time}")
            
            # Створюємо timestamp
            day_int, month_int, year_int = map(int, date_str.split("."))
            date_dt = datetime(year_int, month_int, day_int, tzinfo=TZ)
            date_ts = int(date_dt.timestamp())
            
            results_for_all_dates[str(date_ts)] = result
            processed_dates.add(date_str)
            log(f"✅ Додано графік для {date_str}: {len(result)} груп")
            
        except Exception as e:
            log(f"❌ Помилка обробки поста {idx}: {e}")
            continue

    if not results_for_all_dates:
        log("⚠️ Не знайдено жодних графіків відключень!")
        return False

    # Перевіряємо DIFF
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            old_json = json.load(f)
        old_data = old_json.get("fact", {}).get("data", {})

        if json.dumps(old_data, sort_keys=True) == json.dumps(results_for_all_dates, sort_keys=True):
            log("ℹ️ Дані не змінилися — JSON не оновлюємо")
            return False

    # Встановлюємо поточну дату і час оновлення
    update_formatted = datetime.now(TZ).strftime("%d.%m.%Y %H:%M")
    log(f"🕑 Фінальне оновлення: {update_formatted}")

    # Сортуємо дати від меншої до більшої
    sorted_results = dict(sorted(results_for_all_dates.items(), key=lambda x: int(x[0])))
    results_for_all_dates = sorted_results

    # Формуємо JSON
    new_json = {
        "regionId": "Dnipro",
        "lastUpdated": datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "fact": {
            "data": results_for_all_dates,
            "update": update_formatted,
            "today": int(datetime(today.year, today.month, today.day, tzinfo=TZ).timestamp())
        },
        "preset": {
            "time_zone": {
                str(i): [f"{i - 1:02d}-{i:02d}", f"{i - 1:02d}:00", f"{i:02d}:00"]
                for i in range(1, 25)
            },
            "time_type": {
                "yes": "Світло є",
                "maybe": "Можливе відключення",
                "no": "Світла немає",
                "first": "Світла не буде перші 30 хв.",
                "second": "Світла не буде другі 30 хв"
            }
        }
    }

    # Записуємо JSON
    log(f"💾 Записую JSON → {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(new_json, f, ensure_ascii=False, indent=2)

    log("✔️ JSON успішно оновлено")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            log("🎉 Парсинг завершено успішно")
        else:
            log("ℹ️ Парсинг завершено без оновлень")
    except KeyboardInterrupt:
        log("⚠️ Перервано користувачем")
    except Exception as e:
        log(f"❌ Фатальна помилка: {e}")
        import traceback
        log(traceback.format_exc())