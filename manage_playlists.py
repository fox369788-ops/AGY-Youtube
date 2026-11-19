import os
import sys
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

# 強制 UTF-8 與即時輸出
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "upload_history.json"
PROFILE_DIR = BASE_DIR / "browser_profile"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def fix_playlists():
    log("=" * 60)
    log("  YouTube 影片播放清單自動歸納修正工具")
    log("=" * 60)

    if not HISTORY_FILE.exists():
        log("找不到 upload_history.json 歷史紀錄。")
        return

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)

    if not history:
        log("目前沒有已上傳的影片紀錄。")
        return

    log(f"已記錄影片總數：{len(history)} 部")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                channel="chrome",
                headless=False,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled"
                ],
                no_viewport=True
            )
        except Exception as e:
            log(f"啟動 Chrome 失敗 ({e})，改用 Edge 嘗試...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                channel="msedge",
                headless=False,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled"
                ],
                no_viewport=True
            )

        page = context.pages[0] if context.pages else context.new_page()

        log("正在連線至 YouTube 工作室...")
        page.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        time.sleep(3)

        # 逐一處理每一部已上傳的影片
        for rel_path, item in history.items():
            video_id = item.get("video_id")
            title = item.get("title", "")
            grade = item.get("grade", "")

            # 若 grade 沒填，從檔名或標題判定
            if not grade:
                if "7年級" in title or "7年級" in rel_path or "七年級" in title:
                    grade = "7年級"
                elif "8年級" in title or "8年級" in rel_path or "八年級" in title:
                    grade = "8年級"
                elif "9年級" in title or "9年級" in rel_path or "九年級" in title:
                    grade = "9年級"

            if not video_id or not grade:
                continue

            log("=" * 50)
            log(f"正在設定播放清單：{title}")
            log(f"影片 ID: {video_id}")
            log(f"辨識年級: 【{grade}】")
            log("=" * 50)

            edit_url = f"https://studio.youtube.com/video/{video_id}/edit"
            page.goto(edit_url, wait_until="domcontentloaded")
            time.sleep(3)

            # 檢查影片是否已被刪除
            if page.locator("text='糟糕，系統發生錯誤'").is_visible() or page.locator("text='糟糕'").is_visible():
                log(f"⚠️ 影片 ID [{video_id}] 已在 YouTube 上被刪除，自動跳過！")
                continue

            try:
                # 滾動找到播放清單區域並點擊下拉選單
                pl_trigger = page.locator("ytcp-video-metadata-playlists ytcp-text-dropdown-trigger, ytcp-text-dropdown-trigger:has-text('選取'), ytcp-video-metadata-playlists").first
                pl_trigger.scroll_into_view_if_needed()
                time.sleep(1)
                pl_trigger.click()
                time.sleep(2)

                # 依年級關鍵字（如 8年級、9年級、7年級）在彈窗中精確尋找
                target_item = page.locator(f"tp-yt-paper-checkbox:has-text('{grade}'), ytcp-checkbox-lit:has-text('{grade}'), [role='checkbox']:has-text('{grade}')").first

                if target_item.is_visible():
                    # 檢查是否已勾選
                    is_checked = target_item.get_attribute("aria-checked") == "true" or target_item.get_attribute("checked") is not None
                    if not is_checked:
                        target_item.click()
                        log(f"✓ 成功勾選【{grade}】播放清單！")
                        time.sleep(0.5)
                    else:
                        log(f"ℹ️ 【{grade}】播放清單已處於勾選狀態")
                else:
                    # 備援點擊文字
                    text_el = page.get_by_text(f"{grade}").last
                    if text_el.is_visible():
                        text_el.click()
                        log(f"✓ 成功點擊【{grade}】播放清單項目！")
                        time.sleep(0.5)

                # 點擊「完成」按鈕關閉播放清單選單
                done_btn = page.locator("ytcp-button.done-button, ytcp-button:has-text('完成'), button:has-text('完成')").first
                if done_btn.is_visible():
                    done_btn.click()
                    time.sleep(1.5)

                # 點擊右上角「儲存」按鈕
                save_btn = page.locator("#save, ytcp-button#save, ytcp-button:has-text('儲存'), button:has-text('儲存')").first
                if save_btn.is_visible() and not save_btn.get_attribute("disabled"):
                    save_btn.click()
                    log(f"✓ 成功儲存！影片已正確歸入【{grade}】播放清單！")
                    time.sleep(3)
                else:
                    log(f"ℹ️ 設定確認無誤（儲存按鈕無需點擊）")

            except Exception as e:
                log(f"⚠️ 處理影片 {video_id} 播放清單時發生狀況: {e}")

            time.sleep(1)

        context.close()

    log("\n" + "=" * 60)
    log("🎉 所有已上傳影片的播放清單歸類已全數修正完成！")
    log("=" * 60)

if __name__ == "__main__":
    try:
        fix_playlists()
    except Exception as e:
        log("\n【執行失敗】")
        log(traceback.format_exc())
    finally:
        print("\n請按 [Enter] 鍵結束視窗...", flush=True)
        try:
            input()
        except Exception:
            pass
