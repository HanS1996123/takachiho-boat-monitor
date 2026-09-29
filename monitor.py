import os
import requests
from bs4 import BeautifulSoup

# 從 GitHub Secrets 讀取環境變數
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 高千穗峽遊船預訂網站 URL
TARGET_URL = "https://takachiho-kanko.info/boat/" 

def send_telegram(message):
    """發送 Telegram 通知的函式"""
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
        print("Telegram 通知發送狀態碼:", res.status_code)
    except Exception as e:
        print("發送 Telegram 失敗:", e)

def check_reservation():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 監控目標日期：11, 12, 13 號
        target_dates = ["11", "12", "13"]
        available_found = []

        # 提示：此處邏輯依網頁 HTML 結構解析。
        # 尋找網頁月曆表格中包含 11、12、13 號的欄位，檢查狀態是否不再是 '×'
        # 範例邏輯：搜尋所有表格單元格 (td / tr)
        for cell in soup.find_all(["td", "div", "li"]):
            cell_text = cell.get_text(strip=True)
            for d in target_dates:
                # 若儲存格包含日期數字且狀態包含可預約符號 (如 '○', '△', 或非 '×')
                if d in cell_text and "×" not in cell_text:
                    if d not in available_found:
                        available_found.append(d)

        if available_found:
            dates_str = "、".join(available_found)
            msg = f"🎉 *【高千穗峽遊船】發現空位！*\n\n📅 日期：*{dates_str} 號*\n🔗 [點我前往預訂網頁]({TARGET_URL})"
            send_telegram(msg)
            print(f"發現空位！日期：{dates_str}")
        else:
            print("檢查完成：11、12、13 號目前仍為 × (無空位)。")

    except Exception as e:
        print("抓取網頁時發生錯誤:", e)

if __name__ == "__main__":
    check_reservation()
