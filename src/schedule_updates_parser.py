#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер обновлений графиков отключений электроэнергии
Обрабатывает сообщения об изменениях в существующих графиках
"""

import re
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .config import config
from .logger import log

TZ = ZoneInfo("Europe/Kyiv")

# Ключевые слова для поиска сообщений об обновлениях
UPDATE_KEYWORDS = [
    "додатково застосовуватиметься відключення",
    "продовжується до",
    "відключення продовжується",
    "додатково відключення",
    "за командою диспетчерського центру",
    "НЕК \"Укренерго\"",
    "підчерги",
    "черги"
]


def is_update_message(text: str) -> bool:
    """Проверяет, является ли сообщение обновлением графика"""
    if not text:
        return False
    
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in UPDATE_KEYWORDS)


def time_to_hour(hhmm: str) -> float:
    """Конвертирует время HH:MM в часы (float)"""
    hh, mm = map(int, hhmm.split(":"))
    return hh + (mm / 60.0)


def put_interval_update(result: dict, group_id: str, t1: float, t2: float) -> None:
    """Применяет интервал отключения к существующему графику"""
    for hour in range(1, 25):
        h_start = float(hour - 1)  # час 1 = 0:00-1:00
        h_mid = h_start + 0.5
        h_end = h_start + 1.0

        first_off = (t1 < h_mid and t2 > h_start)
        second_off = (t1 < h_end and t2 > h_mid)

        if not first_off and not second_off:
            continue

        key = str(hour)
        
        # Если группы еще нет, создаем с дефолтными значениями
        if group_id not in result:
            result[group_id] = {str(h): "yes" for h in range(1, 25)}

        # Применяем отключение
        if first_off and second_off:
            result[group_id][key] = "no"
        elif first_off:
            # Если уже есть отключение во второй половине, делаем полное отключение
            if result[group_id][key] == "second":
                result[group_id][key] = "no"
            else:
                result[group_id][key] = "first"
        elif second_off:
            # Если уже есть отключение в первой половине, делаем полное отключение
            if result[group_id][key] == "first":
                result[group_id][key] = "no"
            else:
                result[group_id][key] = "second"


def parse_group_number(text: str) -> List[str]:
    """Извлекает номера подгрупп из текста"""
    groups = []
    
    # Ищем паттерны типа "підчерги 4.2", "черги 5.1" и т.д.
    patterns = [
        r'підчерги\s+(\d+\.\d+)',
        r'черги\s+(\d+\.\d+)',
        r'підчерга\s+(\d+\.\d+)',
        r'черга\s+(\d+\.\d+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            group_id = f"GPV{match}"
            if group_id not in groups:
                groups.append(group_id)
    
    return groups


def parse_time_intervals(text: str) -> List[Tuple[float, float]]:
    """Извлекает временные интервалы из текста"""
    intervals = []
    
    # Паттерн 1: "з 01:00 до 05:00"
    pattern1 = r'з\s+(\d{1,2}:\d{2})\s+до\s+(\d{1,2}:\d{2})'
    matches1 = re.findall(pattern1, text)
    
    for start_time, end_time in matches1:
        try:
            t1 = time_to_hour(start_time)
            t2 = time_to_hour(end_time)
            intervals.append((t1, t2))
        except Exception as e:
            log(f"⚠️ Ошибка парсинга интервала {start_time}-{end_time}: {e}")
    
    # Паттерн 2: "продовжується до 11:30"
    pattern2 = r'продовжується до\s+(\d{1,2}:\d{2})'
    matches2 = re.findall(pattern2, text)
    
    for end_time in matches2:
        try:
            # Для "продовжується до" начальное время берем как текущее время
            current_hour = datetime.now(TZ).hour
            current_minute = datetime.now(TZ).minute
            t1 = current_hour + (current_minute / 60.0)
            t2 = time_to_hour(end_time)
            
            # Если время окончания меньше текущего, значит это завтра
            if t2 <= t1:
                t2 += 24.0
            
            intervals.append((t1, t2))
        except Exception as e:
            log(f"⚠️ Ошибка парсинга времени окончания {end_time}: {e}")
    
    return intervals


def apply_schedule_update(json_data: dict, groups: List[str], intervals: List[Tuple[float, float]], 
                         target_date: Optional[str] = None) -> bool:
    """
    Применяет обновления к существующему графику
    
    Args:
        json_data: Данные JSON с графиками
        groups: Список групп для обновления (например, ["GPV4.2", "GPV5.2"])
        intervals: Список временных интервалов для отключения
        target_date: Целевая дата (если None, применяется к сегодняшней дате)
    
    Returns:
        bool: True если были внесены изменения
    """
    if not groups or not intervals:
        return False
    
    # Определяем целевую дату
    if target_date is None:
        today = datetime.now(TZ).date()
        target_timestamp = str(int(datetime(today.year, today.month, today.day, tzinfo=TZ).timestamp()))
    else:
        # Парсим дату из строки DD.MM.YYYY
        day, month, year = map(int, target_date.split("."))
        target_timestamp = str(int(datetime(year, month, day, tzinfo=TZ).timestamp()))
    
    # Проверяем есть ли данные для этой даты
    fact_data = json_data.get("fact", {}).get("data", {})
    if target_timestamp not in fact_data:
        log(f"⚠️ Нет данных для даты {target_date or 'сегодня'} (timestamp: {target_timestamp})")
        return False
    
    date_data = fact_data[target_timestamp]
    changes_made = False
    
    # Применяем обновления для каждой группы
    for group_id in groups:
        if group_id not in date_data:
            log(f"⚠️ Группа {group_id} не найдена в данных")
            continue
        
        # Сохраняем исходное состояние для сравнения
        original_state = date_data[group_id].copy()
        
        # Применяем все интервалы отключений
        for t1, t2 in intervals:
            # Обрабатываем случай когда время переходит через полночь
            if t2 > 24.0:
                # Разбиваем на два интервала: до полуночи и после полуночи
                put_interval_update({group_id: date_data[group_id]}, group_id, t1, 24.0)
                put_interval_update({group_id: date_data[group_id]}, group_id, 0.0, t2 - 24.0)
            else:
                put_interval_update({group_id: date_data[group_id]}, group_id, t1, t2)
        
        # Проверяем были ли изменения
        if date_data[group_id] != original_state:
            changes_made = True
            log(f"✅ Обновлена группа {group_id}")
            
            # Логируем изменения
            for hour in range(1, 25):
                hour_key = str(hour)
                old_val = original_state[hour_key]
                new_val = date_data[group_id][hour_key]
                if old_val != new_val:
                    log(f"   Час {hour:2d}: {old_val} → {new_val}")
    
    if changes_made:
        # Обновляем время последнего обновления
        json_data["lastUpdated"] = datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        json_data["fact"]["update"] = datetime.now(TZ).strftime("%d.%m.%Y %H:%M")
    
    return changes_made


def process_update_message(text: str) -> Optional[Dict]:
    """
    Обрабатывает сообщение об обновлении графика
    
    Returns:
        Dict с информацией об обновлении или None если не удалось распарсить
    """
    if not is_update_message(text):
        return None
    
    # Извлекаем группы
    groups = parse_group_number(text)
    if not groups:
        log("⚠️ Не найдены номера групп в сообщении об обновлении")
        return None
    
    # Извлекаем временные интервалы
    intervals = parse_time_intervals(text)
    if not intervals:
        log("⚠️ Не найдены временные интервалы в сообщении об обновлении")
        return None
    
    return {
        "groups": groups,
        "intervals": intervals,
        "original_text": text
    }


def update_schedule_from_message(message_text: str, target_date: Optional[str] = None) -> bool:
    """
    Основная функция для обновления графика на основе сообщения
    
    Args:
        message_text: Текст сообщения об обновлении
        target_date: Целевая дата в формате DD.MM.YYYY (если None, используется сегодня)
    
    Returns:
        bool: True если график был обновлен
    """
    # Парсим сообщение
    update_info = process_update_message(message_text)
    if not update_info:
        log("❌ Не удалось распарсить сообщение об обновлении")
        return False
    
    log(f"📝 Найдено обновление для групп: {', '.join(update_info['groups'])}")
    log(f"⏰ Временные интервалы: {update_info['intervals']}")
    
    # Загружаем существующий JSON
    json_path = config.get_json_path()
    if not json_path.exists():
        log(f"❌ JSON файл не найден: {json_path}")
        return False
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as e:
        log(f"❌ Ошибка чтения JSON файла: {e}")
        return False
    
    # Применяем обновления
    changes_made = apply_schedule_update(
        json_data, 
        update_info["groups"], 
        update_info["intervals"], 
        target_date
    )
    
    if not changes_made:
        log("ℹ️ Изменения не были внесены")
        return False
    
    # Сохраняем обновленный JSON
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        log(f"✅ График обновлен и сохранен в {json_path}")
        return True
    except Exception as e:
        log(f"❌ Ошибка сохранения JSON файла: {e}")
        return False


# Функция для тестирования
def test_parser():
    """Тестирует парсер на примерах сообщений"""
    test_messages = [
        "📢 Шановні споживачі! Попереджаємо, що за командою диспетчерського центру НЕК \"Укренерго\", з 01:00 до 05:00 додатково застосовуватиметься відключення підчерги 4.2‼️",
        "📢 Шановні споживачі! Попереджаємо, що за командою диспетчерського центру НЕК \"Укренерго\", відключення підчерги 5.2 продовжується до 11:30!!",
        "Додатково застосовуватиметься відключення черги 3.1 з 14:00 до 18:00",
    ]
    
    for i, message in enumerate(test_messages, 1):
        log(f"\n=== Тест {i} ===")
        log(f"Сообщение: {message}")
        
        result = process_update_message(message)
        if result:
            log(f"✅ Группы: {result['groups']}")
            log(f"✅ Интервалы: {result['intervals']}")
        else:
            log("❌ Не удалось распарсить")


if __name__ == "__main__":
    test_parser()