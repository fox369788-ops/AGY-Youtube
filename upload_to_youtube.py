import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Google API 相關套件
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print("【錯誤】缺少必要的 Google 函式庫，請先執行：")
    print("pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 openpyxl")
    sys.exit(1)

# API 授權範圍 (上傳影片 + 管理播放清單)
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]

BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "token.json"
HISTORY_FILE = BASE_DIR / "upload_history.json"
OUTPUT_DIR = BASE_DIR / "output"
VIDEOS_DIR = BASE_DIR / "videos"

# 支援的影片格式
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}

def load_history():
    """讀取已上傳歷史紀錄，避免重複上傳"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    """儲存上傳歷史紀錄"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_authenticated_service():
    """取得 YouTube 驗證服務"""
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("正在自動刷新憑證...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"刷新失敗 ({e})，重新啟動授權...")
                creds = None

        if not creds:
            if not CLIENT_SECRET_FILE.exists():
                print(f"\n【找不到憑證檔案】\n請確認您已將下載的 OAuth 用戶端憑證重新命名為：")
                print(f"  --> {CLIENT_SECRET_FILE.name}")
                print(f"並存放在以下路徑：\n  --> {CLIENT_SECRET_FILE.parent}\n")
                sys.exit(1)

            print("\n正在啟動本機瀏覽器進行 Google 帳號授權...")
            print("提示：若瀏覽器跳出「Google 尚未驗證這個應用程式」，請點擊【進階】➔【前往(不安全)】繼續。")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
        print("✓ Google 憑證授權成功並已保存！\n")

    return build("youtube", "v3", credentials=creds)

def get_or_create_playlist(youtube, playlist_title):
    """搜尋或建立播放清單"""
    print(f"  [清單檢查] 搜尋播放清單：「{playlist_title}」...")
    try:
        request = youtube.playlists().list(
            part="snippet,status",
            mine=True,
            maxResults=50
        )
        while request:
            response = request.execute()
            for item in response.get("items", []):
                if item["snippet"]["title"].strip() == playlist_title.strip():
                    pl_id = item["id"]
                    print(f"  ✓ 找到既有播放清單！ID: {pl_id}")
                    return pl_id
            request = youtube.playlists().list_next(request, response)

        # 沒找到則建立新清單
        print(f"  [建立清單] 建立新播放清單：「{playlist_title}」...")
        insert_response = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": playlist_title,
                    "description": f"教學課程影片清單 - {playlist_title}"
                },
                "status": {
                    "privacyStatus": "unlisted"
                }
            }
        ).execute()
        pl_id = insert_response["id"]
        print(f"  ✓ 成功建立新播放清單！ID: {pl_id}")
        return pl_id
    except HttpError as e:
        print(f"  ❌ 操作播放清單失敗: {e}")
        return None

def upload_video_file(youtube, file_path, title, description="教學講解影片"):
    """上傳單一影片並設定為不公開與非兒童專屬"""
    print(f"\n>> 正在上傳影片: {title}")
    print(f"   本地路徑: {file_path}")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["教學", "課程"],
            "categoryId": "27"  # 27 = 教育 Education
        },
        "status": {
            "privacyStatus": "unlisted",  # 不公開
            "selfDeclaredMadeForKids": False  # 非兒童打造
        }
    }

    media = MediaFileUpload(
        str(file_path),
        chunksize=1024 * 1024 * 4,  # 4MB chunks
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"   上傳進度: {progress}%", end="\r")

    video_id = response.get("id")
    print(f"\n   ✓ 上傳完成！影片 ID: {video_id}")
    print(f"   ✓ 影片連結: https://youtu.be/{video_id}")
    return video_id

def add_to_playlist(youtube, video_id, playlist_id):
    """將影片加入指定播放清單"""
    if not playlist_id:
        return False
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        ).execute()
        print(f"   ✓ 成功加入播放清單 (ID: {playlist_id})")
        return True
    except HttpError as e:
        print(f"   ⚠️ 加入播放清單時發生錯誤: {e}")
        return False

def generate_classroom_reports(history):
    """生成 Markdown 與 Excel 格式的 Google Classroom 專用連結表"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_file = OUTPUT_DIR / "classroom_links.md"
    excel_file = OUTPUT_DIR / "classroom_links.xlsx"

    # 1. 產生 Markdown
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# Google Classroom 教學影片超連結清單\n\n")
        f.write(f"> 最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 依播放清單分類分組
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

        # 貼心附上 Classroom 貼文草稿格式
        f.write("### 📋 建議 Google Classroom 貼文複製範本\n")
        for pl_name, group in grouped.items():
            f.write("```text\n")
            f.write(f"【{pl_name} 線上學習專區】\n")
            f.write("同學們好，本單元線上講解影片如下，請依序點擊觀看學習：\n\n")
            for idx, v in enumerate(group["videos"], 1):
                f.write(f"{idx}. {v['title']}：{v['url']}\n")
            if group["playlist_url"]:
                f.write(f"\n完整播放清單：{group['playlist_url']}\n")
            f.write("```\n\n")

    # 2. 產生 Excel
    try:
        import pandas as pd
        rows = []
        for rel_path, data in history.items():
            rows.append({
                "學年度/學期": data.get("semester", ""),
                "年級": data.get("grade", ""),
                "播放清單": data.get("playlist_title", ""),
                "影片標題": data.get("title", ""),
                "YouTube 連結": data.get("url", ""),
                "播放清單連結": data.get("playlist_url", ""),
                "隱私狀態": data.get("privacy", "不公開"),
                "上傳時間": data.get("uploaded_at", "")
            })
        if rows:
            df = pd.DataFrame(rows)
            df.to_excel(excel_file, index=False)
    except Exception as e:
        print(f"產生 Excel 報表時略過: {e}")

    print(f"\n✓ 已成功更新 Classroom 連結清單：")
    print(f"  --> Markdown: {md_file}")
    print(f"  --> Excel:    {excel_file}")

def main():
    print("=" * 60)
    print("      YouTube 教學影片自動上傳與 Classroom 清單生成工具")
    print("=" * 60)

    # 掃描 videos 資料夾
    if not VIDEOS_DIR.exists():
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"已為您建立影片目錄：{VIDEOS_DIR}")
        print("請將影片放入對應的年級資料夾後再次執行。")
        return

    # 搜尋所有支援的影片檔案
    # 預期路徑：videos/<學期>/<年級>/<檔案.mp4>
    # 例如：videos/115-1/8年級/1-2-01-操作進度.mp4
    video_files = []
    for root, _, files in os.walk(VIDEOS_DIR):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                video_files.append(Path(root) / f)

    if not video_files:
        print(f"在 {VIDEOS_DIR} 中沒有找到任何影片檔案 (.mp4, .mov 等)。")
        print("請依格式放置影片，例如：")
        print("  videos/115-1/7年級/1-1-01-操作進度.mp4")
        print("  videos/115-1/8年級/1-2-01-操作進度.mp4")
        return

    history = load_history()
    pending_files = []

    for vf in video_files:
        rel_str = str(vf.relative_to(VIDEOS_DIR))
        if rel_str in history:
            # 已上傳過
            continue
        pending_files.append(vf)

    print(f"掃描結果：共找到 {len(video_files)} 部影片，其中待上傳：{len(pending_files)} 部。")

    if not pending_files:
        print("所有影片均已在歷史紀錄中上傳完成！")
        generate_classroom_reports(history)
        return

    # 執行 YouTube API 連線
    youtube = get_authenticated_service()

    # 快取清單 ID 避免重複查詢
    playlist_cache = {}

    for vf in pending_files:
        rel_path = vf.relative_to(VIDEOS_DIR)
        parts = rel_path.parts  # 例如 ('115-1', '8年級', '1-2-01-操作進度.mp4')
        
        semester = parts[0] if len(parts) > 1 else "115學年度第一學期"
        grade = parts[1] if len(parts) > 2 else "通用年級"
        base_name = vf.stem  # 例如 '1-2-01-操作進度'

        # 將 115-1 轉換為中文描述，若已有中文則直接用
        if semester == "115-1":
            semester_text = "115學年度第一學期"
        elif semester == "115-2":
            semester_text = "115學年度第二學期"
        else:
            semester_text = semester

        playlist_title = f"{semester_text}-{grade}"

        # 標題自動加上年級前綴，保留所有符號 '-'
        video_title = f"【{grade}】{base_name}"

        # 取得或建立播放清單
        if playlist_title not in playlist_cache:
            pl_id = get_or_create_playlist(youtube, playlist_title)
            playlist_cache[playlist_title] = pl_id
        else:
            pl_id = playlist_cache[playlist_title]

        pl_url = f"https://www.youtube.com/playlist?list={pl_id}" if pl_id else ""

        # 上傳影片
        video_id = upload_video_file(
            youtube=youtube,
            file_path=vf,
            title=video_title,
            description=f"{semester_text} {grade} 課堂教學影片：{video_title}"
        )

        if video_id:
            # 加入播放清單
            if pl_id:
                add_to_playlist(youtube, video_id, pl_id)

            video_url = f"https://youtu.be/{video_id}"

            # 記錄到歷史
            history[str(rel_path)] = {
                "title": video_title,
                "video_id": video_id,
                "url": video_url,
                "semester": semester_text,
                "grade": grade,
                "playlist_title": playlist_title,
                "playlist_id": pl_id,
                "playlist_url": pl_url,
                "privacy": "不公開",
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_history(history)
            print(f"   [進度已儲存] 成功處理 1 部影片！")

    # 最後更新報表
    generate_classroom_reports(history)
    print("\n" + "=" * 60)
    print("🎉 恭喜！本次所有待上傳教學影片已全數處理完畢！")
    print("=" * 60)

if __name__ == "__main__":
    main()
