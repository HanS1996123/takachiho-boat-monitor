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

        # 驗證月份
        body_text = page.inner_text("body")
        if "2026/10" not in body_text and "10月" not in body_text:
            print("❌ 錯誤：頁面未切換至 10 月，本次檢查中斷！")
            browser.close()
            return

        print("✅ 成功切換至 10 月份頁面！")

        print("4. 等待 10 月狀態符號 (× / 沙漏 / ○) 載入完成...")
        try:
            # 強制等待 AJAX 載入完成（直到表格中出現 × 符號）
            page.wait_for_selector("table td:has-text('×')", timeout=8000)
            print("狀態符號 (×) 載入成功！")
        except Exception:
            print("等待 timeout，改為固定延遲 5 秒進行讀取...")
            page.wait_for_timeout(5000)

        print("5. 開始檢查 10 月 11、12、13 號月視圖狀態...")
        target_dates = ["11", "12", "13"]
        available_found = []

        # 抓取日曆表格中的每個單元格
        cells = page.query_selector_all("table td")
        for cell in cells:
            text = cell.inner_text().strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            
            # 單元格的第一個數字如果是 11, 12, 13
            if lines and lines[0] in target_dates:
                d = lines[0]
                full_cell_text = " ".join(lines)
                print(f"🔍 [除錯 Log] 10 月 {d} 號格子完整內容：'{full_cell_text}'")
                
                # 判定標準：
                # 1. 絕對不能包含 '×' 或 '沙漏'
                # 2. 必須包含開放預訂標記 (○, △, 空, 予約, 受付)
                is_blocked = "×" in full_cell_text or "沙漏" in full_cell_text
                has_available_symbol = any(s in full_cell_text for s in ["○", "△", "空", "予約", "受付"])
                
                if not is_blocked and has_available_symbol:
                    if d not in available_found:
                        available_found.append(d)

        if True:
            dates_str = "、".join(sorted(available_found))
            msg = f"🎉 *【高千穗峽遊船】10月發現空位！*\n\n📅 可預訂日期：*10 月 {dates_str} 號*\n🔗 [點我立即前往預訂]({TARGET_URL})"
            print(f"✅ 發現空位：10 月 {dates_str} 號")
            send_telegram(msg)
        else:
            print("ℹ️ 檢查完成：10 月 11、12、13 號目前均無開放空位 (均包含 × 或未開放)。")

        browser.close()

if __name__ == "__main__":
    check_reservation()
