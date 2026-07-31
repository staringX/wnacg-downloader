"""最近更新同期の作者名フィルタの単体テスト

作者判定は 2 段階（タイトルの [ ] ( ) トークン完全一致 → 詳細ページ標籤欄のタグ完全一致）。
"""
import os

import pytest

from app.crawler import parsers
from app.services.recent_updates_service import (
    split_title_tokens,
    tags_match_author,
    title_matches_author,
)

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def test_split_title_tokens():
    title = "(C97) [サークル名 (作者名)] 作品タイトル (原作) [中国翻訳]"
    assert split_title_tokens(title) == [
        "C97", "サークル名", "作者名", "作品タイトル", "原作", "中国翻訳",
    ]


def test_split_title_tokens_fullwidth_and_empty():
    assert split_title_tokens("［作者名］ タイトル（訳者）") == ["作者名", "タイトル", "訳者"]
    assert split_title_tokens("") == []
    assert split_title_tokens(None) == []


@pytest.mark.parametrize("title, author, expected", [
    # サークル名としてヒット
    ("[作者名] タイトル", "作者名", True),
    # 括弧内の作家名としてヒット
    ("(C97) [サークル (作者名)] タイトル", "作者名", True),
    # 前後の空白は無視して一致
    ("[ 作者名 ] タイトル", "作者名", True),
    # 部分一致は別作者として除外
    ("[作者名2] タイトル", "作者名", False),
    ("[別作者] タイトル (作者名っぽい何か)", "作者名", False),
    # 区切り外のタイトル本文に含まれるだけでは不一致
    ("[別作者] 作者名の冒険", "作者名", False),
    # 括弧が無いタイトルは除外
    ("作者名 タイトル", "作者名", False),
    # 空の作者名は常に不一致
    ("[作者名] タイトル", "", False),
])
def test_title_matches_author(title, author, expected):
    assert title_matches_author(title, author) is expected


# --- 標籤欄（詳細ページ）による救済 -----------------------------------------

@pytest.mark.parametrize("tags, author, expected", [
    (["沒有漢化", "無修正", "さわたしゆん"], "さわたしゆん", True),
    ([" さわたしゆん "], "さわたしゆん", True),   # タグ側の空白は無視
    (["さわたしゆん2"], "さわたしゆん", False),  # 部分一致は不可
    (["無修正"], "さわたしゆん", False),
    ([], "さわたしゆん", False),
    (["さわたしゆん"], "", False),
])
def test_tags_match_author(tags, author, expected):
    assert tags_match_author({"tags": tags}, author) is expected


def test_tags_match_author_handles_missing_details():
    # 詳細取得失敗（None）や tags 欠落でも例外にせず不一致を返す
    assert tags_match_author(None, "さわたしゆん") is False
    assert tags_match_author({}, "さわたしゆん") is False
    assert tags_match_author({"tags": None}, "さわたしゆん") is False


def test_tags_from_real_detail_page_rescue_author():
    """実ページ（fixtures/detail.html）：タイトル照合は失敗するが標籤で救済される"""
    with open(os.path.join(FIX, "detail.html"), encoding="utf-8") as f:
        details = parsers.parse_details(f.read())

    author = "さわたしゆん"
    # 標籤欄のみを抽出できている（+TAG や他区画を拾わない）
    assert details["tags"] == ["沒有漢化", "無修正", "さわたしゆん"]
    # このタイトルは [さわたしゆん] を含むためトークン一致もするが、
    # 標籤側だけでも作者を確定できることを確認する
    assert title_matches_author(details["title"], author) is True
    assert tags_match_author(details, author) is True

    # 雜誌掲載作のようにタイトルへ作者名が出ない場合の救済を模す
    assert title_matches_author("これからの夜 (COMIC 快楽天ビースト 2023年9月号)", author) is False
    assert tags_match_author(details, author) is True
