"""pytest 共通設定

app.config の Settings はインポート時に MANGA_USERNAME / MANGA_PASSWORD を必須とする
（未設定だと ValueError）。テストは実認証情報を必要としないため、app.config を
読み込む前にダミー値を環境変数へ注入しておく。実 .env がある場合はそちらが優先される。
"""
import os

os.environ.setdefault("MANGA_USERNAME", "test_user")
os.environ.setdefault("MANGA_PASSWORD", "test_pass")
# テストは実ネットワークを叩かないため、レート制限の sleep を無効化（高速・決定的）
os.environ.setdefault("REQUEST_MIN_INTERVAL", "0")
os.environ.setdefault("IMAGE_REQUEST_MIN_INTERVAL", "0")
