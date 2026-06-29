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

## フェーズ1: HTTP クライアント基盤

**前提**: フェーズ0 Go。
**目的**: `BrowserManager` 代替の `HttpClient` を新設し、ドメイン解決・ログイン・取得・文字コード・タイムアウト/リトライを実装。

| タスク | ファイル | 完了基準 |
|--------|---------|---------|
| `HttpClient` 実装 | 新規 `app/crawler/http_client.py` | login/get_soup/get_available_url が PoC と同等に動作 |
| リトライ/タイムアウト | 同上 | 指数バックオフ・接続/読取タイムアウト実装 |
| ドメイン解決移植 | 同上（browser.py から流用） | 手動 URL 優先 + 発布ページ解決 |
| 単体テスト | `tests/test_http_client.py` | ログイン成功/失敗・encoding を検証 |

**Exit**: `HttpClient().login()` が CI/ローカルで成功。`base.py` からはまだ未接続。

---

## フェーズ2: 読み取り系クローラ移行（低リスク）

**目的**: 一覧・詳細・検索を BS4 実装に置換（原図は次フェーズ）。

| タスク | 対象 | 完了基準 |
|--------|------|---------|
| collection 移植 | `CollectionCrawler` | ジェネレータ維持・既存収藏件数と一致 |
| details 移植 | `get_manga_details` | 全フィールド取得（XPath 系は BS4 化） |
| search 移植 | `SearchCrawler` | 打ち切り・数字ページネーション再現 |
| ファサード接続 | `base.py` | これら 3 機能を HttpClient 経由に切替 |
| 突合テスト | `tests/` | Selenium 版と同一入力で出力差分なし（ゴールデン比較） |

**検証**: 同一漫画 URL/作者で Selenium 版と requests 版の出力を比較（タイトル・頁数・日付・タグの一致率 100% を目標）。

**Exit**: 収藏夹同期・最近更新同期が requests 経由で従来同等の結果。

---

## フェーズ3: 原図取得移行（高リスク）

**目的**: `get_manga_images` を移行。フェーズ0 の T6 結果で実装方針が分岐。

| フェーズ0 結果 | 実装 |
|----------------|------|
| 原図が静的 HTML | requests+BS4 + ThreadPool 並行 GET（[方式 §3.3](./requests-bs4方式.md)） |
| 原図が JS 注入 | **ハイブリッド**: この機能のみ Playwright/Selenium 温存、または view ページ内 JS/`data-*` から URL 再構成 |

| タスク | 完了基準 |
|--------|---------|
| view リンク収集の BS4 化 | ページ順厳守・重複排除を維持 |
| 原図 URL 抽出の並行化 | `image_fetch_threads` で並行 HTTP（ブラウザ生成廃止） |
| 順序保証テスト | 取得画像の index 昇順・欠落なし |
| 実 DL 結合テスト | 既知漫画を E2E DL し CBZ が現行と同一ページ数 |

**Exit**: ダウンロード機能が requests 経由（または明示ハイブリッド）で完走。

---

## フェーズ4: 収藏登録移行

**目的**: `FavoriteService` をセッションベースに統一（手動 Cookie 受け渡し撤廃）。

| タスク | 完了基準 |
|--------|---------|
| addfav フォーム解析の BS4 化 | `favc_id` option を取得 |
| 収藏 POST のセッション化 | `client.session.post` で成功（Cookie 自動） |
| 結合テスト | 実アカウントで収藏成功・`is_favorited` 更新 |

**Exit**: 収藏機能が requests のみで動作。

---

## フェーズ5: Selenium 完全除去・軽量化

**前提**: フェーズ3 が「全面（非ハイブリッド）」で成立した場合のみ完全除去。ハイブリッド時は原図分の依存を残す。

| タスク | ファイル | 完了基準 |
|--------|---------|---------|
| selenium 依存削除 | [requirements.txt](../backend/requirements.txt) | `selenium` 行を削除 |
| Chromium 削除 | [Dockerfile](../backend/Dockerfile#L6) | chromium/chromium-driver の apt 導入・symlink を削除 |
| 旧コード削除 | browser.py / 各 crawler の Selenium 分岐 | デッドコード除去 |
| イメージ計測 | — | イメージサイズ削減を実測記録 |

**Exit**: Docker イメージから Chromium が消え、ビルド成功・全機能回帰 OK。

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

## フェーズ0結果記入欄（実施後に追記）

| 検証 | 結果(OK/NG) | メモ（HTML 抜粋・所要・備考） |
|------|:----------:|------------------------------|
| T1 ドメイン解決 | | |
| T2 ログイン(R1) | | 実 action= , 必須フィールド= |
| T3 アンチボット(R3) | | |
| T4 一覧 | | 取得件数= |
| T5 詳細 | | 欠落フィールド= |
| T6 原図所在(R2) | | 静的/JS= |
| T7 原図 DL | | content-type= , size= |
| T8 検索 | | |
| T9 収藏フォーム | | option 数= |
| T10 文字コード(R4) | | 判定 encoding= |
| T11 セッション維持(R6) | | |
| **総合判定** | | Go / 部分Go / No-Go |

---

*本計画は [requests-bs4方式.md](./requests-bs4方式.md) と現行クロール層の静的解析に基づく。見積は実装者 1 名・既存挙動の不確実性を含む概算。*
