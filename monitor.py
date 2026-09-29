import os
import requests
from playwright.sync_api import sync_playwright

# 讀取 GitHub Secrets 設定的 Telegram 金鑰
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_URL = "https://eipro.jp/takachiho1/eventCalendars/index"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 錯誤：未讀取到 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID！請確認 GitHub Secrets 名稱是否完全正確。")
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
            print("Telegram 回傳錯誤內容:", res.text)
    except Exception as e:
        print("Telegram 發送失敗:", e)

def check_reservation():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("1. 前往高千穗遊船預訂頁面...")
        page.goto(TARGET_URL, wait_until="networkidle")

        # 步驟 A：點擊「月」視圖按鈕
        print("2. 點擊「月」視圖按鈕...")
        try:
            page.click("text='月'", timeout=5000)
            page.wait_for_timeout(2000)
        except Exception as e:
            print("注意：點擊「月」按鈕時遇到狀況：", e)

        # 步驟 B：點擊切換下個月的箭頭 ▷ (切換至 10 月)
        print("3. 點擊右箭頭 ▷ 切換至 10 月...")
        try:
            # 優先嘗試尋找 2026/09 旁邊的右箭頭元素或文字
            next_button = page.locator("a, button, div, span").filter(has_text="▷").first
            if next_button.count() > 0:
                next_button.click()
            else:
                # 備用選擇器：點擊年月輸入框右側的箭頭
                page.click("div:has-text('2026/09') + *", timeout=5000)
            
            page.wait_for_timeout(3000) # 等待 3 秒載入 10 月 AJAX 月曆資料
            print("已成功切換至 10 月份資料！")
        except Exception as e:
            print("⚠️ 點擊切換下個月箭頭時失敗，請確認頁面狀態：", e)

        # 步驟 C：精準檢查 10 月 11、12、13 號
        print("4. 開始比對 10 月 11、12、13 號預訂狀態...")
        target_dates = ["11", "12", "13"]
        available_found = []

        # 抓取日曆表格中所有包含日期的單元格 (td / div)
        cells = page.query_selector_all("td, .fc-day, .calendar-day")
        for cell in cells:
            text = cell.inner_text().strip()
            for d in target_dates:
                # 確保該格子是 11, 12, 13 號（且屬於日期格子，非說明文字）
                if (text.startswith(d) or f"\n{d}" in text or f"/{d}" in text) and len(text) < 30:
                    # 如果格子內「沒有 ×」或包含「○ / △ / 沙漏」，代表釋出空位！
                    if "×" not in text and any(s in text for s in ["○", "△", "沙漏", "空", "予約"]):
                        if d not in available_found:
                            available_found.append(d)

        if True:
            dates_str = "、".join(available_found)
            msg = f"🎉 *【高千穗峽遊船】10月發現空位！*\n\n📅 日期：*10 月 {dates_str} 號*\n🔗 [點我立即前往預訂]({TARGET_URL})"
            print(f"✅ 發現空位：10 月 {dates_str} 號")
            send_telegram(msg)
        else:
            print("ℹ️ 檢查完成：10 月 11、12、13 號目前均仍無空位 (全為 ×)。")

        browser.close()

if __name__ == "__main__":
    check_reservation()
