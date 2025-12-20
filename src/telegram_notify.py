import requests
import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# --- Завантажуємо .env ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # вихід із /src
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# --- Логи ---
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "telegram_notify.log")
FULL_LOG_FILE = os.path.join(LOG_DIR, "full_log.log")

def log(message):
    timestamp = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} [telegram_notify] {message}"
    print(line)
    #with open(LOG_FILE, "a", encoding="utf-8") as f:
    #    f.write(line + "\n")
    with open(FULL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def calculate_daily_stats(data, day_key):
    """Розрахувати статистику дня для всіх груп"""
    if "fact" not in data or "data" not in data["fact"]:
        return None
    
    day_data = data["fact"]["data"].get(day_key, {})
    if not day_data:
        return None
    
    total_groups = len(day_data)
    total_hours = 24
    
    # Статистика по всіх групах
    total_available_hours = 0
    total_outage_hours = 0
    longest_outages = []
    
    for group_name, group_hours in day_data.items():
        available_hours = 0
        outage_hours = 0
        current_outage_start = None
        current_outage_duration = 0
        group_outages = []
        
        for hour in range(1, 25):  # 1-24
            hour_key = str(hour)
            status = group_hours.get(hour_key, "yes")
            
            if status in ["no", "first", "second"]:  # Відключення
                outage_hours += 1
                if current_outage_start is None:
                    current_outage_start = hour - 1  # 0-23 для відображення
                current_outage_duration += 1
            else:  # Світло є
                available_hours += 1
                if current_outage_start is not None:
                    # Закінчилося відключення
                    end_hour = hour - 2  # 0-23
                    group_outages.append({
                        'start': current_outage_start,
                        'end': end_hour,
                        'duration': current_outage_duration
                    })
                    current_outage_start = None
                    current_outage_duration = 0
        
        # Якщо відключення триває до кінця дня
        if current_outage_start is not None:
            group_outages.append({
                'start': current_outage_start,
                'end': 23,
                'duration': current_outage_duration
            })
        
        total_available_hours += available_hours
        total_outage_hours += outage_hours
        
        # Знаходимо найдовше відключення для цієї групи
        if group_outages:
            longest_group_outage = max(group_outages, key=lambda x: x['duration'])
            longest_outages.append({
                'group': group_name,
                'start': longest_group_outage['start'],
                'end': longest_group_outage['end'],
                'duration': longest_group_outage['duration']
            })
    
    # Середні показники
    avg_available = total_available_hours / total_groups if total_groups > 0 else 0
    avg_outage = total_outage_hours / total_groups if total_groups > 0 else 0
    
    # Найдовше відключення серед всіх груп
    longest_outage = max(longest_outages, key=lambda x: x['duration']) if longest_outages else None
    
    return {
        'total_groups': total_groups,
        'avg_available_hours': round(avg_available, 1),
        'avg_outage_hours': round(avg_outage, 1),
        'longest_outage': longest_outage
    }


def find_next_outage(data, day_key, current_hour=None):
    """Знайти наступне відключення"""
    if current_hour is None:
        current_hour = datetime.now(ZoneInfo("Europe/Kyiv")).hour
    
    if "fact" not in data or "data" not in data["fact"]:
        return None
    
    day_data = data["fact"]["data"].get(day_key, {})
    if not day_data:
        return None
    
    # Шукаємо найближче відключення серед всіх груп
    next_outages = []
    
    for group_name, group_hours in day_data.items():
        for hour in range(current_hour + 1, 25):  # Від наступної години до кінця дня
            hour_key = str(hour)
            status = group_hours.get(hour_key, "yes")
            
            if status in ["no", "first", "second"]:
                # Знайшли початок відключення, тепер знаходимо кінець
                start_hour = hour - 1  # 0-23 для відображення
                end_hour = start_hour
                duration = 1
                
                # Шукаємо кінець відключення
                for next_hour in range(hour + 1, 25):
                    next_hour_key = str(next_hour)
                    next_status = group_hours.get(next_hour_key, "yes")
                    if next_status in ["no", "first", "second"]:
                        end_hour = next_hour - 1
                        duration += 1
                    else:
                        break
                
                hours_until = hour - 1 - current_hour
                next_outages.append({
                    'group': group_name,
                    'start': start_hour,
                    'end': end_hour,
                    'duration': duration,
                    'hours_until': hours_until
                })
                break  # Знайшли перше відключення для цієї групи
    
    if not next_outages:
        return None
    
    # Повертаємо найближче відключення
    return min(next_outages, key=lambda x: x['hours_until'])


def format_time(hour):
    """Форматувати час у вигляді ГГ:00"""
    return f"{hour:02d}:00"


def create_stats_message(data, day_key):
    """Створити повідомлення зі статистикою"""
    stats = calculate_daily_stats(data, day_key)
    next_outage = find_next_outage(data, day_key)
    
    if not stats:
        return "❌ Не вдалося розрахувати статистику"
    
    # Дата
    dt = datetime.fromtimestamp(int(day_key), ZoneInfo("Europe/Kyiv"))
    date_str = f"{dt.day} грудня"
    
    message = f"📊 <b>Статистика на {date_str}:</b>\n\n"
    message += f"⚡ <b>Світло є:</b> {stats['avg_available_hours']} годин (в середньому)\n"
    message += f"🔌 <b>Відключення:</b> {stats['avg_outage_hours']} годин (в середньому)\n"
    
    if stats['longest_outage']:
        lo = stats['longest_outage']
        start_time = format_time(lo['start'])
        end_time = format_time(lo['end'] + 1)
        message += f"📈 <b>Найдовше відключення:</b> {lo['duration']} годин ({start_time}-{end_time})\n"
        message += f"   Група: {lo['group'].replace('GPV', '')}\n"
    
    if next_outage:
        no = next_outage
        start_time = format_time(no['start'])
        end_time = format_time(no['end'] + 1)
        
        message += f"\n⏰ <b>Наступне відключення:</b>\n"
        if no['hours_until'] > 0:
            message += f"🔴 Через {no['hours_until']} годин\n"
        else:
            message += f"🔴 Зараз або незабаром\n"
        message += f"⏱️ З {start_time} до {end_time} ({no['duration']} годин)\n"
        message += f"   Група: {no['group'].replace('GPV', '')}"
    else:
        message += f"\n✅ <b>Наступних відключень сьогодні не заплановано</b>"
    
    return message


# --- Відправка фото з підписом ---
def send_photo(image_path, caption=None, with_stats=True):
    if not TOKEN or not CHAT_ID:
        log("❌ BOT_TOKEN або ADMIN_CHAT_ID не встановлені!")
        return

    if not os.path.exists(image_path):
        log(f"⚠️ Фото не знайдено: {image_path}")
        return

    try:
        # Якщо потрібно додати статистику
        if with_stats and caption:
            # Спробуємо завантажити JSON для статистики
            json_dir = os.path.join(BASE_DIR, "out")
            json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
            if json_files:
                json_path = os.path.join(json_dir, json_files[0])  # Беремо перший JSON
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Знаходимо сьогоднішню дату
                    fact_data = data.get("fact", {}).get("data", {})
                    if fact_data:
                        day_keys = list(fact_data.keys())
                        if day_keys:
                            today_key = day_keys[0]  # Беремо першу доступну дату
                            stats_message = create_stats_message(data, today_key)
                            caption = f"{caption}\n\n{stats_message}"
                except Exception as e:
                    log(f"⚠️ Не вдалося додати статистику: {e}")

        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        with open(image_path, "rb") as img:
            # Додаємо звуковий сигнал для важливих повідомлень
            data_params = {
                "chat_id": CHAT_ID, 
                "caption": caption or "", 
                "parse_mode": "HTML",
                "disable_notification": False  # Увімкнути звук
            }
            requests.post(url, data=data_params, files={"photo": img})
        
        caption_short = (caption or "").replace("\n", " ")[:100] + "..." if len(caption or "") > 100 else (caption or "")
        log(f"✅ Відправлено фото: {image_path} з підписом: {caption_short}")

    except Exception as e:
        log(f"❌ Помилка при відправленні фото: {e}")

def send_error(text, urgent=True):
    if not TOKEN or not CHAT_ID:
        log("❌ BOT_TOKEN або ADMIN_CHAT_ID не встановлені!")
        return

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": f"🚨 <b>DNIPRO_PARSER ERROR</b>\n{text}",
            "parse_mode": "HTML",
            "disable_notification": not urgent  # Звук тільки для термінових помилок
        }
        requests.post(url, data=data)
        log(f"⚠️ Відправлено помилку: {text}")

    except Exception as e:
        log(f"❌ Помилка при відправленні error: {e}")

def send_message(text, urgent=False):
    if not TOKEN or not CHAT_ID:
        log("❌ BOT_TOKEN або ADMIN_CHAT_ID не встановлені!")
        return

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": f"📢 <b>DNIPRO_PARSER</b>\n{text}",
            "parse_mode": "HTML",
            "disable_notification": not urgent  # Звук тільки для термінових повідомлень
        }
        requests.post(url, data=data)
        log(f"Відправлено повідомлення: {text}")

    except Exception as e:
        log(f"❌ Помилка при відправленні повідомлення: {e}")

def send_stats_only():
    """Відправити тільки статистику без зображення"""
    try:
        json_dir = os.path.join(BASE_DIR, "out")
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        if not json_files:
            send_message("❌ Немає даних для статистики")
            return
        
        json_path = os.path.join(json_dir, json_files[0])
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        fact_data = data.get("fact", {}).get("data", {})
        if not fact_data:
            send_message("❌ Немає даних для статистики")
            return
        
        day_keys = list(fact_data.keys())
        if not day_keys:
            send_message("❌ Немає даних для статистики")
            return
        
        today_key = day_keys[0]
        stats_message = create_stats_message(data, today_key)
        send_message(stats_message)
        
    except Exception as e:
        log(f"❌ Помилка при відправленні статистики: {e}")
        send_error(f"Помилка при відправленні статистики: {e}")
