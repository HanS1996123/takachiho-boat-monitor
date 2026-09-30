# ---------------------------------------------------------
# 3. 高千穗峽划船預約監控主邏輯 (Playwright)
# ---------------------------------------------------------
def run_monitor():
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{current_time}] 開始執行高千穗峽預約狀況檢查...")
    
    url = "https://takachiho-kanko.jp/boat/reservation/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 1. 等待週曆容器載入完畢
            page.wait_for_selector(".fc-view-container", timeout=15000)
            
            # -----------------------------------------------------
            # 2. 點擊右箭頭切換到「下一週」（若目標在更後面的週，可重複執行 click）
            # -----------------------------------------------------
            next_btn = page.locator(".fc-next-button")
            if next_btn.is_visible():
                print("➡️ 點擊右箭頭切換至下一週...")
                next_btn.click()
                page.wait_for_timeout(2000)  # 等待 2 秒讓表格資料刷新
            # -----------------------------------------------------

            # 3. 擷取切換後週曆內的文字內容
            calendar_text = page.locator(".fc-view-container").inner_text()
            
            # 4. 判斷是否包含空位符號 (○ 代表有位，△ 代表剩餘少量)
            if "○" in calendar_text or "△" in calendar_text:
                alert_msg = f"🚨【高千穗峽划船釋出空位了！】\n\n發現週曆上有可預約時段 (○ / △)！\n請立刻前往搶票：\n{url}"
                print(alert_msg)
                send_telegram_msg(alert_msg)
            else:
                print("ℹ️ 目前週曆畫面上均無空位 (○ / △)，持續監控中...")

        except Exception as e:
            print(f"❌ 爬蟲網頁抓取失敗: {e}")
        finally:
            browser.close()
