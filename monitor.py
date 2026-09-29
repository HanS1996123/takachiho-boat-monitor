import os
import requests
from playwright.sync_api import sync_playwright

# 讀取 GitHub Secrets 設定
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_URL = "https://eipro.jp/takachiho1/eventCalendars/index"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 錯誤：未讀取到 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID！")
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

        print("2. 點擊「月」視圖按鈕...")
        try:
            page.click("text='月'", timeout=5000)
            page.wait_for_timeout(2000)
        except Exception as e:
            print("注意：點擊「月」按鈕狀況：", e)

        print("3. 點擊右箭頭 ▷ 切換至 10 月...")
        try:
            next_btn = page.locator("a, button, div, span").filter(has_text="▷").first
            if next_btn.count() > 0:
                next_btn.click()
            else:
                page.click("text='▷'", timeout=5000)
            page.wait_for_timeout(3000)
            print("已成功切換至 10 月份資料！")
        except Exception as e:
            print("⚠️ 點擊切換 10 月箭頭失敗：", e)

        print("4. 開始精準檢查 10 月 11、12、13 號預訂狀態...")
        target_dates = ["11", "12", "13"]
        available_found = []

        # 精準檢查每一個月曆單元格
        cells = page.query_selector_all("td")
        for cell in cells:
            text = cell.inner_text().strip()
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            
            # 若單元格的第一行恰好是目標日期 (11, 12, 13)
            if lines and lines[0] in target_dates:
                d = lines[0]
                cell_content = " ".join(lines)
                print(f"🔍 [除錯 Log] 10 月 {d} 號內容為：'{cell_content}'")
                
                # 只有當內容明確包含可預訂標示（○、△、空）且不包含 × 時，才認定有空位
                if "×" not in cell_content and any(s in cell_content for s in ["○", "△", "空", "予約"]):
                    if d not in available_found:
                        available_found.append(d)

        if available_found:
            dates_str = "、".join(available_found)
            msg = f"🎉 *【高千穗峽遊船】10月發現空位！*\n\n📅 日期：*10 月 {dates_str} 號*\n🔗 [點我立即前往預訂]({TARGET_URL})"
            print(f"✅ 發現空位：10 月 {dates_str} 號")
            send_telegram(msg)
        else:
            print("ℹ️ 檢查完成：10 月 11、12、13 號目前均無空位 (全為 ×)。")

        browser.close()

if __name__ == "__main__":
    check_reservation()
