# API 一覧（詳細仕様）

> [要件定義書.md](./要件定義書.md) の付属資料。FastAPI バックエンドの全エンドポイント詳細。
> ベース URL: `http://<host>:18000`（Docker）。自動 API ドキュメント: `/docs`。
> CORS は全オリジン許可。認証なし。

---

## システム

### `GET /`
ルート疎通確認。
- レスポンス: `{ "message": "漫画下载管理器API" }`

### `GET /health`
ヘルスチェック。
- レスポンス: `{ "status": "ok" }`

---

## 漫画管理（tag: manga）

### `GET /api/mangas`
全漫画を取得。
- レスポンス: `MangaResponse[]`
  - `id, title, author, manga_url, page_count, updated_at, file_size, is_downloaded, downloaded_at, cover_image_url, cover_image_path, preview_image_url, is_favorited`
  - `preview_image_url` は `cover_image_url` のエイリアス。

### `DELETE /api/manga/{manga_id}`
漫画を削除（CBZ・カバー画像も物理削除）。
- 200: `{ "success": true, "message": "删除成功" }`
- 404: 漫画が存在しない。

### `POST /api/add-to-favorite`
サイト側お気に入り（作者フォルダ）に登録。
- リクエスト: `{ "manga_id": "<Manga.id>" }`
- 200: `{ "success": true, "message": "已成功收藏到网站" }`
- 404: 漫画なし / 500: 収藏失敗
- ⚠️ 実装注意: ハンドラの型注釈欠落により正しく動作しない可能性あり（[要件定義書 §11-1](./要件定義書.md)）。

---

## 同期・ファイル（tag: sync）

### `POST /api/sync`
収藏夹同期タスクを作成しバックグラウンド実行（シングルトン）。
- 200: `{ "success": true, "task_id": "...", "message": "..." }`（`TaskCreateResponse`）
- 409: 既に同期実行中。

### `POST /api/verify-files`
DL 済み漫画の CBZ 実在を検証し、欠損は状態リセット。
- 200: `VerifyResponse`
  - `success, message, verified_count, fixed_count, missing_files[]`

### `POST /api/update-download-status`
ローカル `downloads/` を走査して DB の DL 状態を更新。
- 200: `UpdateDownloadStatusResponse`
  - `success, message, scanned_files, matched_count, marked_downloaded, marked_not_downloaded, unmatched_files`

---

## ダウンロード（tag: download）

> ルート定義順に注意: 具体パス（`/download/queue`, `/download/batch`）はパラメータパス（`/download/{manga_id}`）より先に定義。

### `GET /api/download/queue`
キュー中（+実行中）の漫画 ID 一覧。
- 200: `string[]`

### `POST /api/download/batch`
複数漫画を一括でキュー投入。
- リクエスト: `{ "manga_ids": ["id1", "id2", ...] }`
- 200: `BatchDownloadResponse`
  - `success, message, total, success_count, failed_count`

### `POST /api/download/{manga_id}`
単体漫画をキュー投入。
- 200: `TaskCreateResponse`
  - 新規投入: `task_id` 有・「下载任务已加入队列」
  - 実行中: 既存 `task_id`・「下载任务正在执行」
  - DL 済み: `task_id=""`・「漫画已下载」
- 404: 漫画なし。

---

## 最近更新（tag: recent-updates）

### `GET /api/recent-updates`
最近更新を更新日降順で取得。
- 200: `MangaResponse[]`（`recent_updates` テーブル由来）

### `POST /api/sync-recent-updates`
最近更新同期タスクを作成（シングルトン）。
- 200: `TaskCreateResponse`
- 409: 既に実行中。

### `POST /api/download-from-update/{update_id}`
最近更新レコードをダウンロード。
- 処理: `mangas` に未存在なら追加（`is_favorited=false`）→ キュー投入。
- 200: `TaskCreateResponse`
- 404: 最近更新レコードなし / 500: 追加失敗。

---

## タスク管理（tag: tasks）

### `GET /api/tasks/{task_id}`
タスク詳細（画面再読込時の状態復元用）。
- 200: `TaskResponse`
  - `id, task_type, status, progress, total_items, completed_items, message, error_message, manga_id, manga_ids, result_data, created_at, updated_at, completed_at`
- 404: タスクなし。

### `GET /api/tasks`
タスク一覧。
- クエリ: `task_type?`, `status?`, `limit=10`
- 200: `TaskResponse[]`（作成日時降順）

### `GET /api/tasks/running/list`
実行中（pending/running）タスク一覧。
- クエリ: `task_type?`
- 200: `TaskResponse[]`

### `GET /api/tasks/latest/{task_type}`
種別ごとの最新タスク。
- 200: `TaskResponse | null`

### `POST /api/tasks/cleanup`
中断タスクを手動清理（全 pending/running を failed 化）。
- 200: `{ "success": true, "message": "...", "cleaned_count": N }`

### `GET /api/events`
Server-Sent Events ストリーム。
- `Content-Type: text/event-stream`
- イベント: `connected`（初回）, `task_created`, `task_updated`
- 30 秒無通信で `: heartbeat` を送出。
- データ形式: `event: <type>\ndata: {"type","data":{...},"timestamp"}\n\n`
  - `task_updated.data`: `task_id, task_type, status, progress, completed_items, total_items, message, error_message`

---

## 設定（tag: settings）

### `GET /api/settings`
アプリ設定取得（未存在時は既定行を生成）。
- 200: `AppConfigResponse`（`manual_manga_site_url`）

### `PUT /api/settings`
アプリ設定更新。
- リクエスト: `{ "manual_manga_site_url": "https://..." | null }`
- 200: `AppConfigResponse`
- 400: URL が `http://`/`https://` で始まらない。

---

## タスク種別（task_type）一覧

| task_type | 生成元 | 実行制御 |
|-----------|--------|---------|
| `sync` | `POST /api/sync` | シングルトン |
| `sync_recent_updates` | `POST /api/sync-recent-updates` | シングルトン |
| `download` | `POST /api/download/*`, `/api/download-from-update/*` | キュー（逐次） |

## タスク状態（status）

`pending` → `running` → `completed` / `failed`

## HTTP ステータスコード方針

| コード | 用途 |
|--------|------|
| 200 | 正常 |
| 400 | バリデーションエラー（設定 URL 形式等） |
| 404 | リソース未存在 |
| 409 | 同期タスクの二重実行 |
| 500 | サーバ内部エラー |
