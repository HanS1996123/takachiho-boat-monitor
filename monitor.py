import os
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_URL = "https://eipro.jp/takachiho1/eventCalendars/index"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("未設定 Telegram Token 或 Chat ID")
        return
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(api_url, json=payload, timeout=10)
        print("Telegram 發送結果狀態碼:", res.status_code)
    except Exception as e:
        print("Telegram 發送失敗:", e)

def check_reservation():
    with sync_playwright() as p:
        # 啟動雲端無頭瀏覽器
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("1. 正在前往高千穗遊船預訂頁面...")
        page.goto(TARGET_URL, wait_until="networkidle")

        # 自動點擊「月」視圖按鈕，解決重新整理跳回週視圖問題
        print("2. 自動按鈕點擊：切換至月檢視模式...")
        try:
            page.click("text='月'", timeout=5000)
            page.wait_for_timeout(3000)  # 等待 3 秒讓 AJAX 月曆資料完整載入
        except Exception as e:
            print("注意：未找到月按鈕或已在月檢視狀態：", e)

        print("3. 讀取月曆 11、12、13 號狀態...")
        target_dates = ["11", "12", "13"]
        available_found = []

        # 抓取頁面上所有表格單元格並比對文字
        cells = page.query_selector_all("td, th, .calendar-cell, div")
        for cell in cells:
            text = cell.inner_text().strip()
            for d in target_dates:
                # 若儲存格包含目標日期數字，且文字中沒有 '×'，代表狀態改變（有空位）
                if d in text and "×" not in text and len(text) < 15:
                    if d not in available_found:
                        available_found.append(d)

        if available_found:
            dates_str = "、".join(available_found)
            msg = f"🎉 *【高千穗峽遊船】發現空位！*\n\n📅 日期：*{dates_str} 號*\n🔗 [點我前往預訂頁面]({TARGET_URL})"
            send_telegram(msg)
            print(f"發現空位！日期：{dates_str}")
        else:
            print("檢查完成：11、12、13 號目前均仍為 × (無空位)。")

        browser.close()

if __name__ == "__main__":
    check_reservation()
