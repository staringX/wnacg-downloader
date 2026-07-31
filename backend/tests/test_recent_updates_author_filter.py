"""最近更新同期の作者名フィルタ（タイトルの [ ] ( ) トークン完全一致）の単体テスト"""
import pytest

from app.services.recent_updates_service import split_title_tokens, title_matches_author


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
