# requests + BeautifulSoup 方式 設計メモ

> [基本設計書.md](./基本設計書.md) 関連資料。現行の Selenium ベースのクロール層を
> `requests`（HTTP クライアント）+ `BeautifulSoup`（HTML パーサ）へ置き換える場合の **やり方** を定義する。
> 移行の実装計画は [requests-bs4移行計画.md](./requests-bs4移行計画.md) を参照。
> 作成日: 2026-06-29

---

## 1. 背景と狙い

現行クロール層（[backend/app/crawler/](../backend/app/crawler/)）はヘッドレス Chromium を Selenium で操作している。主な課題:

- 原図 URL 取得（[manga_details.py:25](../backend/app/crawler/manga_details.py#L25) `_create_temp_driver`）が **Chrome プロセスを並行で複数生成**し、メモリ・起動コストが高い（NAS で特に重い）。
- 全体に `time.sleep(1.5〜5)` が散在し、低速かつ不安定。
- stale element 対策などブラウザ依存の手作りコードが多い。

一方、対象ページの多くは**サーバサイドレンダリング（PHP 生成 HTML）**とみられ、抽出対象データは静的 HTML 内に存在する可能性が高い。もしそうなら、ブラウザを使わず `requests` でページ取得 → `BeautifulSoup` で解析する方が **最速・最軽量**になる。

> ⚠️ ただし「静的 HTML に必要データが乗っているか」は未検証の前提。特に**原図 URL** と**ログイン**は要検証。実現性は [移行計画 フェーズ0](./requests-bs4移行計画.md#フェーズ0-実現性検証poc) で確定させる。

### 既に requests を使っている箇所
本方式は完全な新規導入ではない。以下は既に `requests` ベース:
- ドメイン解決（発布ページ解析）: [browser.py:104](../backend/app/crawler/browser.py#L104)（requests + BS4）
- 収藏 POST: [favorite_service.py:206](../backend/app/services/favorite_service.py#L206)（Selenium の Cookie を requests に手渡し）
- 画像ダウンロード本体: [download_service.py:38](../backend/app/services/download_service.py#L38)（requests）

つまり**画像 DL と一部はすでに requests**。本方式はクロール（HTML 取得・解析）部分も requests に統一する。

---

## 2. 全体設計

### 2.1 共通 HTTP クライアント（`HttpClient`）

`BrowserManager` を置き換える、セッション・ログイン・取得を担うクラスを新設する。

```python
# 新設: app/crawler/http_client.py（ドラフト）
import requests
from bs4 import BeautifulSoup
from typing import Optional
from app.config import settings
from app.models import AppConfig
from app.database import SessionLocal
from app.utils.logger import logger, get_error_message

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

class HttpClient:
    """requests.Session ベースの HTTP クライアント（BrowserManager 代替）"""

    def __init__(self):
        self.base_url: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_UA})
        self._logged_in = False

    # --- ドメイン解決（現行ロジックを流用） ---
    def get_available_url(self) -> Optional[str]:
        manual = self._get_manual_url()
        if manual:
            return manual
        return self._get_available_url_from_publish_page()  # 既存 browser.py 同等

    # --- HTML 取得 → BeautifulSoup ---
    def get_soup(self, url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            # 文字コード自動判定（GBK/Big5/UTF-8 混在の可能性に注意。§5参照）
            resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logger.warning(f"GET 失敗 {url}: {get_error_message(e)}")
            return None

    # --- ログイン（要フェーズ0で確定） ---
    def login(self, username: str, password: str) -> bool:
        if not self.base_url:
            self.base_url = self.get_available_url()
            if not self.base_url:
                return False
        base = self.base_url.rstrip("/")
        # 想定: フォーム POST。実 action/フィールドはフェーズ0で確定する
        resp = self.session.post(
            f"{base}/users-check.html",   # ← 要検証（暫定）
            data={"login_name": username, "login_pass": password},
            timeout=15,
        )
        ok = resp.status_code == 200 and ("logout" in resp.text or username in resp.text)
        self._logged_in = ok
        return ok

    def close(self):
        self.session.close()
```

設計ポイント:
- **Cookie はセッションが自動保持**するため、収藏 POST 時の手動 Cookie 受け渡し（[favorite_service.py:186](../backend/app/services/favorite_service.py#L186)）が不要になる。
- ブラウザ／chromedriver パス探索（[browser.py:42-76](../backend/app/crawler/browser.py#L42)）が丸ごと不要。
- `MangaCrawler` ファサード（[base.py](../backend/app/crawler/base.py)）の公開 API（`login` / `get_collection_stream` / `get_manga_details` / `get_manga_images` / `search_author_updates` / `close`）は**そのまま維持**し、内部実装だけ差し替える。呼び出し側（services 層）は無改修。

### 2.2 セレクタ移植早見表

現行 Selenium の検索を BeautifulSoup へ機械的に置換できる（セレクタ文字列は流用）。

| Selenium | BeautifulSoup |
|----------|---------------|
| `find_element(By.CSS_SELECTOR, sel)` | `soup.select_one(sel)` |
| `find_elements(By.CSS_SELECTOR, sel)` | `soup.select(sel)` |
| `elem.get_attribute('href')` | `elem.get('href')` / `elem['href']` |
| `elem.text.strip()` | `elem.get_text(strip=True)` |
| `By.NAME, "x"` | `soup.select_one('[name="x"]')` |
| `By.XPATH`（テキスト含有） | `soup.find('label', string=lambda s: s and '分類：' in s)` 等 |
| `WebDriverWait(...).until(...)` | **不要**（同期取得のため待機概念がない） |
| `time.sleep(n)` | **不要**（必要なら礼儀的レート制御として残す。§6） |

> XPath の「テキスト含有 + 兄弟要素」系（分類/標籤/上传者/簡介）は BS4 の `find` + `find_next_sibling` / `find_all_next` で書き換える。フェーズ0で実 HTML を見て確定する。

---

## 3. 機能別の実装方針

各クローラモジュールを requests+BS4 でどう書くか。**セレクタは現行流用**、ページ送りロジックも現行を踏襲する。

### 3.1 収藏夹一覧（collection.py 代替）

現行: [collection.py](../backend/app/crawler/collection.py)。書架 → 作者カテゴリ → ページ巡回。

```python
def get_collection_stream(self):
    base = self.client.base_url.rstrip("/")
    soup = self.client.get_soup(f"{base}/users-users_fav.html")
    if not soup:
        return

    # 作者カテゴリ抽出（除外語スキップは現行同様）
    category_links = {}
    for a in soup.select("a[href*='users-users_fav-c-']"):
        text = a.get_text(strip=True)
        if text and text not in ["全部", "管理分類", "書架", "书架", "我的書架"]:
            category_links[text] = a.get("href")

    seen = set()
    for author, cat_url in category_links.items():
        url = self._abs(cat_url)
        visited = set()
        while url and url not in visited:
            visited.add(url)
            page = self.client.get_soup(url)
            if not page:
                break
            for a in page.select("a[href*='photos-index-aid-']"):
                href = self._abs(a.get("href"))
                title = a.get_text(strip=True)
                if not href or not title or href in seen:
                    continue
                seen.add(href)
                # 页数: 親コンテナの p.l_detla（現行ロジック踏襲）
                page_count = self._extract_page_count(a)
                yield {"title": title, "author": author,
                       "manga_url": href, "page_count": page_count}
            # 次ページ: .next > a（現行同様）
            nxt = page.select_one(".paginator .next > a")
            url = self._abs(nxt.get("href")) if nxt else None
```

ポイント:
- **ジェネレータ（ストリーム）を維持**。services 層の逐次保存ロジックはそのまま使える。
- 「親コンテナを辿って p.l_detla を読む」処理は、BS4 では `a.find_parent(class_=...)` で実装。

### 3.2 漫画詳細（manga_details.py の `get_manga_details` 代替）

静的 HTML 解析。現行のセレクタを流用。

```python
def get_manga_details(self, manga_url):
    soup = self.client.get_soup(manga_url)
    if not soup:
        return None
    title = (soup.select_one("h2").get_text(strip=True)
             if soup.select_one("h2") else None)
    page_count = self._num(soup.select_one("p.l_detla"))      # 頁數：20P → 20
    updated_at = self._date(soup.select_one(".gallary_item")) # YYYY-MM-DD
    cover = soup.select_one("img[src*='wnimg']")
    cover_url = cover.get("src") if cover else None
    category = self._after_label(soup, "分類：")
    tags = [a.get_text(strip=True) for a in
            soup.select("a[href*='albums-index-tag-']")
            if a.get_text(strip=True) not in ("", "+TAG")]
    uploader = self._uploader(soup)
    summary = self._after_label(soup, "簡介：")
    return {"title": title, "manga_url": manga_url, "page_count": page_count,
            "updated_at": updated_at, "cover_image_url": cover_url,
            "category": category, "tags": tags,
            "uploader": uploader, "summary": summary}
```

### 3.3 原図 URL 取得（manga_details.py の `get_manga_images` 代替）★最重要・要検証

現行: 詳細ページ群から `photos-view-id-*` リンクを収集 → 各 view ページを開いて原図 `img` を取得。

**前提が成り立つ場合（原図 URL が静的 HTML にある）**:
```python
def get_manga_images(self, manga_url):
    # 1) view リンク収集（静的解析、ページ順厳守）
    view_urls, url, visited = [], manga_url, set()
    while url and url not in visited:
        visited.add(url)
        soup = self.client.get_soup(url)
        for a in soup.select("a[href*='photos-view-id-']"):
            href = self._abs(a.get("href"))
            if href and href not in view_urls:
                view_urls.append(href)
        nxt = soup.select_one(".paginator .next > a")
        url = self._abs(nxt.get("href")) if nxt else None

    # 2) 原図 URL 抽出（スレッドプールで並行 HTTP GET。ブラウザ不要）
    def fetch(idx, view_url):
        soup = self.client.get_soup(view_url)
        for img in soup.select("img[src*='wnimg']"):
            src = img.get("src")
            if src and "/data/" in src and "/t/" not in src:
                ext = src.split(".")[-1].split("?")[0] or "jpg"
                return {"index": idx, "url": src, "filename": f"{idx:04d}.{ext}"}
        return None

    with ThreadPoolExecutor(max_workers=settings.image_fetch_threads) as ex:
        results = ex.map(lambda p: fetch(*p), enumerate(view_urls, 1))
    return [r for r in sorted(filter(None, results), key=lambda r: r["index"])]
```
→ **Chrome プロセス N 個生成が、軽量な HTTP GET N 並行に置き換わる**（本方式の最大の利得）。

**前提が成り立たない場合（原図 URL が JS で注入される）**:
- この機能だけ **ハイブリッド**（Playwright/Selenium を残す or ネットワーク傍受）にする。
- もしくは原図 URL の生成規則（`photos-view` の HTML 内 JS 変数や、view ページ HTML の別属性 `data-*` 等）を解析して requests のみで再構成する。
- 判断はフェーズ0の結果次第。→ [移行計画](./requests-bs4移行計画.md)。

### 3.4 作者検索（search.py 代替）

静的解析。`ul.col_2 > li.cate-*` から作品・日時・頁数・封面。打ち切りロジック（作成日時降順で基準日以前に達したら停止）と数字ページネーション（`p=N`）を現行どおり踏襲。

### 3.5 収藏登録（favorite_service.py 代替）

現行は既に「Selenium で addfav フォーム取得 → requests で POST」。本方式では:
- addfav フォーム取得を `client.get_soup()` に置換し、`select[name='favc_id']` の option を BS4 で解析。
- POST は `self.client.session.post(...)` を使用（**Cookie はセッションが保持**するため手動受け渡し不要）。

---

## 4. 想定アーキテクチャ（移行後）

```
services 層（無改修）
   │  MangaCrawler（ファサード: 公開 API 維持）
   ▼
 ┌─ HttpClient (requests.Session) ── login / get_soup / base_url
 ├─ CollectionCrawler  (BS4)
 ├─ MangaDetailsCrawler(BS4) ── get_manga_images は要検証
 ├─ SearchCrawler      (BS4)
 └─ FavoriteService    (session.post)
        │
        ▼  HTTP（Cookie 自動保持）
   WNACG サイト
```

- **Selenium への依存をゼロ化**できれば、Docker から chromium/chromedriver を除去でき、イメージが大幅に軽量化（[backend/Dockerfile:6-18](../backend/Dockerfile#L6)）。
- `MangaCrawler` の公開 API を維持するため、[services/](../backend/app/services/) 層は原則無改修。

---

## 5. リスク・未確定事項（フェーズ0で検証）

| ID | 項目 | 内容 | 影響 |
|----|------|------|------|
| R1 | ログイン方式 | フォームの実 action / 必須フィールド（CSRF・hidden）・Cookie 発行が requests で成立するか | 致命的（全機能の前提） |
| R2 | 原図 URL の所在 | `photos-view-id-*` ページの原図 URL が静的 HTML にあるか、JS 注入か | 大（DL 機能の可否） |
| R3 | アンチボット | Cloudflare 等の JS チャレンジ / UA・レート制限で requests がブロックされないか | 致命的 |
| R4 | 文字コード | ページが GBK/Big5/UTF-8 のいずれか。`apparent_encoding` で正しく取れるか | 中（文字化け） |
| R5 | DOM 差異 | ブラウザ描画後 DOM と素の HTML でセレクタ一致するか（特に XPath 系の分類/標籤） | 中 |
| R6 | セッション維持 | 長時間クロール中の Cookie 失効・再ログイン要否 | 中 |

> R1〜R3 のいずれかが NG なら「全面移行」は不可。その場合は**ハイブリッド方針**（ログイン・原図だけブラウザ、他は requests）に縮退する。

---

## 6. 運用上の配慮

- **レート制御**: ブラウザ廃止で高速化する分、サイトへ過負荷をかけないよう `requests` 連打を避ける。ページ取得間に小さな待機（例 0.3〜1 秒）や同時接続数の上限（`image_fetch_threads` 流用）を設ける。
- **タイムアウト/リトライ**: `requests` に明示タイムアウトと指数バックオフ・リトライを実装（現行 Selenium にはない堅牢化ポイント）。
- **User-Agent**: 現行と同一 UA を踏襲。
- **エラーハンドリング**: `get_soup` が None を返した場合のフォールバックを各機能で維持（現行同様、要素単位 try/except）。

---

## 7. 期待効果（フェーズ0クリア前提）

| 指標 | 現行(Selenium) | 移行後(requests+BS4) |
|------|---------------|---------------------|
| 原図取得 | Chrome N プロセス生成 | 軽量 HTTP N 並行 |
| 1 ページ取得 | 固定 sleep 1.5〜5 秒 | レスポンス即時（〜数百 ms） |
| メモリ | ブラウザ常駐で大 | プロセス常駐なし・小 |
| Docker イメージ | chromium 同梱で大 | Python のみで小 |
| 依存 | selenium + chromium/driver | requests + beautifulsoup4（既存） |
| 安定性 | stale element / 描画タイミング依存 | HTTP 応答のみに依存 |

---

*本書はクロール層（[app/crawler/](../backend/app/crawler/)）と [favorite_service.py](../backend/app/services/favorite_service.py) の静的解析に基づく設計案。サンプルコードはドラフトであり、実セレクタ/HTML 構造はフェーズ0で確定する。*
