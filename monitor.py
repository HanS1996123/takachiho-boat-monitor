import os
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_URL = "https://eipro.jp/takachiho1/eventCalendars/index"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 錯誤：未設定 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID！")
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

        print("2. 切換至「月」視圖...")
        try:
            page.click("text='月'", timeout=5000)
            page.wait_for_timeout(2000)
        except Exception as e:
            print("注意：點擊「月」按鈕狀況：", e)

        print("3. 切換至 10 月...")
        switched = False
        arrow_selectors = ["a:has-text('▷')", "span:has-text('▷')", "button:has-text('▷')", ".fc-button-next"]
        for sel in arrow_selectors:
            try:
                if page.locator(sel).count() > 0:
                    page.click(sel, timeout=2000)
                    switched = True
                    break
            except Exception:
                continue

        if not switched:
            page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('*'));
                const target = elements.find(el => el.children.length === 0 && el.textContent.includes('▷'));
                if (target) target.click();
            }""")

        # 等待 4 秒確保 AJAX 與動態圖像完整載入
        page.wait_for_timeout(4000)

        # 驗證月份
        body_text = page.inner_text("body")
        if "2026/10" not in body_text and "10月" not in body_text:
            print("❌ 錯誤：頁面未切換至 10 月，本次檢查中斷！")
            browser.close()
            return

        print("✅ 成功切換至 10 月份頁面！")

        print("4. 開始詳細剖析 10 月 11、12、13 號 HTML 內容...")
        target_dates = ["6", "12", "13"]
        available_found = []

        # 搜尋日曆中所有的單元格
        cells = page.query_selector_all("td")
        for cell in cells:
            text = cell.inner_text().strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            
            # 精準比對：只有當第一行數字「完全等於」11、12 或 13 時才處理
            if lines and lines[0] in target_dates:
                d = lines[0]
                html_content = cell.inner_html().strip()
                
                # 在 Log 記錄完整的 HTML 碼供除錯（防範圖片或 class 標示）
                print(f"🔍 [除錯 Log] 10 月 {d} 號 HTML 碼：{html_content}")

                # 判定不可預訂的關鍵特徵 (文字、圖片檔名或 class)
                blocked_keywords = ["×", "✕", "沙漏", "close", "soldout", "ng", "batsu", "disabled"]
                is_blocked = any(kw in html_content.lower() for kw in blocked_keywords)

                # 判定可預訂的關鍵特徵
                available_keywords = ["○", "△", "空", "予約", "ok", "open", "maru"]
                has_available = any(kw in html_content.lower() for kw in available_keywords)

                # 只有在「沒有不可預訂特徵」且「有可預訂標示」時，才認定有空位
                if not is_blocked and has_available:
                    if d not in available_found:
                        available_found.append(d)

        if available_found:
            dates_str = "、".join(sorted(available_found))
            msg = f"🎉 *【高千穗峽遊船】10月發現空位！*\n\n📅 可預訂日期：*10 月 {dates_str} 號*\n🔗 [點我立即前往預訂]({TARGET_URL})"
            print(f"✅ 發現空位：10 月 {dates_str} 號")
            send_telegram(msg)
        else:
            print("ℹ️ 檢查完成：10 月 11、12、13 號目前均無開放空位。")

        browser.close()

if __name__ == "__main__":
    check_reservation()
