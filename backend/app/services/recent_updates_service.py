"""最近更新业务服务"""
import re
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
from app.database import SessionLocal
from app.models import Manga, RecentUpdate, AppConfig
from app.crawler.base import MangaCrawler
from app.config import settings
from app.utils.logger import logger, get_error_message
from app.services.task_manager import TaskManager
from app.services.recent_updates_singleton import recent_updates_singleton
from app.services.sync_service import _record_synced_at

# 詳細ページの「分類」欄がこれらの文字列を含む作品のみ「漢化」とみなす（簡体・繁体両対応）
HANHUA_MARKERS = ("漢化", "汉化")

# タイトルを作者名候補に切り分ける区切り文字（半角・全角の []（） ）
_TITLE_SPLIT_RE = re.compile(r"[\[\]\(\)［］（）]")


def split_title_tokens(title: str) -> List[str]:
    """タイトルを [ ] ( ) で切り分け、前後の空白を除いた非空トークンを返す

    例: "(C97) [サークル (作者名)] タイトル [中国翻訳]"
        → ["C97", "サークル", "作者名", "タイトル", "中国翻訳"]
    """
    return [t.strip() for t in _TITLE_SPLIT_RE.split(title or "") if t.strip()]


def title_matches_author(title: str, author: str) -> bool:
    """タイトル中の [ ] ( ) 区切りトークンのいずれかが作者名と完全一致するか

    検索は部分一致でヒットするため、同名を含む別作者の作品が混入する。
    トークン完全一致しない作品は「別の作者」とみなし保存対象外にする。
    """
    author = (author or "").strip()
    if not author:
        return False
    return author in split_title_tokens(title)


def tags_match_author(details: dict, author: str) -> bool:
    """詳細ページの「標籤」欄のタグのいずれかが作者名と完全一致するか

    タイトルが `[作者名]` 形式でない作品（雜誌掲載作など）でも、標籤欄には
    作者名タグが付いていることが多い。タイトル照合の救済として使う。
    """
    author = (author or "").strip()
    if not author:
        return False
    return any((t or "").strip() == author for t in (details or {}).get("tags") or [])


def _is_hanhua_details(details: dict) -> bool:
    """詳細ページの「分類」欄に「漢化/汉化」が含まれるか判定"""
    category = (details or {}).get("category") or ""
    return any(marker in category for marker in HANHUA_MARKERS)


class RecentUpdatesService:
    """最近更新业务服务类"""

    @staticmethod
    def execute_sync_recent_updates_task(task_id: str, db: Session = None):
        """执行同步最近更新任务（后台任务）"""
        if not db:
            db = SessionLocal()
        
        try:
            # 使用单例管理器检查并启动任务
            if not recent_updates_singleton.start_task(task_id):
                TaskManager.update_task(db, task_id, status="failed", error_message="已有同步最近更新任务正在运行")
                return
            
            TaskManager.update_task(db, task_id, status="running", message="开始同步最近更新...")

            # 「漢化」のみ取得するか（既定 True。None も True 扱い）
            app_config = db.query(AppConfig).filter(AppConfig.id == "singleton").first()
            hanhua_only = True
            if app_config is not None and app_config.recent_updates_hanhua_only is not None:
                hanhua_only = app_config.recent_updates_hanhua_only
            logger.info(f"最近更新同步：仅「漢化」过滤 = {hanhua_only}")

            # 获取所有已收藏的作者
            authors = db.query(Manga.author).distinct().all()
            author_list = [a[0] for a in authors]
            
            # 排除用户自定义的分类（从配置中读取）
            excluded_categories = settings.excluded_categories
            author_list = [author for author in author_list if author not in excluded_categories]
            
            if not author_list:
                TaskManager.update_task(db, task_id, status="completed", message="没有找到已收藏的作者（已排除自定义分类）", progress=100)
                return
            
            total_authors = len(author_list)
            TaskManager.update_task(db, task_id, total_items=total_authors, message=f"找到 {total_authors} 个已收藏的作者，开始搜索更新...")
            
            # 获取每个作者收藏夹中最新的漫画的更新日期
            author_latest_dates = {}
            for author in author_list:
                latest_manga = db.query(Manga).filter(
                    Manga.author == author
                ).order_by(Manga.updated_at.desc()).first()
                
                if latest_manga and latest_manga.updated_at:
                    author_latest_dates[author] = latest_manga.updated_at
                else:
                    author_latest_dates[author] = datetime(2000, 1, 1)
            
            # 初始化爬虫
            crawler = MangaCrawler()
            if not crawler.login(settings.manga_username, settings.manga_password):
                TaskManager.update_task(db, task_id, status="failed", error_message="登录失败")
                return
            
            total_added = 0
            total_deleted = 0
            processed_authors = 0

            # 对每个作者进行搜索和更新
            for idx, author in enumerate(author_list, 1):
                try:
                    # 収藏夹（Manga）側のこの作者の最新作の更新日。
                    collection_latest = author_latest_dates.get(author, datetime(2000, 1, 1))

                    # ステップ1：最近更新から、収藏夹の最新作より古い作品を削除する。
                    # （収藏夹に追い付いた＝もう「新着」ではない作品の掃除）
                    deleted = db.query(RecentUpdate).filter(
                        RecentUpdate.author == author,
                        RecentUpdate.updated_at < collection_latest,
                    ).delete(synchronize_session=False)
                    if deleted:
                        db.commit()
                        total_deleted += deleted
                        logger.info(f"  作者 {author} 删除了 {deleted} 条早于收藏夹最新作的记录")

                    # ステップ2：クロール打ち切り日 = 最近更新側のこの作者の最新作の
                    # 更新日。ここより新しい作品だけ追加し、古い作品に当たったら打ち切る。
                    # 最近更新が空（初回や全削除後）なら収藏夹の最新作を下限に使う。
                    recent_latest = db.query(func.max(RecentUpdate.updated_at)).filter(
                        RecentUpdate.author == author
                    ).scalar() or datetime(2000, 1, 1)
                    since_date = max(collection_latest, recent_latest)
                    logger.info(
                        f"搜索作者: {author}, 收藏夹最新={collection_latest}, "
                        f"最近更新最新={recent_latest}, 截止日期={since_date}")

                    TaskManager.update_task(
                        db, task_id,
                        completed_items=idx - 1,
                        progress=int((idx - 1) / total_authors * 90),
                        message=f"正在搜索作者 {author} ({idx}/{total_authors})..."
                    )

                    # 搜索作者并获取更新（since_date より新しい作品のみ・古い作品で打ち切り）
                    new_mangas = crawler.search_author_updates(author, since_date)
                    
                    if not new_mangas:
                        logger.info(f"  作者 {author} 没有找到新更新")
                        continue

                    logger.info(f"  作者 {author} 找到 {len(new_mangas)} 个新更新")

                    # 作者名フィルタ＋「漢化」フィルタ。
                    # 作者判定は 2 段階：
                    #   1. タイトルを [ ] ( ) で切り分けたトークンの完全一致（ページ取得なし）
                    #   2. 不一致なら詳細ページの「標籤」欄のタグと完全一致するか
                    # どちらにも一致しなければ「別の作者」として除外する。
                    # 詳細ページは 1 作品につき 1 回だけ取得し、漢化判定と共用する。
                    before = len(new_mangas)
                    kept = []
                    skipped_author = 0
                    skipped_hanhua = 0
                    for md in new_mangas:
                        title = md.get("title", "Unknown")
                        title_ok = title_matches_author(md.get("title", ""), author)

                        # 詳細ページが要るのは「タイトル不一致の救済」か「漢化判定」のとき
                        details = None
                        if not title_ok or hanhua_only:
                            try:
                                details = crawler.get_manga_details(md["manga_url"])
                            except Exception as e:
                                logger.warning(
                                    f"    详情获取失败，跳过: {title[:40]} - {get_error_message(e)}")
                                continue
                            if details is None:
                                logger.warning(f"    详情获取失败，跳过: {title[:40]}")
                                continue

                        if not title_ok:
                            if tags_match_author(details, author):
                                logger.info(f"    标签命中作者名，保留: {title[:60]}")
                            else:
                                logger.info(f"    作者名不一致（标题・标签均无），跳过: {title[:60]}")
                                skipped_author += 1
                                continue

                        if hanhua_only and not _is_hanhua_details(details):
                            skipped_hanhua += 1
                            continue

                        kept.append(md)

                    new_mangas = kept
                    logger.info(
                        f"  作者 {author} 过滤: {before} → {len(new_mangas)}"
                        f"（作者名不一致 {skipped_author} 件 / 非漢化 {skipped_hanhua} 件）")
                    if not new_mangas:
                        continue

                    # 保存新更新到数据库
                    for manga_data in new_mangas:
                        # 检查是否已存在（通过manga_url）
                        existing = db.query(RecentUpdate).filter(
                            RecentUpdate.manga_url == manga_data['manga_url']
                        ).first()
                        
                        if existing:
                            # 更新现有记录
                            existing.title = manga_data['title']
                            existing.updated_at = manga_data['updated_at']
                            existing.page_count = manga_data.get('page_count')
                            existing.cover_image_url = manga_data.get('cover_image_url')
                            total_added += 1
                        else:
                            # 创建新记录
                            try:
                                new_update = RecentUpdate(
                                    title=manga_data['title'],
                                    author=manga_data['author'],
                                    manga_url=manga_data['manga_url'],
                                    updated_at=manga_data['updated_at'],
                                    page_count=manga_data.get('page_count'),
                                    cover_image_url=manga_data.get('cover_image_url'),
                                    is_downloaded=False
                                )
                                db.add(new_update)
                                total_added += 1
                            except Exception as e:
                                # 处理可能的唯一约束冲突（并发情况下可能发生）
                                db.rollback()
                                if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                                    logger.warning(f"  并发冲突，跳过: {manga_data.get('title', 'Unknown')[:50]}")
                                    continue
                                else:
                                    raise
                    
                    db.commit()

                    processed_authors += 1
                    
                except Exception as e:
                    logger.error(f"处理作者 {author} 时出错: {get_error_message(e)}")
                    db.rollback()
                    continue
            
            crawler.close()

            # 最后更新时刻を記録（画面表示用）
            _record_synced_at(db, "recent")

            # 任务完成
            TaskManager.update_task(
                db, task_id,
                status="completed",
                progress=100,
                completed_items=total_authors,
                message=f"同步完成: 新增/更新 {total_added} 条，删除 {total_deleted} 条",
                result_data=f'{{"added_count": {total_added}, "deleted_count": {total_deleted}}}'
            )
            
            logger.info(f"同步最近更新任务完成: 新增/更新 {total_added} 条，删除 {total_deleted} 条")
            
        except Exception as e:
            logger.error(f"同步最近更新任务失败: {get_error_message(e)}")
            TaskManager.update_task(db, task_id, status="failed", error_message=get_error_message(e))
        finally:
            # 释放单例锁
            recent_updates_singleton.finish_task(task_id)
            if db:
                db.close()

