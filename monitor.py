import os
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_URL = "https://eipro.jp/takachiho1/eventCalendars/index"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 錯誤：未讀取到 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID，請檢查 GitHub Secrets 設定！")
        return
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(api_url, json=payload, timeout=10)
        print(f"Telegram 發送結果狀態碼: {res.status_code}")
        if res.status_code != 200:
            print("Telegram 回傳錯誤:", res.text)
    except Exception as e:
        print("Telegram 發送失敗:", e)

def check_reservation():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("1. 正在前往預訂頁面...")
        page.goto(TARGET_URL, wait_until="networkidle")

        print("2. 自動切換至「月」檢視模式...")
        try:
            page.click("text='月'", timeout=5000)
            page.wait_for_timeout(3000)
        except Exception as e:
            print("未點擊到月按鈕或已在月檢視：", e)

        print("3. 解析日曆表格資料...")
        target_dates = ["11", "12", "13"]
        available_found = []

        # 精準抓取日曆表格（table）中的列（tr）與儲存格
        rows = page.query_selector_all("table tr")
        for row in rows:
            text = row.inner_text().strip()
            # 只有當這一列屬於日曆內容（包含 ×、○、沙漏等狀態符號）時才進行分析
            if any(symbol in text for symbol in ["×", "○", "△", "沙漏"]):
                for d in target_dates:
                    # 比對日期：確保該欄位包含目標日期，且狀態「不包含 ×」
                    if f"{d}日" in text or f"/{d}" in text or text.startswith(d):
                        if "×" not in text:
                            if d not in available_found:
                                available_found.append(d)

        if available_found:
            dates_str = "、".join(available_found)
            msg = f"🎉 *【高千穗峽遊船】發現空位！*\n\n📅 日期：*{dates_str} 號*\n🔗 [點我前往預訂頁面]({TARGET_URL})"
            print(f"✅ 發現空位：{dates_str}")
            send_telegram(msg)
        else:
            print("ℹ️ 檢查完成：11、12、13 號目前均無空位 (仍為 ×)。")

        browser.close()

if __name__ == "__main__":
    check_reservation()
