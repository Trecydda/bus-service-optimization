import sys
import json
import time
import pathlib
from patchright.sync_api import sync_playwright # <-- Изменён импорт

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = pathlib.Path("data")
OUT_DIR.mkdir(exist_ok=True)

# Папка для хранения профиля браузера (куки, кеш и т.д.)
USER_DATA_DIR = pathlib.Path("chrome_profile")
USER_DATA_DIR.mkdir(exist_ok=True)

def main():
    with sync_playwright() as p:
        print("Запускаем браузер (Patchright, режим Chrome)...")
        
        # Используем launch_persistent_context для максимальной скрытности
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            channel="chrome",        # Используем установленный Google Chrome
            headless=False,
            no_viewport=True,        # Не задаём фиксированный размер окна
            # ВАЖНО: не добавляем кастомные User-Agent или заголовки
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        vids = set()
        
        def handle_response(response):
            if "getVehiclesMarkers.php" in response.url and response.status == 200:
                try:
                    data = response.json()
                    anims = data.get("anims", [])
                    for anim in anims:
                        vid = anim.get("vid") or anim.get("id")
                        if vid:
                            vids.add(vid)
                except Exception:
                    pass
        
        page.on("response", handle_response)
        
        print("Открываем карту и ждем загрузки транспорта...")
        # Ждём не только загрузки, но и появления первых данных о машинах
        page.goto("https://buscheb.ru/", wait_until="networkidle", timeout=60000)
        
        # Даём дополнительное время на инициализацию карты и запросов
        page.wait_for_timeout(7000)
        
        print(f"Браузер нашел {len(vids)} машин на карте!")
        
        if not vids:
            print("Машин не найдено. Проверьте, не появилась ли капча на экране.")
            context.close()
            return

        print("Начинаем сбор прогнозов...")
        for i, vid in enumerate(vids, 1):
            url = f"https://buscheb.ru/php/getVehicleForecasts.php?vid={vid}&type=0&city=cheboksari&info=12345&lang=ru&_={int(time.time()*1000)}"
            
            response = page.request.get(url)
            if response.ok:
                data = response.json()
                (OUT_DIR / f"{vid}.json").write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"[{i}/{len(vids)}] Сохранен vid={vid} (остановок: {len(data)})")
            else:
                print(f"[{i}/{len(vids)}] Ошибка для vid={vid}")
                
            time.sleep(1)

        context.close()
        print("\nГотово! Все файлы сохранены в папку 'data'.")

if __name__ == "__main__":
    main()