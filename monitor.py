import os
import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------
# 1. Render Health Check 背景服務（防止免費容器被強制休眠）
# ---------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        # 隱藏 HTTP 請求 Log，保持 Console 畫面乾淨
        return

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# 啟動 HTTP 伺服器背景執行緒
threading.Thread(target=run_health_check_server, daemon=True).start()


# ---------------------------------------------------------
# 2. Telegram 訊息推播函式
# ---------------------------------------------------------
def send_telegram_msg(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("⚠️ 未設定 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID，跳過訊息推播")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ Telegram 通知發送成功！")
        else:
            print(f"❌ Telegram 發送失敗: {res.text}")
    except Exception as e:
        print(f"❌ 發送 Telegram 訊息發生例外: {e}")


# ---------------------------------------------------------
# 3. 高千穗峽划船預約監控主邏輯 (Playwright)
# ---------------------------------------------------------
def run_monitor():
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{current_time}] 開始執行高千穗峽預約狀況檢查...")
    
    # 目標日期（10/11, 10/12, 10/13）與預約網站
    target_dates = ["10/11", "10/12", "10/13"]
    url = "https://takachiho-kanko.jp/boat/reservation/"  # 替換為實際高千穗峽預約網址
    available_dates = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 過濾跨月無效日期，取得當月日曆儲存格 (.fc-daygrid-day:not(.fc-other-month))
            day_cells = page.query_selector_all(".fc-daygrid-day:not(.fc-other-month)")

            for cell in day_cells:
                cell_text = cell.inner_text()
                
                # 檢查是否包含目標日期
                for target_date in target_dates:
                    if target_date in cell_text:
                        # 判斷有無空位（非滿員/非✕，或包含 ○/殘數標示）
                        if ("滿員" not in cell_text and "✕" not in cell_text) or ("○" in cell_text or "殘" in cell_text):
                            available_dates.append(target_date)

            # 抓到空位時發送 Telegram 警報
            if available_dates:
                unique_dates = ", ".join(sorted(list(set(available_dates))))
                alert_msg = f"🚨【高千穗峽划船釋出空位！】\n\n發現以下日期有空位：{unique_dates}\n請立刻前往搶票：\n{url}"
                print(alert_msg)
                send_telegram_msg(alert_msg)
            else:
                print("ℹ️ 目前 10/11 - 10/13 均無空位，持續監控中...")

        except Exception as e:
            print(f"❌ 爬蟲網頁抓取失敗: {e}")
        finally:
            browser.close()


# ---------------------------------------------------------
# 4. 主程式：24 Hours / 7 Days 無限迴圈 (每 5 分鐘跑一次)
# ---------------------------------------------------------
if __name__ == "__main__":
    print("🚀 高千穗峽划船預約監控服務已啟動（每 5 分鐘自動檢查一次）...")
    while True:
        try:
            run_monitor()
        except Exception as e:
            print(f"❌ 主程序運作異常: {e}")
        
        print("⏳ 等待 5 分鐘後進行下一輪檢查...\n")
        time.sleep(300)  # 300 秒 = 5 分鐘
