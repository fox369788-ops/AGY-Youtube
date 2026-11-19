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
OUTPUT_DIR = BASE_DIR / "output"
VIDEOS_DIR = BASE_DIR / "videos"
PROFILE_DIR = BASE_DIR / "browser_profile"
LOG_FILE = BASE_DIR / "upload_log.txt"

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as lf:
            lf.write(formatted + "\n")
    except Exception:
        pass

def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def generate_classroom_reports(history, current_run_videos=None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_file = OUTPUT_DIR / "classroom_links.md"
    excel_file = OUTPUT_DIR / "classroom_links.xlsx"
    latest_txt_file = OUTPUT_DIR / "本次最新上傳_Classroom貼文.txt"

    # 1. 產生【本次最新上傳】專用貼文檔（方便直接全選複製貼進 Classroom）
    if current_run_videos:
        with open(latest_txt_file, "w", encoding="utf-8") as f:
            f.write("========================================================\n")
            f.write("  本次最新上傳完成清單（可直接全選複製貼至 Classroom）\n")
            f.write(f"  上傳時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("========================================================\n\n")

            # 依播放清單分組
            cur_grouped = {}
            for item in current_run_videos:
                pl = item.get("playlist_title", "教學影片")
                if pl not in cur_grouped:
                    cur_grouped[pl] = []
                cur_grouped[pl].append(item)

            for pl_name, v_list in cur_grouped.items():
                f.write(f"【{pl_name} 線上學習專區】\n")
                f.write("各位同學好，本單元最新線上教學影片如下，請依序點擊觀看學習：\n\n")
                for idx, v in enumerate(v_list, 1):
                    f.write(f"{idx}. {v['title']}：{v['url']}\n")
                f.write("\n--------------------------------------------------------\n\n")

    # 2. 產生歷次總表 Markdown
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# Google Classroom 教學影片超連結總表\n\n")
        f.write(f"> 最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        grouped = {}
        for rel_path, data in history.items():
            pl_name = data.get("playlist_title", "未分類")
            if pl_name not in grouped:
                grouped[pl_name] = {
                    "playlist_url": data.get("playlist_url", ""),
                    "videos": []
                }
            grouped[pl_name]["videos"].append(data)

        for pl_name, group in grouped.items():
            f.write(f"## 📁 {pl_name}\n")
            if group["playlist_url"]:
                f.write(f"* 🔗 **播放清單完整連結**：[{pl_name}]({group['playlist_url']})\n\n")

            f.write("| 序號 | 影片標題 | YouTube 播放連結 | 設定狀態 | 上傳時間 |\n")
            f.write("| :---: | :--- | :--- | :---: | :---: |\n")
            for idx, v in enumerate(group["videos"], 1):
                f.write(f"| {idx} | **{v['title']}** | [{v['url']}]({v['url']}) | {v.get('privacy', '不公開')} | {v.get('uploaded_at', '')} |\n")
            f.write("\n---\n\n")

    # 3. 產生 Excel 總表（最新上傳排在最上面第一列！）
    try:
        import pandas as pd
        rows = []
        for rel_path, data in history.items():
            rows.append({
                "上傳時間": data.get("uploaded_at", ""),
                "年級": data.get("grade", ""),
                "影片標題": data.get("title", ""),
                "YouTube 播放連結": data.get("url", ""),
                "所屬播放清單": data.get("playlist_title", ""),
                "學年度/學期": data.get("semester", ""),
                "隱私狀態": data.get("privacy", "不公開")
            })
        if rows:
            df = pd.DataFrame(rows)
            # 依上傳時間降冪排列，最新上傳的永遠在第一列！
            df = df.sort_values(by="上傳時間", ascending=False)
            df.to_excel(excel_file, index=False)
    except Exception as e:
        log(f"產生 Excel 略過: {e}")

    log(f"✓ Classroom 連結清單已成功輸出：")
    if current_run_videos:
        log(f"  --> 本次貼文檔: {latest_txt_file}")
    log(f"  --> Markdown:   {md_file}")
    log(f"  --> Excel (最新排最上): {excel_file}")

def run():
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as lf:
            lf.write(f"=== 上傳任務開始：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    except Exception:
        pass

    log("=" * 60)
    log("   YouTube 教學影片自動上傳助手 (免 API / 免 Google Cloud)")
    log("=" * 60)

    # 1. 掃描待上傳影片
    video_files = []
    for root, _, files in os.walk(VIDEOS_DIR):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                video_files.append(Path(root) / f)

    if not video_files:
        log("【找不到待上傳影片】請將影片放入 videos 目錄對應年級資料夾。")
        return

    history = load_history()
    # 只要在 history 裡，自動跳過，絕不重複上傳！
    pending = [vf for vf in video_files if str(vf.relative_to(VIDEOS_DIR)) not in history]

    log(f"掃描結果：資料夾內共有 {len(video_files)} 部影片。")
    log(f"  --> 已上傳過（自動跳過）：{len(video_files) - len(pending)} 部")
    log(f"  --> 本次待上傳：{len(pending)} 部")

    if not pending:
        log("\n✓ 所有影片皆已在先前上傳完成，無需重複上傳！")
        generate_classroom_reports(history)
        return

    for idx, f in enumerate(pending, 1):
        log(f"  [{idx}] {f.name} ({f.parent.name})")

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    log("\n正在啟動 Chrome 瀏覽器...")

    from playwright.sync_api import sync_playwright

    current_run_uploaded = []

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
            log(f"Chrome 啟動失敗 ({e})，改用 Edge 啟動...")
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

        log("正在連線至 YouTube 工作室 (studio.youtube.com)...")
        page.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        time.sleep(3)

        # 自動偵測是否已在工作室
        logged_in = False
        for check_round in range(15):
            url = page.url
            if "channel/" in url or page.locator("#create-icon, #upload-button, ytcp-button:has-text('建立'), ytcp-button:has-text('上傳影片')").count() > 0:
                logged_in = True
                break
            time.sleep(1)

        if not logged_in:
            log("\n============================================================")
            log("【提示：請在瀏覽器中登入您的 YouTube 帳號】")
            log("登入完成並看到 YouTube 工作室畫面後，回到此視窗按 [Enter] 繼續。")
            log("============================================================\n")
            input(">> 登入完成後，請在此按 [Enter] 鍵繼續：")
            time.sleep(2)

        log("✓ 登入狀態確認成功！開始自動上傳...")

        for vf in pending:
            rel_path = vf.relative_to(VIDEOS_DIR)
            parts = rel_path.parts
            semester = parts[0] if len(parts) > 1 else "115-1"
            grade = parts[1] if len(parts) > 2 else "通用年級"
            base_name = vf.stem

            if semester == "115-1":
                sem_str = "115學年度第一學期"
            elif semester == "115-2":
                sem_str = "115學年度第二學期"
            else:
                sem_str = semester

            playlist_title = f"{sem_str}-{grade}"
            video_title = f"【{grade}】{base_name}"

            log("=" * 50)
            log(f"正在處理: {video_title}")
            log(f"目標播放清單: {playlist_title}")
            log(f"本機檔案: {vf}")
            log("=" * 50)

            # 確保畫面上沒有前一個影片遺留的「影片處理中」對話框阻擋
            try:
                blocking_dialog = page.locator("ytcp-uploads-still-processing-dialog:visible, ytcp-uploads-dialog:visible, tp-yt-paper-dialog:visible").first
                if blocking_dialog.is_visible():
                    log("偵測到前次彈窗殘留，自動清理關閉中...")
                    visible_close = page.locator("ytcp-button:has-text('關閉'):visible, #close-button:visible, button:has-text('關閉'):visible").first
                    if visible_close.is_visible():
                        visible_close.click()
                    else:
                        page.keyboard.press("Escape")
                    time.sleep(1.5)
            except Exception:
                pass

            if "studio.youtube.com" not in page.url:
                page.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
                time.sleep(3)

            # 開啟上傳視窗
            log("正在點擊上傳按鈕...")
            for attempt in range(8):
                if page.locator("input[type='file']").count() > 0:
                    break

                try:
                    center_btn = page.locator("#upload-button, ytcp-button:has-text('上傳影片')").first
                    if center_btn.is_visible():
                        center_btn.click()
                        time.sleep(2)
                        if page.locator("input[type='file']").count() > 0:
                            break
                except Exception:
                    pass

                try:
                    create_btn = page.locator("#create-icon, #create-button, ytcp-button:has-text('建立')").first
                    if create_btn.is_visible():
                        create_btn.click()
                        time.sleep(1)
                        upload_opt = page.locator("tp-yt-paper-item:has-text('上傳影片'), ytcp-text-menu #text-item-0").first
                        if upload_opt.is_visible():
                            upload_opt.click()
                            time.sleep(2)
                            if page.locator("input[type='file']").count() > 0:
                                break
                except Exception:
                    pass

                time.sleep(1)

            # 載入影片檔案
            log("正在傳送檔案至 YouTube 工作室...")
            file_input = page.locator("input[type='file']").first
            file_input.wait_for(state="attached", timeout=30000)
            file_input.set_input_files(str(vf))
            log("✓ 檔案已載入，等待 YouTube 工作室解析影片...")

            # 等待對話框掛載
            page.locator("ytcp-uploads-dialog").wait_for(state="attached", timeout=60000)
            time.sleep(3)

            # 檢查是否達到 YouTube 每日上傳數量上限
            if page.locator("text='已達每日上傳數量上限', text='已達每日上傳上限'").is_visible():
                log("\n" + "!" * 60)
                log("⚠️ 偵測到 YouTube 已達每日上傳數量上限！")
                log("本片及後續影片暫停上傳，請於 24 小時後再次執行，或於網頁中點擊「驗證」解鎖。")
                log("!" * 60 + "\n")
                break

            # 從對話框屬性擷取 YouTube 官方指派的 video-id
            dialog = page.locator("ytcp-uploads-dialog").first
            video_id = ""
            for _ in range(30):
                video_id = dialog.get_attribute("video-id")
                if video_id:
                    break
                time.sleep(1)

            if video_id:
                video_url = f"https://youtu.be/{video_id}"
                log(f"✓ 成功取得 YouTube 官方影片 ID: {video_id}")
                log(f"✓ 影片專屬播放連結: {video_url}")
            else:
                video_url = ""

            # 1. 填寫標題 (保留所有 '-')
            try:
                title_box = page.locator("#textbox[aria-label*='標題'], div#textbox[contenteditable='true'], #title-textarea #textbox").first
                title_box.wait_for(state="visible", timeout=30000)
                title_box.click()
                time.sleep(0.5)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                time.sleep(0.5)
                page.keyboard.type(video_title)
                log(f"✓ 已設定影片標題: {video_title}")
            except Exception as e:
                log(f"⚠️ 設定標題時出錯: {e}")

            time.sleep(1)

            # 2. 設定非兒童專屬
            try:
                not_kids = page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK'], tp-yt-paper-radio-button:has-text('不是專為兒童打造'), tp-yt-paper-radio-button:has-text('No, it\\'s not made for kids')").first
                not_kids.scroll_into_view_if_needed()
                not_kids.click()
                log("✓ 已設定「非兒童打造」")
            except Exception as e:
                log(f"⚠️ 設定受眾出錯: {e}")

            time.sleep(1)

            # 3. 播放清單
            try:
                pl_trigger = page.locator("ytcp-video-metadata-playlists ytcp-text-dropdown-trigger, ytcp-text-dropdown-trigger:has-text('選取'), ytcp-video-metadata-playlists").first
                if pl_trigger.is_visible():
                    pl_trigger.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    pl_trigger.click()
                    time.sleep(2)

                    # 依照年級關鍵字（如 8年級、9年級、7年級）在彈窗中精確尋找並勾選
                    target_chk = page.locator(f"tp-yt-paper-checkbox:has-text('{grade}'), ytcp-checkbox-lit:has-text('{grade}'), [role='checkbox']:has-text('{grade}')").first

                    if target_chk.is_visible():
                        is_checked = target_chk.get_attribute("aria-checked") == "true" or target_chk.get_attribute("checked") is not None
                        if not is_checked:
                            target_chk.click()
                            log(f"✓ 成功勾選【{grade}】播放清單！")
                        else:
                            log(f"ℹ️ 【{grade}】播放清單已處於勾選狀態")
                        time.sleep(0.5)
                    else:
                        text_el = page.get_by_text(f"{grade}").last
                        if text_el.is_visible():
                            text_el.click()
                            log(f"✓ 成功透過文字點擊【{grade}】播放清單！")
                            time.sleep(0.5)

                    # 點擊「完成」按鈕關閉選單
                    done_btn = page.locator("ytcp-button.done-button, ytcp-button:has-text('完成'), button:has-text('完成')").first
                    if done_btn.is_visible():
                        done_btn.click()
                        time.sleep(1)
            except Exception as e:
                log(f"⚠️ 處理播放清單略過: {e}")

            # 4. 再次確認連結
            if not video_url:
                try:
                    link_el = page.locator("a[href*='youtu.be'], a.ytcp-video-info").first
                    if link_el.is_visible():
                        video_url = link_el.get_attribute("href") or link_el.inner_text().strip()
                        log(f"✓ 取得影片連結: {video_url}")
                except Exception:
                    pass

            # 5. 前往「影片元素」步驟
            next_btn = page.locator("#next-button, ytcp-button:has-text('下一步')").first
            if next_btn.is_visible():
                next_btn.click()
                time.sleep(2)

            # 檢查是否有同名字幕檔案 (.srt 或 .vtt，採用方式 A 同檔名原則)
            srt_candidate = vf.with_suffix(".srt")
            if not srt_candidate.exists():
                srt_candidate = vf.with_suffix(".vtt")

            if srt_candidate.exists():
                log(f"✓ 偵測到同名專屬字幕檔: {srt_candidate.name}，正在自動掛載字幕...")
                try:
                    add_sub_btn = page.locator("ytcp-video-elements-cell-subtitles ytcp-button#add-button, #subtitles-button, ytcp-button:has-text('新增字幕'), ytcp-button:has-text('新增')").first
                    if add_sub_btn.is_visible():
                        add_sub_btn.click()
                        time.sleep(2)

                        upload_file_btn = page.locator("tp-yt-paper-item:has-text('上傳檔案'), ytcp-button:has-text('上傳檔案'), button:has-text('上傳檔案')").first
                        if upload_file_btn.is_visible():
                            upload_file_btn.click()
                            time.sleep(1)

                            continue_btn = page.locator("ytcp-button:has-text('繼續'), button:has-text('繼續')").first
                            if continue_btn.is_visible():
                                continue_btn.click()
                                time.sleep(1)

                        sub_file_input = page.locator("input[type='file']").last
                        sub_file_input.set_input_files(str(srt_candidate))
                        log("✓ 字幕檔已傳送，等待 YouTube 解析時間軸...")
                        time.sleep(3)

                        done_sub_btn = page.locator("ytcp-button:has-text('完成'), button:has-text('完成'), ytcp-button#save-button").first
                        if done_sub_btn.is_visible():
                            done_sub_btn.click()
                            log("✓ 專屬中文字幕已成功儲存！")
                            time.sleep(2)
                except Exception as e:
                    log(f"⚠️ 自動掛載字幕略過 ({e})，繼續完成影片發布")

            # 繼續點擊「下一步」直到最後的「瀏覽權限」步驟
            for step in range(3):
                try:
                    next_btn = page.locator("#next-button, ytcp-button:has-text('下一步')").first
                    if next_btn.is_visible():
                        next_btn.click()
                        time.sleep(1.5)
                except Exception:
                    break

            # 6. 設定不公開
            try:
                unlisted = page.locator("tp-yt-paper-radio-button[name='UNLISTED'], tp-yt-paper-radio-button:has-text('不公開')").first
                unlisted.scroll_into_view_if_needed()
                unlisted.click()
                log("✓ 已設定影片權限為「不公開」")
            except Exception as e:
                log(f"⚠️ 設定不公開出錯: {e}")

            time.sleep(1)

            # 7. 點擊發布/儲存
            try:
                save_btn = page.locator("#done-button, ytcp-button:has-text('儲存'), ytcp-button:has-text('發布')").first
                save_btn.click()
                log("✓ 已點擊發布，正在儲存中...")
                time.sleep(4)
            except Exception as e:
                log(f"⚠️ 點擊發布出錯: {e}")

            # 關閉「影片處理中」對話框
            log("正在自動關閉「影片處理中」彈窗...")
            dialog_closed = False
            for close_attempt in range(12):
                # 1. 抓取目前畫面上真正「可見」的關閉按鈕
                try:
                    visible_close = page.locator("ytcp-button:has-text('關閉'):visible, #close-button:visible, button:has-text('關閉'):visible, [aria-label*='關閉']:visible").first
                    if visible_close.is_visible():
                        visible_close.click()
                        log("✓ 已自動點擊「關閉」按鈕")
                        dialog_closed = True
                        time.sleep(1.5)
                        break
                except Exception:
                    pass

                # 2. 如果沒抓到，使用鍵盤 Escape 鍵（YouTube 對話框原生支援按 Esc 關閉）
                try:
                    page.keyboard.press("Escape")
                    time.sleep(1)
                    if page.locator("ytcp-uploads-still-processing-dialog:visible, ytcp-uploads-dialog:visible").count() == 0:
                        log("✓ 已透過鍵盤 Escape 成功關閉對話框")
                        dialog_closed = True
                        break
                except Exception:
                    pass

                time.sleep(1)

            if not dialog_closed:
                log("⚠️ 未能自動關閉彈窗，但將在下一部影片啟動時再次嘗試清理")

            item_data = {
                "title": video_title,
                "video_id": video_id,
                "url": video_url if video_url else f"https://youtu.be/{video_id}",
                "semester": sem_str,
                "grade": grade,
                "playlist_title": playlist_title,
                "playlist_url": "",
                "privacy": "不公開",
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            history[str(rel_path)] = item_data
            current_run_uploaded.append(item_data)
            save_history(history)
            log(f"🎉 【{video_title}】處理完成！連結：{video_url}")
            time.sleep(2)

        context.close()

    generate_classroom_reports(history, current_run_videos=current_run_uploaded)
    log("\n" + "=" * 60)
    log("🎉 所有影片已全數處理完畢！可前往 output/ 查看 Classroom 連結與貼文。")
    log("=" * 60)

def main():
    try:
        run()
    except Exception as e:
        log("\n【執行過程中發生未預期錯誤】")
        log(traceback.format_exc())
    finally:
        print("\n請按 [Enter] 鍵結束視窗...", flush=True)
        try:
            input()
        except Exception:
            pass

if __name__ == "__main__":
    main()
