# AGY-Youtube：教學影片自動上傳與 YouTube 播放清單自動歸納助手

> 專為中小學與高中職教師設計之日常課堂教學影片自動化整理發布工具。支援依學期、年級自動分批上傳至 YouTube、保留連字號與章節標記、精準歸納入對應的 YouTube 播放清單，並自動產出可直接複製貼入 Google Classroom 的教學清單與貼文草稿。

---

## 🎯 專案核心目標與特色

1. **免 API 憑證、免 Google Cloud 複雜設定**  
   採用本機瀏覽器自動化技術（Playwright），直接沿用日常 Chrome / Edge 瀏覽器登入狀態，徹底避開 Google Cloud 專案建立、API 配額限制（每日僅 6 部）與兩步驟驗證（2SV）阻擋。
2. **完整保留標題特殊符號**  
   解決 YouTube Studio 網頁版上傳時自動將檔名減號 `-`、底線 `_` 吃掉並轉為空白的問題。程式由後台精確指派標題（例如：`【8年級】1-1_01_資訊科技的社會議題`），符號完整保留。
3. **播放清單精確自動歸納**  
   自動解析目錄結構與年級標記（`7年級` / `8年級` / `9年級`），上傳時自動在 YouTube 工作室勾選對應的年級播放清單（例如：`115學年度第一學期8年級`），告別未分類影片。
4. **支援同名字幕檔（.srt / .vtt）自動上傳**  
   採用「方式 A 同名原則」，只要在影片旁邊放置同名的字幕檔案（例如 `1-1_01_資訊科技的社會議題.srt`），程式上傳時會自動在「影片元素」中載入並儲存為 YouTube 專屬中文字幕軌，完全無需手動加前綴！
5. **全自動彈窗關閉與異常防呆**  
   上傳發布後自動關閉「影片處理中」轉檔通知彈窗（支援 `:visible` 視覺定位與鍵盤 `Esc` 雙重保險），支援 YouTube「每日上傳數量上限」自動感應與安全暫停。
5. **Classroom 專屬超連結報表一鍵產出**  
   每次上傳完成自動在 `output/` 目錄生成包含 YouTube 連結的 Markdown、Excel（最新影片自動排在最上方第一列）以及專屬的 `本次最新上傳_Classroom貼文.txt`，教師可直接全選複製貼至 Google Classroom。
6. **智慧記憶、防止重複上傳**  
   內建上傳歷史資料庫（`upload_history.json`），已上傳過的影片留存於本機目錄也不會重複上傳，支援續傳與增量備課。

---

## 📁 目錄結構說明

```text
d:\AGY-Youtube\
├── videos\                              <-- 待上傳影片放置區（依學期與年級分層）
│   └── 115-1\
│       ├── 7年級\                       <-- 放置 7 年級影片
│       ├── 8年級\                       <-- 放置 8 年級影片
│       └── 9年級\                       <-- 放置 9 年級影片
├── output\                              <-- Classroom 報表輸出目錄
│   ├── 本次最新上傳_Classroom貼文.txt    <-- 當次最新上傳文字草稿（直接貼 Classroom）
│   ├── classroom_links.md               <-- 歷次完整超連結總表（Markdown）
│   └── classroom_links.xlsx             <-- 歷次完整超連結總表（Excel，最新在前）
├── 一鍵上傳到YouTube.bat                 <-- 主執行檔：雙擊自動掃描並上傳新影片
├── 一鍵修正已上傳影片播放清單.bat         <-- 輔助工具：批次將已上傳影片歸納入播放清單
├── upload_with_browser.py               <-- 核心腳本：Playwright 瀏覽器自動化上傳
├── manage_playlists.py                  <-- 輔助腳本：播放清單自動修復與歸納
├── upload_to_youtube.py                 <-- 備用腳本：YouTube Data API v3 官方介面
├── 使用說明.md                           <-- 詳細操作說明手冊
├── requirements.txt                     <-- Python 依賴套件清單
└── .gitignore                           <-- Git 排除規則（自動忽略所有大容量影片與隱私檔案）
```

---

## 🚀 快速開始指南

### 1. 安裝環境需求
* 作業系統：Windows 10 / 11
* Python 3.10 以上
* Google Chrome 或 Microsoft Edge 瀏覽器

在專案目錄下開啟命令提示字元（CMD）或 PowerShell 安裝依賴：
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 放置教學影片
將您錄製好的教學影片放入對應的資料夾，例如：
* `videos\115-1\8年級\1-1_01_資訊科技的社會議題.mp4`
* `videos\115-1\9年級\1-1_01_資料數位化.mp4`

### 3. 一鍵執行上傳
直接雙擊執行 **`一鍵上傳到YouTube.bat`**：
* **首次執行**：瀏覽器會開啟 YouTube Studio，請登入您的 YouTube 帳號一次（登入狀態會永久保存在本機 `browser_profile`，日後無需重複登入）。
* **後續執行**：雙擊後系統自動全自動辨識、上傳、加入播放清單、設定不公開與非兒童專屬，並產出 Classroom 連結！

### 4. 複製連結到 Classroom
上傳完成後，打開 `output\本次最新上傳_Classroom貼文.txt`，按 `Ctrl+A` 全選、`Ctrl+C` 複製，直接貼進 Google Classroom 即可發布給學生學習！

---

## 🛠️ 進階管理工具

* **`一鍵修正已上傳影片播放清單.bat`**：若頻道中有既有已發布的教學影片尚未加入播放清單，執行此工具可自動逐一進入影片編輯頁面，將影片打勾歸納至指定年級播放清單中。

---

## 🔒 隱私與安全性注意事項

* 本專案已在 `.gitignore` 嚴格排除所有 `*.mp4` 影片檔案、`browser_profile/`（瀏覽器個人登入狀態與 Cookie）以及個人日誌，確保推送到 GitHub 或他人電腦時**絕不洩漏個人 Google 帳號隱私**。
