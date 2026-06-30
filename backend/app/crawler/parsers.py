"""HTML 解析の純関数群（ブラウザ非依存・副作用なし）

移行方針: Selenium が取得した DOM / requests が取得した HTML のどちらに対しても、
ここに集約した純粋な解析関数を適用する。入力は HTML 文字列、出力は JSON 化可能な
プレーンな dict/list。これによりゴールデンマスター・テストで「現状の解析挙動」を固定し、
requests+BeautifulSoup 移行後も同一出力を再現できることを保証する。

セレクタは現行クローラ（collection.py / manga_details.py / search.py）に忠実に合わせ、
フェーズ0 で判明した改版（封面 CDN 変更・詳細頁数の label 移動）の修正を反映する。
"""
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

# 収藏カテゴリ抽出時に除外する作者以外の分類名（collection.py と一致）
EXCLUDED_CATEGORY_NAMES = ["全部", "管理分類", "書架", "书架", "我的書架"]


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _abs_url(href: Optional[str], base: str) -> Optional[str]:
    """相対 URL / 協議相対 URL を絶対化（current crawler のロジックに準拠）"""
    if not href:
        return None
    base = base.rstrip("/")
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"{base}{href}"
    return f"{base}/{href}"


def _page_count_near(anchor) -> Optional[int]:
    """漫画リンク近傍の p.l_detla から頁数を抽出（list ページ用）"""
    node = anchor
    for _ in range(6):
        node = node.parent
        if node is None:
            break
        el = node.select_one("p.l_detla") if hasattr(node, "select_one") else None
        if el:
            m = re.search(r"(\d+)\s*P?", el.get_text())
            if m:
                return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# 収藏（書架）系
# ---------------------------------------------------------------------------
def parse_favorite_categories(html: str) -> Dict[str, str]:
    """書架ページから作者カテゴリ {作者名: href} を抽出"""
    soup = _soup(html)
    cats: Dict[str, str] = {}
    for a in soup.select("a[href*='users-users_fav-c-']"):
        text = a.get_text(strip=True)
        if text and text not in EXCLUDED_CATEGORY_NAMES:
            cats[text] = a.get("href")
    return cats


def parse_collection_page(html: str, base: str) -> Dict:
    """カテゴリ/書架ページから漫画リスト + 次ページリンクを抽出

    Returns: {"mangas": [{title, manga_url, page_count}], "next_url": str|None}
    """
    soup = _soup(html)
    mangas: List[Dict] = []
    seen = set()
    for a in soup.select("a[href*='photos-index-aid-']"):
        title = a.get_text(strip=True)
        url = _abs_url(a.get("href"), base)
        if not title or not url or url in seen:
            continue
        seen.add(url)
        mangas.append({
            "title": title,
            "manga_url": url,
            "page_count": _page_count_near(a),
        })
    nxt = soup.select_one(".paginator .next > a")
    next_url = _abs_url(nxt.get("href"), base) if nxt and nxt.get("href") else None
    return {"mangas": mangas, "next_url": next_url}


# ---------------------------------------------------------------------------
# 詳細ページ
# ---------------------------------------------------------------------------
def _label_text_after(soup, marker: str) -> Optional[str]:
    """label/p で marker（例「分類：」）を含む要素のテキストから marker 以降を返す"""
    for tag in soup.find_all(["label", "p"]):
        t = tag.get_text(strip=True)
        if t and marker in t:
            return t.split(marker, 1)[1].strip() or None
    return None


def parse_details(html: str, manga_url: str = "", base: str = "") -> Dict:
    """詳細ページから漫画メタデータを抽出

    Returns: {title, manga_url, page_count, updated_at(str|None),
              cover_image_url, category, tags[], uploader, summary}
    """
    soup = _soup(html)
    base = base or _origin(manga_url)

    title_el = soup.select_one("h2")
    title = title_el.get_text(strip=True) if title_el else None

    # 頁数: p.l_detla 優先、無ければ label「頁數：N」回退（改版対応）
    page_count = None
    pc_el = soup.select_one("p.l_detla")
    if pc_el:
        m = re.search(r"(\d+)\s*P?", pc_el.get_text())
        if m:
            page_count = int(m.group(1))
    if page_count is None:
        for lb in soup.find_all("label"):
            lt = lb.get_text()
            if "頁數" in lt or "页数" in lt:
                m = re.search(r"(\d+)\s*P?", lt)
                if m:
                    page_count = int(m.group(1))
                    break

    # 更新日: .gallary_item の最初から YYYY-MM-DD
    updated_at = None
    gi = soup.select_one(".gallary_item")
    if gi:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", gi.get_text())
        if m:
            updated_at = m.group(1)

    # 封面: .uwthumb img 優先、無ければ /data/ サムネ（改版対応）
    cover = soup.select_one(".uwthumb img")
    if not cover:
        cover = soup.select_one("img[src*='/data/']")
    cover_url = _abs_url(cover.get("src"), base) if cover else None

    category = _label_text_after(soup, "分類：")

    tags = []
    for a in soup.select("a[href*='albums-index-tag-']"):
        t = a.get_text(strip=True)
        if t and t != "+TAG":
            tags.append(t)

    uploader = None
    up = soup.select_one("a[href*='search/index.php'] img[src*='userpic']")
    if up:
        a = up.find_parent("a")
        uploader = a.get_text(strip=True) if a else None

    summary = None
    sm = soup.find(["p", "label"], string=lambda s: s and "簡介：" in s)
    if sm:
        nxt = sm.find_next_sibling()
        if nxt:
            summary = nxt.get_text(strip=True) or None

    return {
        "title": title,
        "manga_url": manga_url,
        "page_count": page_count,
        "updated_at": updated_at,
        "cover_image_url": cover_url,
        "category": category,
        "tags": tags,
        "uploader": uploader,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# 画像（view）ページ
# ---------------------------------------------------------------------------
def parse_view_links(html: str, base: str) -> List[str]:
    """詳細ページ内の画像閲覧リンク photos-view-id-* を表示順で抽出（重複排除）"""
    soup = _soup(html)
    out, seen = [], set()
    for a in soup.select("a[href*='photos-view-id-']"):
        url = _abs_url(a.get("href"), base)
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def parse_original_image(html: str) -> Optional[str]:
    """view ページから原図 URL を抽出（wnimg かつ /data/ かつ 非 /t/）"""
    soup = _soup(html)
    for img in soup.select("img[src*='wnimg']"):
        src = img.get("src")
        if src and "/data/" in src and "/t/" not in src:
            return f"https:{src}" if src.startswith("//") else src
    return None


def parse_next_page(html: str, base: str, kind: str = "fav") -> Optional[str]:
    """.paginator .next > a の次ページ URL（fav / photos 共通の「後頁」リンク）"""
    soup = _soup(html)
    nxt = soup.select_one(".paginator .next > a")
    return _abs_url(nxt.get("href"), base) if nxt and nxt.get("href") else None


# ---------------------------------------------------------------------------
# 検索ページ
# ---------------------------------------------------------------------------
def parse_search_page(html: str, base: str, author: str = "") -> List[Dict]:
    """検索結果ページから作品リストを抽出（search.py のセレクタに準拠）

    Returns: [{title, manga_url, updated_at(str|None), page_count, cover_image_url, author}]
    """
    soup = _soup(html)
    out: List[Dict] = []
    container = soup.select_one("ul.col_2")
    items = container.select("li[class*='cate-']") if container else []
    for item in items:
        a = item.select_one("a[href*='photos-index-aid-']")
        if not a:
            continue
        title = a.get_text(strip=True)
        url = _abs_url(a.get("href"), base)
        if not title or not url:
            continue
        updated_at = None
        page_count = None
        info = item.select_one("span.info")
        if info:
            it = info.get_text()
            m = re.search(r"创建于(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})", it)
            if m:
                updated_at = f"{m.group(1)} {m.group(2)}"
            else:
                m = re.search(r"创建于(\d{4}-\d{2}-\d{2})", it)
                if m:
                    updated_at = m.group(1)
            pm = re.search(r"(\d+)张图片", it)
            if pm:
                page_count = int(pm.group(1))
        img = item.select_one("img[src*='wnimg'], img[src*='qy0'], img[src*='/data/']")
        cover = _abs_url(img.get("src"), base) if img else None
        out.append({
            "title": title,
            "manga_url": url,
            "updated_at": updated_at,
            "page_count": page_count,
            "cover_image_url": cover,
            "author": author,
        })
    return out


# ---------------------------------------------------------------------------
# 収藏フォーム
# ---------------------------------------------------------------------------
def parse_addfav_form(html: str) -> Dict[str, str]:
    """収藏フォームの favc_id option を {value: 名称} で抽出"""
    soup = _soup(html)
    sel = soup.select_one("select[name='favc_id']")
    if not sel:
        return {}
    out = {}
    for o in sel.select("option"):
        v = o.get("value")
        t = o.get_text(strip=True)
        if v and t and t != "請選擇收藏分類":
            out[v] = t
    return out


def _origin(url: str) -> str:
    m = re.match(r"(https?://[^/]+)", url or "")
    return m.group(1) if m else ""
