#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML-рендерер зображень через Playwright
Замінює старі Python/Pillow генератори на HTML/CSS підхід

Цей модуль відповідає за:
- Завантаження JSON даних з графіками відключень
- Підготовку HTML шаблонів з даними
- Рендеринг HTML в PNG через браузер Chromium
- Генерацію різних типів зображень (повний, аварійний, тижневий, матриця груп, картка)
"""

import asyncio
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
from typing import Dict, List, Optional, Tuple

from .config import config
from .logger import log


class HTMLRenderer:
    """
    Рендерер зображень через HTML/CSS шаблони
    
    Основні можливості:
    - Генерація 5 типів зображень (повний, аварійний, тижневий, матриця груп, картка)
    - Підтримка світлої теми
    - Автоматична підготовка даних для JavaScript
    - Очищення тимчасових файлів
    """
    
    def __init__(self, json_path: str):
        """
        Ініціалізація HTML рендерера
        
        Args:
            json_path: Шлях до JSON файлу з даними відключень
        """
        self.json_path = Path(json_path)
        self.templates_dir = config.TEMPLATES_DIR  # Нова папка templates
        self.output_dir = config.IMAGES_DIR  # Папка output/images
        self.data = self._load_json_data()
        
        # Створюємо вихідну папку якщо її немає
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_json_data(self) -> dict:
        """Завантажити JSON дані з файлу"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"Помилка завантаження JSON {self.json_path}: {e}")
            raise
            
    def _get_available_groups(self) -> List[str]:
        """Отримати список доступних GPV груп з JSON даних"""
        groups = set()
        
        # Шукаємо групи в fact.data (фактичні дані)
        if 'fact' in self.data and 'data' in self.data['fact']:
            for day_data in self.data['fact']['data'].values():
                if isinstance(day_data, dict):
                    for key in day_data.keys():
                        if key.startswith('GPV') and '.' in key:
                            groups.add(key)
        
        # Також шукаємо в preset.data (якщо є)
        if 'preset' in self.data and 'data' in self.data['preset']:
            for key in self.data['preset']['data'].keys():
                if key.startswith('GPV') and '.' in key:
                    groups.add(key)
        
        return sorted(list(groups))
    
    async def _render_template(self, template_name: str, output_path: str, 
                             gpv_key: Optional[str] = None, 
                             theme: str = "light",
                             day: Optional[str] = None,
                             scale: float = 2.0) -> Tuple[int, int]:
        """
        Рендерити HTML шаблон в PNG зображення
        
        Args:
            template_name: Назва HTML шаблону (наприклад, "full-template.html")
            output_path: Шлях для збереження PNG файлу
            gpv_key: Ключ GPV групи (наприклад, "GPV1.1")
            theme: Тема оформлення ("light" або "dark")
            day: День для відображення ("today" або "tomorrow")
            scale: Масштаб рендерингу (1.0 = звичайний, 2.0 = високий DPI)
            
        Returns:
            Tuple[int, int]: Ширина та висота згенерованого зображення
        """
        
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Шаблон не знайдено: {template_path}")
            
        # Створюємо тимчасовий HTML файл з даними
        temp_html = await self._prepare_template(template_path, gpv_key, theme, day)
        
        async with async_playwright() as p:
            # Запускаємо браузер Chromium
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                device_scale_factor=scale,  # Масштаб для високої якості
                viewport={'width': 1200, 'height': 800}  # Розмір вікна браузера
            )
            page = await context.new_page()
            
            try:
                # Завантажуємо HTML сторінку
                await page.goto(f"file://{temp_html.absolute()}")
                
                # Чекаємо повного завантаження
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(1000)  # Додаткова пауза для стабільності
                
                # Знаходимо контейнер для скріншоту
                container = page.locator('.container')
                await container.wait_for()
                
                # Робимо скріншот
                screenshot_bytes = await container.screenshot(
                    path=output_path,
                    type='png'
                )
                
                # Отримуємо розміри зображення
                box = await container.bounding_box()
                width = int(box['width'] * scale) if box else 0
                height = int(box['height'] * scale) if box else 0
                
                log(f"✅ Рендер завершено: {output_path} ({width}x{height})")
                return width, height
                
            finally:
                await browser.close()
                # Видаляємо тимчасовий файл
                if temp_html.exists():
                    temp_html.unlink()
    
    async def _prepare_template(self, template_path: Path, gpv_key: Optional[str], 
                              theme: str, day: Optional[str]) -> Path:
        """
        Підготувати HTML шаблон з даними
        
        Args:
            template_path: Шлях до HTML шаблону
            gpv_key: Ключ GPV групи (наприклад, "GPV1.1")
            theme: Тема оформлення ("light" або "dark")
            day: День для відображення ("today" або "tomorrow")
            
        Returns:
            Path: Шлях до підготовленого тимчасового HTML файлу
        """
        
        # Читаємо шаблон
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Створюємо тимчасову папку
        temp_dir = config.BASE_DIR / "temp_render"
        temp_dir.mkdir(exist_ok=True)
        
        # Копіюємо ресурси (CSS та JS файли)
        css_src = self.templates_dir / "css" / "schedule-shared.css"
        js_src = self.templates_dir / "js" / "schedule-shared.js"
        
        if css_src.exists():
            shutil.copy2(css_src, temp_dir / "schedule-shared.css")
        if js_src.exists():
            shutil.copy2(js_src, temp_dir / "schedule-shared.js")
                
        # Копіюємо іконки
        icons_dir = temp_dir / "icons"
        icons_dir.mkdir(exist_ok=True)
        assets_dir = self.templates_dir / "assets"
        if assets_dir.exists():
            for icon_file in assets_dir.glob("*.svg"):
                shutil.copy2(icon_file, icons_dir / icon_file.name)
            
        # Підготовлюємо дані для JavaScript
        prepared_data = self._prepare_data_for_js()
            
        # Додаємо дані в HTML через скрипт
        data_script = f"""
        <script>
            window.__SCHEDULE__ = {json.dumps(prepared_data, ensure_ascii=False)};
            {f'window.__GPV_KEY__ = "{gpv_key}";' if gpv_key else ''}
        </script>
        """
        
        # Вставляємо скрипт перед закриваючим </head>
        html_content = html_content.replace('</head>', f'{data_script}</head>')
        
        # Додаємо параметри теми та дня в URL через скрипт
        url_params = []
        if theme == "dark":
            url_params.append("theme=dark")
        if day:
            url_params.append(f"day={day}")
        if gpv_key:
            url_params.append(f"gpv={gpv_key}")
            
        if url_params:
            params_script = f"""
            <script>
                // Імітуємо URL параметри
                const mockUrl = new URL(window.location);
                {'; '.join([f'mockUrl.searchParams.set("{p.split("=")[0]}", "{p.split("=")[1]}")' for p in url_params])};
                Object.defineProperty(window, 'location', {{
                    value: mockUrl,
                    writable: false
                }});
            </script>
            """
            html_content = html_content.replace('</head>', f'{params_script}</head>')
        
        # Зберігаємо тимчасовий HTML файл
        temp_html = temp_dir / f"temp_{template_path.stem}_{datetime.now().timestamp()}.html"
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return temp_html
    
    def _prepare_data_for_js(self) -> dict:
        """
        Підготувати дані в форматі, очікуваному JavaScript кодом
        
        Цей метод:
        - Копіює вихідні JSON дані
        - Створює структуру preset.data з fact.data якщо її немає
        - Додає назви днів тижня українською мовою
        - Додає описи типів станів (світло є/нема/можливо)
        - Додає назви груп (Черга 1.1, Черга 2.2 тощо)
        
        Returns:
            dict: Підготовлені дані для JavaScript
        """
        prepared_data = self.data.copy()
        
        # Якщо немає preset.data, створюємо його з fact.data для сумісності
        if 'preset' not in prepared_data:
            prepared_data['preset'] = {}
            
        if 'data' not in prepared_data.get('preset', {}):
            # Створюємо preset.data на основі fact.data
            if 'fact' in prepared_data and 'data' in prepared_data['fact']:
                # Беремо перший день для створення структури preset
                first_day_data = next(iter(prepared_data['fact']['data'].values()), {})
                if first_day_data:
                    prepared_data['preset']['data'] = {}
                    
                    # Для кожної групи створюємо тижневу структуру
                    for gpv_key in first_day_data.keys():
                        if gpv_key.startswith('GPV'):
                            prepared_data['preset']['data'][gpv_key] = {
                                '1': first_day_data[gpv_key],  # Понеділок
                                '2': first_day_data[gpv_key],  # Вівторок  
                                '3': first_day_data[gpv_key],  # Середа
                                '4': first_day_data[gpv_key],  # Четвер
                                '5': first_day_data[gpv_key],  # П'ятниця
                                '6': first_day_data[gpv_key],  # Субота
                                '7': first_day_data[gpv_key],  # Неділя
                            }
        
        # Додаємо назви днів тижня, якщо їх немає
        if 'days' not in prepared_data.get('preset', {}):
            prepared_data['preset']['days'] = {
                '1': 'Понеділок',
                '2': 'Вівторок', 
                '3': 'Середа',
                '4': 'Четвер',
                '5': "П'ятниця",
                '6': 'Субота',
                '7': 'Неділя'
            }
            
        # Додаємо описи типів станів, якщо їх немає
        if 'time_type' not in prepared_data.get('preset', {}):
            prepared_data['preset']['time_type'] = {
                'yes': 'Світло є',
                'no': 'Світла нема',
                'maybe': 'Можливо відключення',
                'first': 'Перші 30 хв',
                'second': 'Другі 30 хв',
                'mfirst': 'Можливо перші 30 хв',
                'msecond': 'Можливо другі 30 хв'
            }
            
        # Додаємо назви груп, якщо їх немає
        if 'sch_names' not in prepared_data.get('preset', {}):
            prepared_data['preset']['sch_names'] = {}
            groups = self._get_available_groups()
            for group in groups:
                # GPV1.1 -> "Черга 1.1"
                group_num = group.replace('GPV', '')
                prepared_data['preset']['sch_names'][group] = f"Черга {group_num}"
        
        return prepared_data
    
    async def generate_full_schedule(self, theme: str = "light") -> str:
        """
        Генерувати повний графік (сьогодні + тиждень)
        
        Args:
            theme: Тема оформлення ("light" або "dark")
            
        Returns:
            str: Шлях до згенерованого PNG файлу
            
        Raises:
            ValueError: Якщо немає доступних GPV груп
        """
        groups = self._get_available_groups()
        if not groups:
            raise ValueError("Немає доступних GPV груп")
            
        gpv_key = groups[0]  # Беремо першу групу
        theme_suffix = "-dark" if theme == "dark" else ""
        output_file = f"gpv-full{theme_suffix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        output_path = str(self.output_dir / output_file)
        
        log(f"🖼️ Генерую повний графік для {gpv_key} (тема: {theme})")
        
        await self._render_template(
            "full-template.html",
            output_path,
            gpv_key=gpv_key,
            theme=theme
        )
        
        return output_path
    
    async def generate_emergency_schedule(self, gpv_key: str, theme: str = "light") -> str:
        """
        Генерувати аварійний графік для групи
        
        Args:
            gpv_key: Ключ GPV групи (наприклад, "GPV1.1")
            theme: Тема оформлення ("light" або "dark")
            
        Returns:
            str: Шлях до згенерованого PNG файлу
        """
        theme_suffix = "-dark" if theme == "dark" else ""
        group_num = gpv_key.replace('GPV', '').replace('.', '-')
        output_file = f"gpv-{group_num}-emergency{theme_suffix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        output_path = str(self.output_dir / output_file)
        
        log(f"🚨 Генерую аварійний графік для {gpv_key} (тема: {theme})")
        
        await self._render_template(
            "emergency-template.html",
            output_path,
            gpv_key=gpv_key,
            theme=theme
        )
        
        return output_path
    
    async def generate_week_schedule(self, gpv_key: str, theme: str = "light") -> str:
        """
        Генерувати тижневий графік
        
        Args:
            gpv_key: Ключ GPV групи (наприклад, "GPV1.1")
            theme: Тема оформлення ("light" або "dark")
            
        Returns:
            str: Шлях до згенерованого PNG файлу
        """
        theme_suffix = "-dark" if theme == "dark" else ""
        group_num = gpv_key.replace('GPV', '').replace('.', '-')
        output_file = f"gpv-{group_num}-week{theme_suffix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        output_path = str(self.output_dir / output_file)
        
        log(f"📅 Генерую тижневий графік для {gpv_key} (тема: {theme})")
        
        await self._render_template(
            "week-template.html",
            output_path,
            gpv_key=gpv_key,
            theme=theme
        )
        
        return output_path
    
    async def generate_groups_matrix(self, day: str = "today", theme: str = "light") -> str:
        """
        Генерувати матрицю всіх груп
        
        Args:
            day: День для відображення ("today" або "tomorrow")
            theme: Тема оформлення ("light" або "dark")
            
        Returns:
            str: Шлях до згенерованого PNG файлу
        """
        theme_suffix = "-dark" if theme == "dark" else ""
        day_suffix = "-tomorrow" if day == "tomorrow" else ""
        output_file = f"gpv-all-groups{day_suffix}{theme_suffix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        output_path = str(self.output_dir / output_file)
        
        log(f"📊 Генерую матрицю груп ({day}, тема: {theme})")
        
        await self._render_template(
            "groups-template.html",
            output_path,
            theme=theme,
            day=day
        )
        
        return output_path
    
    async def generate_summary_card(self, gpv_key: str, theme: str = "light") -> str:
        """
        Генерувати компактну картку для групи
        
        Args:
            gpv_key: Ключ GPV групи (наприклад, "GPV1.1")
            theme: Тема оформлення ("light" або "dark")
            
        Returns:
            str: Шлях до згенерованого PNG файлу
        """
        theme_suffix = "-dark" if theme == "dark" else ""
        group_num = gpv_key.replace('GPV', '').replace('.', '-')
        output_file = f"gpv-{group_num}-summary{theme_suffix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        output_path = str(self.output_dir / output_file)
        
        log(f"🎴 Генерую картку для {gpv_key} (тема: {theme})")
        
        await self._render_template(
            "summary-item.html",
            output_path,
            gpv_key=gpv_key,
            theme=theme
        )
        
        return output_path
    
    async def generate_all_for_group(self, gpv_key: str, theme: str = "light") -> Dict[str, str]:
        """
        Генерувати всі типи зображень для групи
        
        Args:
            gpv_key: Ключ GPV групи (наприклад, "GPV1.1")
            theme: Тема оформлення ("light" або "dark")
            
        Returns:
            Dict[str, str]: Словник з шляхами до згенерованих файлів
                           {'emergency': path, 'week': path, 'summary': path}
        """
        results = {}
        
        log(f"🎨 Генерую всі зображення для {gpv_key} (тема: {theme})")
        
        # Аварійний графік
        results['emergency'] = await self.generate_emergency_schedule(gpv_key, theme)
        
        # Тижневий графік  
        results['week'] = await self.generate_week_schedule(gpv_key, theme)
        
        # Картка
        results['summary'] = await self.generate_summary_card(gpv_key, theme)
        
        return results
    
    async def generate_all_images(self, theme: str = "light") -> Dict[str, any]:
        """
        Генерувати всі зображення
        
        Args:
            theme: Тема оформлення ("light" або "dark")
            
        Returns:
            Dict[str, any]: Результати генерації:
                - 'full': список шляхів до повних графіків
                - 'groups': список шляхів до матриць груп
                - 'individual': словник {gpv_key: {type: path}} для індивідуальних зображень
        """
        results = {
            'full': [],
            'groups': [],
            'individual': {}
        }
        
        log(f"🎨 Починаю генерацію всіх зображень (тема: {theme})")
        
        # Повний графік
        results['full'].append(await self.generate_full_schedule(theme))
        
        # Матриця груп (сьогодні та завтра)
        results['groups'].append(await self.generate_groups_matrix("today", theme))
        results['groups'].append(await self.generate_groups_matrix("tomorrow", theme))
        
        # Індивідуальні графіки для кожної групи
        groups = self._get_available_groups()
        for gpv_key in groups:
            results['individual'][gpv_key] = await self.generate_all_for_group(gpv_key, theme)
            
        log(f"✅ Генерація завершена! Створено зображень:")
        log(f"   - Повних графіків: {len(results['full'])}")
        log(f"   - Матриць груп: {len(results['groups'])}")
        log(f"   - Індивідуальних наборів: {len(results['individual'])}")
        
        return results
    
    def cleanup_temp(self):
        """Очистити тимчасові файли"""
        temp_dir = config.BASE_DIR / "temp_render"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


async def main():
    """Тестова функція для запуску HTML рендерера"""
    import sys
    
    if len(sys.argv) < 2:
        print("Використання: python html_renderer.py <path_to_json>")
        sys.exit(1)
        
    json_path = sys.argv[1]
    renderer = HTMLRenderer(json_path)
    
    try:
        # Генеруємо всі зображення (світла тема)
        await renderer.generate_all_images("light")
        
    finally:
        renderer.cleanup_temp()


if __name__ == "__main__":
    asyncio.run(main())