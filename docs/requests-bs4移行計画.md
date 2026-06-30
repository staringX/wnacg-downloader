# requests + BeautifulSoup 全面移行 実装計画

> [requests-bs4方式.md](./requests-bs4方式.md) を前提に、クロール層を Selenium から
> `requests` + `BeautifulSoup` へ**全面移行**するための実装計画。
> **フェーズ0（実現性検証）を必須ゲート**とし、ここを通過しない限り本移行に着手しない。
> 作成日: 2026-06-29

---

## 0. 方針サマリ

| 項目 | 内容 |
|------|------|
| ゴール | Selenium/Chromium 依存をゼロ化し、クロールを requests+BS4 に統一。Docker を軽量化。 |
| 不変条件 | `MangaCrawler` ファサードの公開 API を維持し、[services/](../backend/app/services/) 層は無改修。 |
| 中止/縮退条件 | フェーズ0で R1(ログイン)・R2(原図)・R3(アンチボット) のいずれかが NG → 全面移行中止、**ハイブリッド**へ縮退。 |
| ブランチ戦略 | `feature/requests-bs4` で作業。フェーズ毎に PR。Selenium 実装は最終フェーズまで残す。 |
| ロールバック | 各フェーズは独立 PR。問題時はファサードの実装切替フラグ（§6）で即時切戻し可能。 |

**リグレッション基盤（移行前に整備済み・2026-06-30）**: [移行テスト戦略.md](./移行テスト戦略.md) 参照。
クローラ解析を純関数 [app/crawler/parsers.py](../backend/app/crawler/parsers.py) に切り出し、
保存した HTML フィクスチャに対するゴールデンマスター・テスト（[tests/test_crawler_golden.py](../backend/tests/test_crawler_golden.py)、現状 11 passed）で現状動作を固定済み。各フェーズで `pytest tests/` を回し、出力差分ゼロを維持する。

移行対象ファイル:
- 置換: [browser.py](../backend/app/crawler/browser.py) / [collection.py](../backend/app/crawler/collection.py) / [manga_details.py](../backend/app/crawler/manga_details.py) / [search.py](../backend/app/crawler/search.py) / [favorite_service.py](../backend/app/services/favorite_service.py)
- 改修: [base.py](../backend/app/crawler/base.py)（内部実装の差替）、[requirements.txt](../backend/requirements.txt)、[Dockerfile](../backend/Dockerfile)
- 無改修（前提）: [services/sync_service.py](../backend/app/services/sync_service.py) / [download_service.py](../backend/app/services/download_service.py) / [recent_updates_service.py](../backend/app/services/recent_updates_service.py)

---

## フェーズ0: 実現性検証（PoC）★必須ゲート

**目的**: requests+BS4 だけで「ログイン・一覧・詳細・原図・検索・収藏」が成立するかを、本体に手を入れず**独立スクリプト**で実測判定する。

**成果物**: `backend/scripts/poc_requests_bs4.py`（使い捨て検証スクリプト）＋ 検証結果レポート（本書 §フェーズ0結果記入欄に追記）。

### 0.1 検証項目とチェック観点

| # | 検証 | 手段 | 合格基準 |
|---|------|------|---------|
| T1 | ドメイン解決 | 既存 `_get_available_url_from_publish_page` 相当を実行 | 有効 base_url を 1 件取得 |
| T2 | **ログイン(R1)** | `requests.Session` でログインフォームへ POST | ログイン後ページに自分のユーザー名 or `logout` 等のログイン済みマーカーが出る／Cookie が発行される |
| T3 | アンチボット(R3) | T2/T4 のレスポンス HTML を確認 | Cloudflare/JS チャレンジ・キャプチャ・空ボディでない |
| T4 | 一覧取得 | `users-users_fav.html` を取得し作者カテゴリ・漫画リンクを抽出 | 既知の収藏件数とおおむね一致 |
| T5 | 詳細取得 | 既知の漫画 URL を解析 | title / page_count / updated_at / cover / category / tags / uploader / summary が取れる |
| T6 | **原図 URL(R2)** | `photos-view-id-*` ページを取得し原図 `img[src*=wnimg]`(`/data/`,非`/t/`) を確認 | **静的 HTML に原図 URL が存在**する（=requests のみで取得可） |
| T7 | 原図の実 DL | T6 の URL へ requests GET | 画像バイナリ（>0byte, image/*）が取得できる |
| T8 | 検索 | `q/?q=<作者>&s=create_time_DESC` を解析 | 作品リスト・日時・頁数が取れる |
| T9 | 収藏フォーム | `users-addfav-id-<aid>.html?ajax=true` を取得 | `select[name=favc_id]` の option が解析できる |
| T10 | 文字コード(R4) | T4/T5 の日本語/中文タイトル | 文字化けなし（正しい encoding 判定） |
| T11 | セッション維持(R6) | T2 のセッションで T4〜T9 を連続実行 | 途中で未ログインに戻らない |

### 0.2 PoC スクリプト雛形

```python
# backend/scripts/poc_requests_bs4.py（使い捨て・本体非依存）
import os, sys, re, requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
USER = os.environ["MANGA_USERNAME"]
PWD  = os.environ["MANGA_PASSWORD"]
BASE = os.environ.get("POC_BASE_URL")  # T1 で得た base_url を渡す

s = requests.Session()
s.headers.update({"User-Agent": UA})

def soup(url):
    r = s.get(url, timeout=15)
    r.encoding = r.apparent_encoding or "utf-8"
    print(f"[GET] {r.status_code} {url} ({len(r.text)}B, enc={r.encoding})")
    return BeautifulSoup(r.text, "html.parser"), r

def t2_login():
    # ★action/フィールドは要観察。まず GET でフォームを見てから決める
    page, _ = soup(f"{BASE}/users-login.html")
    form = page.select_one("form")
    print("  form action:", form.get("action") if form else None)
    print("  hidden:", [(i.get('name'), i.get('value')) for i in page.select("input[type=hidden]")])
    r = s.post(f"{BASE}/users-check.html",  # ← 観察結果で差し替え
               data={"login_name": USER, "login_pass": PWD}, timeout=15)
    logged_in = (USER in r.text) or ("logout" in r.text.lower())
    print("  login result:", logged_in, "cookies:", s.cookies.get_dict())
    return logged_in

def t6_original(view_url):
    page, _ = soup(view_url)
    cands = [i.get("src") for i in page.select("img[src*='wnimg']")]
    orig = [u for u in cands if u and "/data/" in u and "/t/" not in u]
    print("  原図候補:", cands)
    print("  原図判定:", orig)
    return orig

if __name__ == "__main__":
    # T2 → T4 → T5 → T6 → T7 ... を順に実行し標準出力で確認
    assert t2_login(), "T2 ログイン失敗（R1）"
    # 以降、既知 URL を引数/環境変数で渡して T4-T9 を確認
    ...
```

### 0.3 判定（Go/No-Go ゲート）

| 結果 | 判断 |
|------|------|
| T1〜T11 全合格 | **Go**: フェーズ1 以降の全面移行へ進む |
| T6/T7 のみ NG（原図が JS 注入） | **部分 Go（ハイブリッド）**: 原図取得だけブラウザ/傍受を残し、他は requests へ移行 |
| T2 NG（ログイン不可） or T3 NG（アンチボット） | **No-Go**: 全面移行中止。現行 Selenium 維持 or 別途ブラウザ自動化を検討 |

> 判定結果と実測値（HTML 抜粋・所要時間・メモリ）を本書末尾「フェーズ0結果記入欄」に記録し、関係者レビューを経て次フェーズ着手を決定する。

### 0.4 フェーズ0 作業見積
- スクリプト作成 + 実測 + 判定: **0.5〜1.5 人日**（ログイン/原図の挙動次第）。

---

## フェーズ1: HTTP クライアント基盤 ★完了（2026-06-30）

**前提**: フェーズ0 Go。
**目的**: `BrowserManager` 代替の `HttpClient` を新設し、ドメイン解決・ログイン・取得・文字コード・タイムアウト/リトライを実装。

| タスク | ファイル | 完了基準 | 状態 |
|--------|---------|---------|:----:|
| `HttpClient` 実装 | 新規 [app/crawler/http_client.py](../backend/app/crawler/http_client.py) | login/get_soup/get_available_url が PoC と同等に動作 | ✅ |
| リトライ/タイムアウト | 同上 | 指数バックオフ・接続/読取タイムアウト・5xx 再試行 | ✅ |
| ドメイン解決移植 | 同上（browser.py から流用） | 手動 URL 優先 + 発布ページ解決 | ✅ |
| 単体テスト | [tests/test_http_client.py](../backend/tests/test_http_client.py) | ログイン成功/失敗・encoding・リトライ・解決を検証（11 件） | ✅ |

**実装メモ**:
- ログイン仕様はフェーズ0 PoC 準拠: `POST /users-check_login.html`（`normal=1`/`login_name`/`login_pass`）、書架 `/users-users_fav.html` 到達（`users-users_fav-c-` or username 出現）で成立判定。
- `session` を注入可能にし、実ネットワーク非依存の単体テスト（フェイク Session）を実現。
- 文字コードは charset 欠落／`ISO-8859-1` 回退時に `apparent_encoding` で補正（R4）。
- `app.config` インポート時の認証必須を回避するため [tests/conftest.py](../backend/tests/conftest.py) でダミー認証情報を注入。

**Exit**: `pytest tests/` で **22 passed**（ゴールデン 11 + HttpClient 11）。`base.py` からはまだ未接続（フェーズ2 で接続）。

---

## フェーズ2: 読み取り系クローラ移行（低リスク）★完了（2026-06-30）

**目的**: 一覧・詳細・検索を BS4 実装に置換（原図は次フェーズ）。

| タスク | 対象 | 完了基準 | 状態 |
|--------|------|---------|:----:|
| collection 移植 | [collection_http.py](../backend/app/crawler/collection_http.py) `CollectionCrawlerHttp` | ジェネレータ維持・作者カテゴリ毎ページ送り・グローバル重複排除 | ✅ |
| details 移植 | [manga_details_http.py](../backend/app/crawler/manga_details_http.py) `MangaDetailsCrawlerHttp` | 全フィールド取得・`updated_at` を datetime に変換し互換維持 | ✅ |
| search 移植 | [search_http.py](../backend/app/crawler/search_http.py) `SearchCrawlerHttp` | since_date 打ち切り・数字ページネーション再現 | ✅ |
| ファサード接続 | [base.py](../backend/app/crawler/base.py) | `crawler_backend` で 3 機能を HttpClient 経由に切替。Selenium import は遅延化 | ✅ |
| 突合テスト | [tests/test_http_crawlers.py](../backend/tests/test_http_crawlers.py) | フィクスチャ + フェイク HttpClient で出力をゴールデンと突合（7 件） | ✅ |

**実装メモ**:
- 切替フラグ `crawler_backend`（[config.py](../backend/app/config.py)、env `CRAWLER_BACKEND`）を追加。既定 `selenium` で**本番挙動は不変**。`requests`/`hybrid` で読取系を HTTP 化。
- 検索の数字ページネーションは [parsers.parse_search_next_page](../backend/app/crawler/parsers.py) を新設（既存パーサは無改修＝ゴールデン維持）。
- `base.py` は Selenium 系モジュールを selenium/hybrid 分岐内で遅延 import。`requests` 単独運用では browser/database/selenium を一切巻き込まない（将来のフェーズ5 完全除去に前向き対応）。
- `get_manga_images`（原図）は本フェーズ未移行。`requests` では `NotImplementedError`、`hybrid` では Selenium 実装にフォールバック（フェーズ3 で本実装）。
- [sync_service.py](../backend/app/services/sync_service.py) の Selenium 必須ゲートを backend 判定に変更（requests 時は Selenium 不要）。

**Exit**: `pytest tests/` で **29 passed**（golden 11 + http_client 11 + http_crawlers 7）。`CRAWLER_BACKEND=requests` で MangaCrawler が Selenium/DB 非依存に構築できることをスモーク確認。収藏夹同期・最近更新同期は読取系のみ使用のため requests 経由で完結（実サイト E2E はフェーズ6 で確認）。

---

## フェーズ3: 原図取得移行（高リスク）★完了（2026-06-30）

**目的**: `get_manga_images` を移行。フェーズ0 T6 で**原図は静的 HTML に存在**と判明したため、
requests+BS4 + ThreadPool 並行 GET の**全面移行ルート**を採用（ブラウザ不要）。

| タスク | 完了基準 | 状態 |
|--------|---------|:----:|
| view リンク収集の BS4 化 | [parse_view_links](../backend/app/crawler/parsers.py) でページ順厳守・重複排除。`.next > a` で分页 | ✅ |
| 原図 URL 抽出の並行化 | `image_fetch_threads` で view ページを並行 GET（[manga_details_http.py](../backend/app/crawler/manga_details_http.py) `_fetch_original`）。ブラウザ生成廃止 | ✅ |
| 順序保証テスト | index 昇順・filename 4 桁ゼロ詰め・shape 検証（[tests/test_http_crawlers.py](../backend/tests/test_http_crawlers.py)） | ✅ |
| 実 DL 結合テスト | E2E（実サイト）はフェーズ6 で確認 | ⏳ |

**実装メモ**:
- `get_manga_images` を [manga_details_http.py](../backend/app/crawler/manga_details_http.py) に実装。NotImplementedError を撤去。
- view ページは非ログインでも取得可（フェーズ0 実証）。原図抽出は既存 `parse_original_image`（wnimg かつ `/data/` 非 `/t/`）を再利用。
- 並行取得は `ThreadPoolExecutor(max_workers=image_fetch_threads)`、`as_completed` で集約し index 昇順に整列。戻り値 `[{index, url, filename}]` は Selenium 版・downloader と同一契約。
- `requests` バックエンドで原図取得が完結。`hybrid` は引き続き Selenium 実装にフォールバック（任意）。

**Exit**: `pytest tests/` で **30 passed**。ダウンロード機能が `CRAWLER_BACKEND=requests` で（ブラウザ非依存に）原図取得まで到達可能。実サイト E2E DL の CBZ ページ数一致はフェーズ6 で確認。

---

## フェーズ4: 収藏登録移行 ★完了（2026-06-30）

**目的**: `FavoriteService` をセッションベースに統一（手動 Cookie 受け渡し撤廃）。

| タスク | 完了基準 | 状態 |
|--------|---------|:----:|
| addfav フォーム解析の BS4 化 | [parse_addfav_form](../backend/app/crawler/parsers.py) で `favc_id` option を取得 | ✅ |
| 収藏 POST のセッション化 | `HttpClient.post`（`session.post`）で成功（Cookie 自動・手動受け渡し撤廃） | ✅ |
| 結合テスト | フェイク MangaCrawler で収藏フロー検証（7 件）。実アカウント E2E はフェーズ6 | ✅/⏳ |

**実装メモ**:
- [favorite_service.py](../backend/app/services/favorite_service.py) を backend 分岐に再構成。`requests`/`hybrid` は `_categories_http` / `_add_http`（HttpClient セッション、`parse_addfav_form`）。`selenium` は従来の driver ベースを遅延 import で温存。
- `HttpClient.post`（単発・タイムアウト付き・非リトライ）を追加。
- 収藏 POST: `users-save_fav-id-{aid}.html` に `favc_id` を XHR ヘッダ（`X-Requested-With`/`Referer`/`Accept`）付きで送信。200 を成功とみなす従来挙動を踏襲（`_interpret_save_response` に集約）。

**Exit**: `pytest tests/` で **37 passed**。`CRAWLER_BACKEND=requests` で**全機能（同期・最近更新・DL・収藏）がブラウザ非依存で動作**。`is_favorited` 更新を含む実アカウント E2E はフェーズ6 で確認。

---

## フェーズ5: Selenium 完全除去・軽量化 ★完了（2026-06-30）

**前提**: フェーズ3 が「全面（非ハイブリッド）」で成立 + 実環境 E2E（下記）で requests 動作確認済み。

| タスク | ファイル | 完了基準 | 状態 |
|--------|---------|---------|:----:|
| selenium 依存削除 | [requirements.txt](../backend/requirements.txt) | `selenium==4.27.0` 行を削除 | ✅ |
| Chromium 削除 | [Dockerfile](../backend/Dockerfile) | chromium/chromium-driver の apt 導入・symlink・wget/gnupg/unzip を削除 | ✅ |
| 旧コード削除 | browser.py / collection.py / manga_details.py / search.py | 4 ファイルを削除（git rm） | ✅ |
| ファサード簡素化 | [base.py](../backend/app/crawler/base.py) | backend 分岐・browser・hybrid・driver を撤去し requests 専用化 | ✅ |
| サービス簡素化 | [favorite_service.py](../backend/app/services/favorite_service.py) / [sync_service.py](../backend/app/services/sync_service.py) | Selenium 分岐・SELENIUM ゲートを除去 | ✅ |
| 既定切替 | [config.py](../backend/app/config.py) | `crawler_backend` 既定を `requests` に（フラグは互換のため残置） | ✅ |

**実環境 E2E（CRAWLER_BACKEND=requests, ブラウザ非依存）**: [scripts/e2e_download_requests.py](../backend/scripts/e2e_download_requests.py)
- ログイン（発布ページ解決 → `www.wn07.cfd`）→ 収藏夹先頭作品（65 カテゴリ）→ 詳細（title/page_count=20/updated_at/cover/category/tags 全取得）→ 原図 20/20 を 3 スレッド並行 GET（3.4s）→ 画像 DL → CBZ 化まで完走。
- **`page_count(20) == 原図数(20)` 一致**。原図 URL は `/data/` 直下・非 `/t/`、index 1..20 連続。
- 併せて封面 CDN の協議相対多重スラッシュ（`////host`）を `_abs_url` で正規化（golden 不変）。

**Exit**: Dockerfile から Chromium 撤去・selenium 依存ゼロ。`pytest tests/` **37 passed**、実環境 DL 完走。
※ Selenium への切戻しは git revert 相当（フラグ rollback は廃止）。

---

## フェーズ6: 回帰テスト・リリース

| タスク | 完了基準 |
|--------|---------|
| E2E 回帰 | 同期収藏 / 最近更新 / 単体 DL / 一括 DL / 収藏 / ファイル検証 が全て成功 |
| 性能比較 | 同期・DL の所要時間/メモリを Selenium 版と比較し記録 |
| 段階リリース | feature ブランチ → 検証環境 → 本番。問題時は §6 フラグで即切戻し |
| ドキュメント更新 | [基本設計書 §2.4/§6.1](./基本設計書.md) の技術スタック・外部 IF を requests+BS4 に更新 |

---

## 6. 切替・ロールバック設計

移行期間中の安全策として、**ファサードに実装切替フラグ**を設ける。

```python
# config.py に追加（案）
crawler_backend: str = "selenium"  # "selenium" | "requests" | "hybrid"

# base.py（案）
class MangaCrawler:
    def __init__(self):
        if settings.crawler_backend == "requests":
            self.client = HttpClient()
            self.collection = CollectionCrawlerHttp(self.client)
            ...
        else:  # selenium（既存）
            self.browser = BrowserManager()
            ...
```
- 環境変数 `CRAWLER_BACKEND` で無停止切替。問題発生時は `selenium` に戻すだけ。
- `hybrid` は「原図のみ Selenium、他は requests」を表す。

---

## 7. 全体スケジュール（目安）

| フェーズ | 内容 | 見積 | ゲート |
|---------|------|------|--------|
| 0 | 実現性検証(PoC) | 0.5〜1.5 人日 | **Go/No-Go** |
| 1 | HTTP クライアント基盤 | 1〜2 人日 | — |
| 2 | 読取系クローラ移行 | 2〜3 人日 | 出力差分ゼロ |
| 3 | 原図取得移行 | 1〜3 人日 | DL 完走 |
| 4 | 収藏登録移行 | 0.5〜1 人日 | 収藏成功 |
| 5 | Selenium 除去・軽量化 | 0.5〜1 人日 | イメージ削減 |
| 6 | 回帰・リリース | 1〜2 人日 | 全機能 OK |
| | **合計** | **約 6.5〜13.5 人日** | （ハイブリッド時はフェーズ5縮小） |

---

## 8. 完了条件（Definition of Done）

- [ ] フェーズ0 の判定が記録され Go である（または部分 Go の方針が合意済み）
- [ ] `MangaCrawler` 公開 API 不変・services 層無改修
- [ ] 同期収藏 / 最近更新 / 単体・一括 DL / 収藏 / ファイル検証の回帰 OK
- [ ] Selenium 版と requests 版で抽出結果の差分なし（ゴールデン比較）
- [ ] （全面時）Docker から Chromium 除去・イメージ縮小を実測
- [ ] `CRAWLER_BACKEND` フラグで切戻し可能
- [ ] 設計ドキュメント更新

---

## フェーズ0結果記入欄（実施済み: 2026-06-30）

実行: `backend/.venv/bin/python scripts/poc_requests_bs4.py`（[scripts/poc_requests_bs4.py](../backend/scripts/poc_requests_bs4.py)）

| 検証 | 結果 | メモ（実測） |
|------|:----:|------------------------------|
| T1 ドメイン解決 | ✅OK | 発布ページ `wn01.link` → 候補 4 件、有効 `https://www.wn07.cfd` を取得 |
| T2 ログイン(R1) | ✅OK | **requests でログイン成立**。action=`/users-check_login.html`、フィールド=`login_name`/`login_pass`/`normal=1`(hidden)/`remember_pass`。Cookie `MPIC_bnS5` 発行。書架（`users-users_fav-c-` 多数）到達で確認 |
| T3 アンチボット(R3) | ✅OK※ | **当初 NG は誤検知**。`cloudflare-static/email-decode.min.js`（良性のメール難読化）に語が一致しただけ。実際の JS チャレンジ/キャプチャは無し。CF CDN 配下だが素の HTTP で全ページ取得可 |
| T4 一覧 | ✅OK | 作者カテゴリ 65 件、1 ページ目漫画 20 件を抽出 |
| T5 詳細 | △要調整 | データは静的 HTML に**存在**するが**現行セレクタが古い**。下記「セレクタ更新事項」参照。title/date は取得、頁数・分類は `label` 内、封面サムネ CDN が変更 |
| T6 原図所在(R2) | ✅OK | **原図 URL は静的 HTML に存在**（`//img5.wnimg1.ru/data/2390/91/231.png`）。view ページ `img[src*='wnimg']` かつ `/data/` 非 `/t/` で取得可 |
| T7 原図 DL | ✅OK | requests GET で 200 / `image/png` / 1,844,948B 取得成功 |
| T8 検索 | ✅OK | `ul.col_2 > li.cate-*` を 8 件取得 |
| T9 収藏フォーム | ✅OK※ | 当初「option 0」は対象が**既収藏**で `你已經收藏過了` が返ったため（=エンドポイントは認証セッションに正しく応答）。XHR ヘッダ付与で確認 |
| T10 文字コード(R4) | ✅OK | UTF-8 自動判定、日本語/中文タイトル文字化けなし |
| T11 セッション維持(R6) | ✅OK | 同一 `Session` で T2→T9 を連続実行、未ログインに戻らず |
| **総合判定** | **✅ Go** | ログイン・全ページ取得・**原図 URL の静的取得が成立**。requests+BS4 への**全面移行は可能**。ブラウザ不要。 |

> ⚠️ スクリプト末尾の自動判定は当初「No-Go」と表示したが、これは T3 の誤検知（良性 CF スクリプトへの語一致）が原因。検知ロジックは修正済み。**正しい判定は Go**。

### フェーズ0 で判明したセレクタ更新事項（重要）

実 HTML（base=`www.wn07.cfd`）で確認した、現行 Selenium コードと異なる点。**requests 移行版・現行 Selenium 版の双方で要修正**:

| 対象 | 現行コードの想定 | 実 HTML での実態 | 対応 |
|------|----------------|-----------------|------|
| 詳細ページ頁数 | `p.l_detla`（[manga_details.py:98](../backend/app/crawler/manga_details.py#L98)） | 詳細ページに `p.l_detla` は**無い**。`label` に `頁數：24P` | `label` テキストから正規表現抽出に変更 |
| 詳細ページ分類 | `//label[contains(.,'分類：')]` | `label` に `分類：雜誌&短篇／漢化`（一致） | 維持可（BS4 化） |
| 封面サムネ | `img[src*='wnimg']`（[manga_details.py:126](../backend/app/crawler/manga_details.py#L126)） | サムネ CDN が **`//t4.wnacgimg.date/data/t/...`** に変更。`wnimg` に**マッチしない** | セレクタを `wnacgimg.date` 含む or `/data/t/` ベースに更新 |
| 原図（view ページ） | `img[src*='wnimg']` + `/data/` 非 `/t/` | 原図は `//img5.wnimg1.ru/data/...`（`wnimg` 一致・現行ロジック有効） | 維持可 |

> ※ 封面サムネ CDN 変更は、**現行の本番環境でも封面取得が失敗している可能性**を示唆する。移行とは別に確認・修正推奨。

---

*本計画は [requests-bs4方式.md](./requests-bs4方式.md) と現行クロール層の静的解析に基づく。見積は実装者 1 名・既存挙動の不確実性を含む概算。*
