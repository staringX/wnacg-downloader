"""
フェーズ0 実現性検証 PoC スクリプト（使い捨て）

requests + BeautifulSoup だけで WNACG のクロールが成立するかを検証する。
本体コードには一切依存しない独立スクリプト。

実行: backend ディレクトリで
    .venv/bin/python scripts/poc_requests_bs4.py

認証情報はプロジェクトルートの .env から読み込む。
礼儀的レート制御として各リクエスト間に DELAY 秒のウェイトを入れる。
"""
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DELAY = 1.2  # リクエスト間ウェイト（秒）

results = {}


def load_env():
    """プロジェクトルートの .env を素朴にパース"""
    env = {}
    root = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    with open(os.path.abspath(root), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def mark(tid, ok, note=""):
    results[tid] = (ok, note)
    flag = "OK " if ok else "NG "
    print(f"  [{flag}] {tid}: {note}")


def get(session, url, label=""):
    time.sleep(DELAY)
    r = session.get(url, timeout=15)
    r.encoding = r.apparent_encoding or "utf-8"
    print(f"  [GET] {r.status_code} {url}  ({len(r.text)}B enc={r.encoding}) {label}")
    return r


# ---------------------------------------------------------------------------
# T1: ドメイン解決（発布ページ解析）
# ---------------------------------------------------------------------------
def t1_resolve_domain(publish_url):
    print("\n=== T1: ドメイン解決 ===")
    try:
        r = requests.get(publish_url, timeout=12, headers={"User-Agent": UA})
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        for ul in soup.find_all("ul"):
            for li in ul.find_all("li"):
                for a in li.find_all("a", {"target": "_blank"}, href=True):
                    href = a.get("href", "")
                    if "wn01.link" in href or "google.cn" in href:
                        continue
                    if a.find("i") and href.startswith("http"):
                        urls.append(href)
        if not urls:  # 備用
            for ul in soup.find_all("ul"):
                for li in ul.find_all("li"):
                    for a in li.find_all("a", href=True):
                        href = a.get("href", "")
                        if "wn01.link" in href or "google.cn" in href:
                            continue
                        if href.startswith("http"):
                            urls.append(href)
        print(f"  候補 URL: {urls}")
        for u in urls:
            try:
                tr = requests.get(f"{u}/", timeout=8, headers={"User-Agent": UA})
                if tr.status_code == 200:
                    mark("T1", True, f"有効 base_url = {u}")
                    return u.rstrip("/")
            except Exception:
                continue
        mark("T1", False, "疎通可能な候補なし")
        return None
    except Exception as e:
        mark("T1", False, f"{type(e).__name__}: {str(e)[:120]}")
        return None


# ---------------------------------------------------------------------------
# T2/T3/T10: ログイン + アンチボット + 文字コード
# ---------------------------------------------------------------------------
def t2_login(session, base, user, pwd):
    print("\n=== T2: ログイン ===")
    # まずログインフォームを観察
    r = get(session, f"{base}/users-login.html", "ログインフォーム")

    # T3: アンチボット兆候
    # 注意: "cloudflare-static/email-decode" のような良性スクリプトを誤検知しないよう、
    #       実際の JS チャレンジ/キャプチャを示す語に限定する。
    lowered = r.text.lower()
    antibot_signals = ["cf-browser-verification", "jschl-answer",
                       "challenge-platform", "_cf_chl_opt", "g-recaptcha",
                       "h-captcha", "请完成验证", "請完成驗證"]
    hit = [k for k in antibot_signals if k in lowered]
    # ログインフォーム自体が出ていれば実質チャレンジは無いとみなす
    has_login_form = bool(r.encoding and "login_pass" in r.text)
    antibot = bool(hit) and not has_login_form
    mark("T3", not antibot,
         "アンチボット兆候なし（CF CDN 配下だが素の HTTP で取得可）"
         if not antibot else f"アンチボット/チャレンジ検出: {hit}")

    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    action = form.get("action") if form else None
    hidden = {i.get("name"): i.get("value")
              for i in soup.select("input[type=hidden]") if i.get("name")}
    print(f"  form action = {action}")
    print(f"  hidden fields = {hidden}")
    field_names = [i.get("name") for i in soup.select("input") if i.get("name")]
    print(f"  input names = {field_names}")

    # POST 先を決定（action があればそれ、なければ既知の候補を試行）
    post_targets = []
    if action:
        if action.startswith("http"):
            post_targets.append(action)
        elif action.startswith("/"):
            post_targets.append(f"{base}{action}")
        else:
            post_targets.append(f"{base}/{action}")
    post_targets += [f"{base}/users-check.html", f"{base}/users-login.html"]

    payload = {"login_name": user, "login_pass": pwd}
    payload.update(hidden)  # CSRF 等があれば引き継ぐ

    for target in post_targets:
        try:
            time.sleep(DELAY)
            pr = session.post(target, data=payload, timeout=15,
                              headers={"Referer": f"{base}/users-login.html"})
            cookies = session.cookies.get_dict()
            # ログイン済み判定: ユーザー名出現 or logout リンク or cookie 発行
            body = pr.text
            logged = (user in body) or ("logout" in body.lower()) or \
                     ("users-logout" in body.lower())
            print(f"  [POST] {pr.status_code} {target}  cookies={list(cookies.keys())} logged={logged}")
            if logged or cookies:
                # 確認: マイページ系で再判定
                vr = get(session, f"{base}/users-users_fav.html", "ログイン後の書架")
                ok = ("users-users_fav-c-" in vr.text) or (user in vr.text)
                mark("T2", ok, f"POST先={target} / 書架到達={ok}")

                # T10: 文字コード
                garbled = "�" in vr.text[:5000]
                mark("T10", not garbled,
                     f"enc={vr.encoding} 文字化け={'あり' if garbled else 'なし'}")
                return ok
        except Exception as e:
            print(f"  [POST] FAIL {target}: {type(e).__name__} {str(e)[:100]}")
            continue
    mark("T2", False, "全 POST 候補でログイン不成立")
    return False


# ---------------------------------------------------------------------------
# T4: 収藏一覧
# ---------------------------------------------------------------------------
def t4_collection(session, base):
    print("\n=== T4: 収藏一覧 ===")
    try:
        r = get(session, f"{base}/users-users_fav.html", "書架")
        soup = BeautifulSoup(r.text, "html.parser")
        cats = {}
        for a in soup.select("a[href*='users-users_fav-c-']"):
            t = a.get_text(strip=True)
            if t and t not in ["全部", "管理分類", "書架", "书架", "我的書架"]:
                cats[t] = a.get("href")
        manga = soup.select("a[href*='photos-index-aid-']")
        print(f"  作者カテゴリ数 = {len(cats)} 例: {list(cats)[:5]}")
        print(f"  当ページ漫画リンク数 = {len(manga)}")
        sample_url = None
        if manga:
            href = manga[0].get("href")
            sample_url = href if href.startswith("http") else f"{base}/{href.lstrip('/')}"
        ok = len(cats) > 0 or len(manga) > 0
        mark("T4", ok, f"カテゴリ{len(cats)} / 漫画{len(manga)} / sample={sample_url}")
        return sample_url, cats
    except Exception as e:
        mark("T4", False, f"{type(e).__name__}: {str(e)[:120]}")
        return None, {}


# ---------------------------------------------------------------------------
# T5: 詳細
# ---------------------------------------------------------------------------
def t5_details(session, manga_url):
    print("\n=== T5: 詳細 ===")
    if not manga_url:
        mark("T5", False, "対象漫画 URL なし（T4 失敗）")
        return None
    try:
        r = get(session, manga_url, "詳細ページ")
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.select_one("h2")
        page_el = soup.select_one("p.l_detla")
        gallery = soup.select_one(".gallary_item")
        cover = soup.select_one("img[src*='wnimg']")
        date = None
        if gallery:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", gallery.get_text())
            date = m.group(1) if m else None
        fields = {
            "title": title.get_text(strip=True) if title else None,
            "page_count": page_el.get_text(strip=True) if page_el else None,
            "date": date,
            "cover": cover.get("src") if cover else None,
        }
        got = sum(1 for v in fields.values() if v)
        print(f"  抽出: {fields}")
        mark("T5", got >= 3, f"{got}/4 フィールド取得")
        return soup
    except Exception as e:
        mark("T5", False, f"{type(e).__name__}: {str(e)[:120]}")
        return None


# ---------------------------------------------------------------------------
# T6/T7: 原図 URL の所在 + 実 DL（★最重要）
# ---------------------------------------------------------------------------
def t6_t7_original(session, detail_soup, base):
    print("\n=== T6/T7: 原図 URL の所在 + DL ===")
    if not detail_soup:
        mark("T6", False, "詳細取得失敗のためスキップ")
        mark("T7", False, "スキップ")
        return
    view_links = detail_soup.select("a[href*='photos-view-id-']")
    print(f"  view リンク数（詳細1ページ目） = {len(view_links)}")
    if not view_links:
        mark("T6", False, "view リンクが静的 HTML に存在しない（JS 注入の可能性）")
        mark("T7", False, "スキップ")
        return
    href = view_links[0].get("href")
    view_url = href if href.startswith("http") else f"{base}/{href.lstrip('/')}"
    try:
        r = get(session, view_url, "view ページ")
        vsoup = BeautifulSoup(r.text, "html.parser")
        cands = [i.get("src") for i in vsoup.select("img[src*='wnimg']")]
        orig = [u for u in cands if u and "/data/" in u and "/t/" not in u]
        print(f"  img[wnimg] 候補 = {cands}")
        print(f"  原図判定（/data/ かつ 非 /t/） = {orig}")
        if not orig:
            mark("T6", False, "静的 HTML に原図 URL なし → 原図のみハイブリッド要")
            mark("T7", False, "スキップ")
            return
        mark("T6", True, f"静的 HTML に原図 URL あり: {orig[0][:80]}")
        # T7: 実 DL（1 枚のみ）
        img_url = orig[0] if orig[0].startswith("http") else f"https:{orig[0]}"
        time.sleep(DELAY)
        ir = session.get(img_url, timeout=20)
        ct = ir.headers.get("Content-Type", "")
        size = len(ir.content)
        ok = ir.status_code == 200 and size > 0 and "image" in ct
        mark("T7", ok, f"status={ir.status_code} type={ct} size={size}B")
    except Exception as e:
        mark("T6", False, f"{type(e).__name__}: {str(e)[:120]}")
        mark("T7", False, "例外")


# ---------------------------------------------------------------------------
# T8: 検索
# ---------------------------------------------------------------------------
def t8_search(session, base, cats):
    print("\n=== T8: 検索 ===")
    if not cats:
        mark("T8", False, "作者名なし（T4 失敗）のためスキップ")
        return
    author = next(iter(cats))
    from urllib.parse import quote
    url = f"{base}/q/?q={quote(author)}&f=_all&s=create_time_DESC&syn=yes"
    try:
        r = get(session, url, f"検索: {author}")
        soup = BeautifulSoup(r.text, "html.parser")
        container = soup.select_one("ul.col_2")
        items = container.select("li[class*='cate-']") if container else []
        links = soup.select("a[href*='photos-index-aid-']")
        print(f"  ul.col_2 内 li.cate-* = {len(items)} / 総 aid リンク = {len(links)}")
        mark("T8", len(items) > 0 or len(links) > 0,
             f"検索結果 items={len(items)} links={len(links)}")
    except Exception as e:
        mark("T8", False, f"{type(e).__name__}: {str(e)[:120]}")


# ---------------------------------------------------------------------------
# T9: 収藏フォーム
# ---------------------------------------------------------------------------
def t9_favorite_form(session, base, manga_url):
    print("\n=== T9: 収藏フォーム ===")
    if not manga_url:
        mark("T9", False, "対象漫画 URL なしのためスキップ")
        return
    m = re.search(r"photos-index-aid-(\d+)\.html", manga_url)
    if not m:
        mark("T9", False, "aid 抽出失敗")
        return
    aid = m.group(1)
    url = f"{base}/users-addfav-id-{aid}.html?ajax=true&_t={int(time.time()*1000)}"
    try:
        r = get(session, url, f"addfav aid={aid}")
        soup = BeautifulSoup(r.text, "html.parser")
        sel = soup.select_one("select[name='favc_id']")
        opts = sel.select("option") if sel else []
        names = [(o.get("value"), o.get_text(strip=True)) for o in opts]
        print(f"  favc_id option = {names[:8]}")
        mark("T9", sel is not None and len(opts) > 0,
             f"option 数 = {len(opts)}")
    except Exception as e:
        mark("T9", False, f"{type(e).__name__}: {str(e)[:120]}")


def main():
    env = load_env()
    user = env.get("MANGA_USERNAME", "")
    pwd = env.get("MANGA_PASSWORD", "")
    publish = env.get("PUBLISH_PAGE_URL", "https://wn01.link")
    if not user or not pwd:
        print("認証情報が .env にありません")
        sys.exit(1)
    print(f"ユーザー: {user[:3]}*** / 発布ページ: {publish}")

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    base = t1_resolve_domain(publish)
    if not base:
        summarize()
        return

    logged = t2_login(session, base, user, pwd)
    sample_url, cats = t4_collection(session, base)  # T11: 同一セッション継続
    detail_soup = t5_details(session, sample_url)
    t6_t7_original(session, detail_soup, base)
    t8_search(session, base, cats)
    t9_favorite_form(session, base, sample_url)

    # T11: セッション維持（ここまで未ログインに落ちていないか）
    mark("T11", logged and bool(cats),
         "連続リクエストでセッション維持" if (logged and cats) else "セッション/ログイン不安定")
    summarize()


def summarize():
    print("\n" + "=" * 60)
    print("フェーズ0 結果サマリ")
    print("=" * 60)
    order = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11"]
    for tid in order:
        if tid in results:
            ok, note = results[tid]
            print(f"  {tid}: {'OK ' if ok else 'NG '} {note}")
        else:
            print(f"  {tid}: --  未実行")
    # Go/No-Go 判定
    def ok(t):
        return results.get(t, (False, ""))[0]
    print("-" * 60)
    if ok("T2") and ok("T3") and ok("T6") and ok("T7"):
        print("総合判定: Go（全面移行可能）")
    elif ok("T2") and ok("T3") and not ok("T6"):
        print("総合判定: 部分Go（原図のみハイブリッド／他は requests 移行可）")
    elif not ok("T2") or not ok("T3"):
        print("総合判定: No-Go（ログイン or アンチボットで requests 不成立）")
    else:
        print("総合判定: 要再検証（部分的な失敗あり）")


if __name__ == "__main__":
    main()
