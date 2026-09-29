import os
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_URL = "https://eipro.jp/takachiho1/eventCalendars/index"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 錯誤：未讀取到 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID！請檢查 GitHub Secrets 設定。")
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

        print("3. 嘗試切換至 10 月...")
        switched = False
        
        # 多重 Selector 嘗試點擊 ▷ 箭頭
        arrow_selectors = [
            "a:has-text('▷')",
            "span:has-text('▷')",
            "button:has-text('▷')",
            "div:has-text('▷')",
            ".fc-button-next",
            "a[title*='Next']"
        ]

        for selector in arrow_selectors:
            try:
                if page.locator(selector).count() > 0:
                    page.click(selector, timeout=2000)
                    page.wait_for_timeout(2000)
                    switched = True
                    break
            except Exception:
                continue

        # 若文字定位失敗，執行 JS 強制點擊包含 ▷ 符號的元素
        if not switched:
            print("嘗試使用 JavaScript 強制點擊 ▷ 箭頭...")
            try:
                page.evaluate("""() => {
                    const elements = Array.from(document.querySelectorAll('*'));
                    const target = elements.find(el => el.children.length === 0 && el.textContent.includes('▷'));
                    if (target) target.click();
                }""")
                page.wait_for_timeout(2000)
            except Exception as e:
                print("JS 點擊失敗:", e)

        # 4. 安全檢查：驗證頁面是否確實載入 2026/10
        body_text = page.inner_text("body")
        if "2026/10" not in body_text and "10月" not in body_text:
            print("❌ 錯誤：頁面未成功切換至 10 月（目前仍停留在 9 月）。為防止誤報，本次檢查中斷！")
            browser.close()
            return
        
        print("✅ 成功確認頁面已載入 10 月份資料！")

        print("5. 開始精準檢查 10 月 11、12、13 號預訂狀態...")
        target_dates = ["11", "12", "13"]
        available_found = []

        cells = page.query_selector_all("td")
        for cell in cells:
            text = cell.inner_text().strip()
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            
            if lines and lines[0] in target_dates:
                d = lines[0]
                cell_content = " ".join(lines)
                print(f"🔍 [除錯 Log] 10 月 {d} 號內容為：'{cell_content}'")
                
                # 必須包含明確的可預訂標示 (○、△、空、予約)，且不能有 ×
                has_available_symbol = any(s in cell_content for s in ["○", "△", "空", "予約"])
                if "×" not in cell_content and has_available_symbol:
                    if d not in available_found:
                        available_found.append(d)

        if True:
            dates_str = "、".join(available_found)
            msg = f"🎉 *【高千穗峽遊船】10月發現空位！*\n\n📅 日期：*10 月 {dates_str} 號*\n🔗 [點我立即前往預訂]({TARGET_URL})"
            print(f"✅ 發現空位：10 月 {dates_str} 號")
            send_telegram(msg)
        else:
            print("ℹ️ 檢查完成：10 月 11、12、13 號目前均無空位 (全為 ×)。")

        browser.close()

if __name__ == "__main__":
    check_reservation()
