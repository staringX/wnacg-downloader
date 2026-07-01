"""タスク間の相互排他ルール（画面更新とダウンロードの同時実行制御）

ルール:
- 内容更新（収藏夹同期／最近更新同期）は、他の同期またはダウンロードが動いている間は開始不可。
- ダウンロードは、同期が動いている間は開始不可。ダウンロード同士は並行可（キュー実行）。
"""
from sqlalchemy.orm import Session

from app.services.sync_singleton import sync_singleton
from app.services.recent_updates_singleton import recent_updates_singleton
from app.services.download_queue import download_queue_manager


def is_any_sync_running() -> bool:
    """収藏夹同期・最近更新同期のいずれかが実行中か"""
    return sync_singleton.is_running() or recent_updates_singleton.is_running()


def has_active_downloads(db: Session) -> bool:
    """ダウンロードが実行中、またはキューに待機中のものがあるか"""
    if download_queue_manager.is_executing():
        return True
    return len(download_queue_manager.get_queue(db)) > 0
