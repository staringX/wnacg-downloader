"""同步业务服务"""
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Tuple, List, Dict
from datetime import datetime
from app.database import SessionLocal
from app.models import Manga, AppConfig
from app.crawler.base import MangaCrawler
from app.crawler.parsers import extract_aid
from app.config import settings
from app.utils.logger import logger
from app.services.task_manager import TaskManager
from app.services.sync_singleton import sync_singleton


class SyncService:
    """同步业务服务类"""
    
    @staticmethod
    def verify_local_files(db: Session) -> Tuple[int, int, List[str]]:
        """
        验证本地文件与数据库状态的一致性
        检查标记为"已下载"的漫画，其CBZ文件是否真实存在
        
        Returns:
            tuple: (verified_count, fixed_count, missing_files)
        """
        logger.info("=" * 60)
        logger.info("开始验证本地文件完整性...")
        logger.info("=" * 60)
        
        # 查询所有标记为已下载的漫画
        downloaded_mangas = db.query(Manga).filter(
            Manga.is_downloaded == True
        ).all()
        
        if not downloaded_mangas:
            logger.info("没有已下载的漫画需要验证")
            return 0, 0, []
        
        logger.info(f"找到 {len(downloaded_mangas)} 个已下载的漫画记录")
        
        verified_count = 0
        fixed_count = 0
        missing_files = []
        
        for manga in downloaded_mangas:
            cbz_path = manga.cbz_file_path
            cover_path = manga.cover_image_path
            
            cbz_exists = False
            cover_exists = False
            
            # 检查CBZ文件是否存在
            if cbz_path:
                cbz_file = Path(cbz_path)
                cbz_exists = cbz_file.exists() and cbz_file.is_file()
            
            # 检查封面文件是否存在
            if cover_path:
                cover_file = Path(cover_path)
                cover_exists = cover_file.exists() and cover_file.is_file()
            
            # 如果CBZ文件不存在，重置下载状态
            if not cbz_exists:
                logger.warning(f"文件丢失: {manga.title[:50]} - 路径: {cbz_path}")
                
                # 重置下载状态
                manga.is_downloaded = False
                manga.download_status = "not_started"
                manga.downloaded_pages = 0
                manga.cbz_file_path = None
                manga.downloaded_at = None
                manga.file_size = None
                
                # 如果封面也不存在，清除封面路径
                if not cover_exists:
                    manga.cover_image_path = None
                
                fixed_count += 1
                missing_files.append(manga.title)
            else:
                verified_count += 1
                logger.debug(f"验证通过: {manga.title[:50]}")
        
        # 提交所有更改
        if fixed_count > 0:
            db.commit()
            logger.warning(f"已重置 {fixed_count} 个丢失文件的下载状态")
        
        logger.info("=" * 60)
        logger.info(f"验证完成: {verified_count} 个完整, {fixed_count} 个需要重新下载")
        logger.info("=" * 60)
        
        return verified_count, fixed_count, missing_files
    
    @staticmethod
    def scan_and_update_local_files(db: Session) -> Dict[str, int]:
        """
        扫描本地下载目录，更新数据库中的下载状态
        
        功能：
        1. 扫描下载目录中的所有CBZ文件
        2. 根据文件名和作者文件夹匹配数据库中的漫画
        3. 更新数据库中的is_downloaded状态和文件路径
        4. 同时检查数据库标记为已下载但文件不存在的记录，重置其状态
        
        Returns:
            dict: {
                'scanned_files': 扫描到的CBZ文件数量,
                'matched_count': 匹配并更新的漫画数量,
                'marked_downloaded': 新标记为已下载的数量,
                'marked_not_downloaded': 重置为未下载的数量,
                'unmatched_files': 未匹配到数据库记录的文件数量
            }
        """
        logger.info("=" * 60)
        logger.info("开始扫描本地下载文件并更新数据库状态...")
        logger.info("=" * 60)
        
        download_dir = Path(settings.download_dir)
        if not download_dir.exists():
            logger.warning(f"下载目录不存在: {download_dir}")
            return {
                'scanned_files': 0,
                'matched_count': 0,
                'marked_downloaded': 0,
                'marked_not_downloaded': 0,
                'unmatched_files': 0
            }
        
        # 第一步：扫描所有CBZ文件
        cbz_files = []
        for author_dir in download_dir.iterdir():
            if not author_dir.is_dir():
                continue
            
            author_name = author_dir.name
            for cbz_file in author_dir.glob("*.cbz"):
                if cbz_file.is_file():
                    cbz_files.append({
                        'path': str(cbz_file),
                        'author': author_name,
                        'title': cbz_file.stem,  # 文件名（不含扩展名）
                        'file_size': cbz_file.stat().st_size
                    })
        
        logger.info(f"扫描到 {len(cbz_files)} 个CBZ文件")
        
        # 第二步：匹配数据库记录并更新
        # 注意：下载时会对标题和作者进行清理（移除特殊字符，空格替换为下划线）
        # 所以需要将数据库中的原始标题和作者应用相同的清理逻辑来匹配
        
        def normalize_title_for_filename(title: str) -> str:
            """清理标题用于文件名（与下载逻辑一致）"""
            # 移除所有非字母数字字符（除了空格、连字符、下划线）
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            # 将空格替换为下划线
            safe_title = safe_title.replace(' ', '_')
            return safe_title
        
        def normalize_author_for_dirname(author: str) -> str:
            """清理作者名用于文件夹名（与下载逻辑一致）"""
            # 移除所有非字母数字字符（除了空格、连字符、下划线、括号）
            safe_author = "".join(c for c in author if c.isalnum() or c in (' ', '-', '_', '（', '）', '(', ')')).strip()
            # 将空格替换为下划线
            safe_author = safe_author.replace(' ', '_') if safe_author else "未知作者"
            return safe_author
        
        matched_count = 0
        marked_downloaded = 0
        marked_not_downloaded = 0
        unmatched_files = []
        
        # 获取所有漫画记录
        all_mangas = db.query(Manga).all()
        
        # 为每个漫画预计算清理后的标题和作者（用于匹配）
        manga_normalized_map = {}
        for manga in all_mangas:
            normalized_title = normalize_title_for_filename(manga.title)
            normalized_author = normalize_author_for_dirname(manga.author)
            manga_normalized_map[manga.id] = {
                'manga': manga,
                'normalized_title': normalized_title,
                'normalized_author': normalized_author
            }
        
        for cbz_info in cbz_files:
            cbz_path = cbz_info['path']
            cbz_author_dir = cbz_info['author']  # 文件夹名（已清理）
            cbz_title_file = cbz_info['title']  # 文件名（不含扩展名，已清理）
            cbz_file_size = cbz_info['file_size']
            
            # 查找匹配的漫画：将数据库中的标题和作者应用相同的清理逻辑
            matched_manga = None
            for manga_id, normalized_info in manga_normalized_map.items():
                if (normalized_info['normalized_author'] == cbz_author_dir and 
                    normalized_info['normalized_title'] == cbz_title_file):
                    matched_manga = normalized_info['manga']
                    break
            
            if matched_manga:
                matched_count += 1
                
                # 检查是否需要更新
                needs_update = False
                
                if not matched_manga.is_downloaded:
                    needs_update = True
                    marked_downloaded += 1
                    logger.info(f"✓ 标记为已下载: {matched_manga.title[:50]} (作者: {matched_manga.author[:30]})")
                
                if matched_manga.cbz_file_path != cbz_path:
                    needs_update = True
                
                if needs_update:
                    matched_manga.is_downloaded = True
                    matched_manga.download_status = "completed"
                    matched_manga.cbz_file_path = cbz_path
                    matched_manga.file_size = cbz_file_size
                    if not matched_manga.downloaded_at:
                        matched_manga.downloaded_at = datetime.now()
                    matched_manga.downloaded_pages = matched_manga.page_count or 0
            else:
                unmatched_files.append({
                    'path': cbz_path,
                    'author': cbz_author_dir,
                    'title': cbz_title_file
                })
                logger.debug(f"⚠ 未匹配到数据库记录: {cbz_author_dir}/{cbz_title_file}")
        
        # 第三步：检查数据库标记为已下载但文件不存在的记录
        downloaded_mangas = db.query(Manga).filter(Manga.is_downloaded == True).all()
        for manga in downloaded_mangas:
            if manga.cbz_file_path:
                cbz_file = Path(manga.cbz_file_path)
                if not cbz_file.exists() or not cbz_file.is_file():
                    # 文件不存在，重置状态
                    logger.warning(f"✗ 文件不存在，重置状态: {manga.title[:50]} - {manga.cbz_file_path}")
                    manga.is_downloaded = False
                    manga.download_status = "not_started"
                    manga.downloaded_pages = 0
                    manga.cbz_file_path = None
                    manga.downloaded_at = None
                    manga.file_size = None
                    marked_not_downloaded += 1
        
        # 提交所有更改
        if matched_count > 0 or marked_not_downloaded > 0:
            db.commit()
            logger.info(f"已更新 {matched_count} 个匹配记录")
            if marked_downloaded > 0:
                logger.info(f"  其中 {marked_downloaded} 个新标记为已下载")
            if marked_not_downloaded > 0:
                logger.info(f"  重置了 {marked_not_downloaded} 个丢失文件的下载状态")
        
        logger.info("=" * 60)
        logger.info(f"扫描完成: 扫描 {len(cbz_files)} 个文件, 匹配 {matched_count} 个, "
                   f"新标记 {marked_downloaded} 个, 重置 {marked_not_downloaded} 个, "
                   f"未匹配 {len(unmatched_files)} 个")
        logger.info("=" * 60)
        
        return {
            'scanned_files': len(cbz_files),
            'matched_count': matched_count,
            'marked_downloaded': marked_downloaded,
            'marked_not_downloaded': marked_not_downloaded,
            'unmatched_files': len(unmatched_files)
        }
    
    @staticmethod
    def _dedup_and_index_by_aid(db: Session) -> Dict[str, Manga]:
        """既存 Manga を aid で索引化し、同一 aid の重複行を統合する。

        ミラー切替でホストが変わると同一作品が別 URL の新規行として増えていた
        （URL 完全一致の既存判定をすり抜ける）。ここで aid 単位に集約し、情報量の
        多い行（ダウンロード済み > 収藏済み > CBZあり > 直近更新）を1行だけ残して
        残りを削除する。aid を取れない行はグルーピング対象外（従来通り扱う）。

        Returns: {aid: 残した Manga} のマップ。
        """
        groups: Dict[str, List[Manga]] = {}
        for m in db.query(Manga).all():
            aid = extract_aid(m.manga_url)
            if aid:
                groups.setdefault(aid, []).append(m)

        def _completeness(m: Manga):
            return (
                1 if m.is_downloaded else 0,
                1 if m.is_favorited else 0,
                1 if m.cbz_file_path else 0,
                m.updated_at_db or datetime.min,
            )

        index: Dict[str, Manga] = {}
        removed = 0
        for aid, rows in groups.items():
            if len(rows) > 1:
                rows.sort(key=_completeness, reverse=True)
                for dup in rows[1:]:
                    db.delete(dup)
                    removed += 1
            index[aid] = rows[0]

        if removed:
            db.commit()
            logger.warning(f"收藏夹重复清理：合并同一作品(aid)的重复记录，删除 {removed} 条")
        return index

    @staticmethod
    def execute_sync_task(task_id: str, db: Session = None):
        """执行同步任务（后台任务）"""
        if not db:
            db = SessionLocal()
        
        try:
            # 使用单例管理器检查并启动任务
            if not sync_singleton.start_task(task_id):
                TaskManager.update_task(db, task_id, status="failed", error_message="已有同步任务正在运行")
                return
            
            TaskManager.update_task(db, task_id, status="running", message="开始同步收藏夹...")
            
            # 🔍 第一步：验证本地文件完整性
            try:
                verified_count, fixed_count, missing_files = SyncService.verify_local_files(db)
                TaskManager.update_task(db, task_id, message=f"文件验证完成：{verified_count}个完整，{fixed_count}个需要修复")
            except Exception as e:
                logger.warning(f"文件验证失败: {e}")
            
            crawler = MangaCrawler()
            
            try:
                # 登录
                if not crawler.login(settings.manga_username, settings.manga_password):
                    TaskManager.update_task(db, task_id, status="failed", error_message="登录失败")
                    return
                
                TaskManager.update_task(db, task_id, message="登录成功，开始爬取收藏夹...")
                
                added_count = 0
                updated_count = 0
                processed_count = 0

                # 既存 Manga を aid（作品の安定ID）で索引化し、同時に重複行を統合。
                # ミラー切替でホストが変わると同一作品が別 URL の新規行として増えて
                # いたため、ここで aid 単位に集約してから同期する。
                existing_by_aid = SyncService._dedup_and_index_by_aid(db)

                # 生成器：每yield一个漫画，立即处理并保存
                for item in crawler.get_collection_stream():
                    processed_count += 1

                    try:
                        # 既存判定は aid で行う（ホスト非依存）。aid を取れない場合のみ
                        # 従来通り URL 完全一致にフォールバック。
                        aid = extract_aid(item['manga_url'])
                        existing = existing_by_aid.get(aid) if aid else None
                        if existing is None:
                            existing = db.query(Manga).filter(
                                Manga.manga_url == item['manga_url']).first()

                        if existing:
                            # ミラー切替でホストが変わっていたら最新 URL へ更新
                            # （古いホストのままだとダウンロードがデッドリンクになる）
                            if existing.manga_url != item['manga_url']:
                                existing.manga_url = item['manga_url']
                                db.commit()
                            # 已存在，仅更新基本信息（如果需要）
                            if item.get('page_count') and not existing.page_count:
                                existing.page_count = item['page_count']
                                db.commit()
                            # 分類（category）が未取得なら詳情ページから補完（既存収藏のタグ表示用）
                            if not existing.category:
                                try:
                                    details = crawler.get_manga_details(existing.manga_url)
                                    if details:
                                        if details.get('category'):
                                            existing.category = details['category']
                                        if details.get('updated_at') and not existing.updated_at:
                                            existing.updated_at = details['updated_at']
                                        if details.get('cover_image_url') and not existing.cover_image_url:
                                            existing.cover_image_url = details['cover_image_url']
                                        db.commit()
                                except Exception as detail_error:
                                    logger.warning(f"     ⚠ 补全分类失败: {detail_error}")
                            updated_count += 1
                            logger.info(f"[{processed_count}] ⟳ 已存在: {item['title'][:50]}")
                        else:
                            # 新漫画，创建记录并立即保存
                            logger.info(f"[{processed_count}] ✚ 新增: {item['title'][:50]}")
                            
                            try:
                                manga = Manga(
                                    title=item['title'],
                                    author=item['author'],
                                    manga_url=item['manga_url'],
                                    page_count=item.get('page_count')
                                )
                                db.add(manga)
                                db.commit()
                                db.refresh(manga)
                                # 同一 run の後続ページで再登場しても重複追加しないよう索引へ登録
                                if aid:
                                    existing_by_aid[aid] = manga
                            except Exception as e:
                                # 处理可能的唯一约束冲突（并发情况下可能发生）
                                db.rollback()
                                if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                                    logger.warning(f"[{processed_count}] ⚠️  并发冲突，跳过: {item['title'][:50]}")
                                    updated_count += 1
                                    continue
                                else:
                                    raise
                            
                            added_count += 1
                            
                            # 立即获取详细信息
                            try:
                                details = crawler.get_manga_details(manga.manga_url)
                                if details:
                                    if details.get('page_count'):
                                        manga.page_count = details['page_count']
                                    if details.get('updated_at'):
                                        manga.updated_at = details['updated_at']
                                    if details.get('cover_image_url'):
                                        manga.cover_image_url = details['cover_image_url']
                                    if details.get('category'):
                                        manga.category = details['category']
                                    db.commit()
                            except Exception as detail_error:
                                logger.warning(f"     ⚠ 获取详情失败: {detail_error}")
                        
                        # 更新任务进度
                        progress = int((processed_count / max(processed_count, 1)) * 90)  # 90%用于爬取，10%用于完成
                        TaskManager.update_task(
                            db, task_id,
                            progress=progress,
                            completed_items=processed_count,
                            message=f"已处理 {processed_count} 个漫画（新增 {added_count}，更新 {updated_count}）"
                        )
                        
                    except Exception as e:
                        logger.error(f"[{processed_count}] ✗ 处理失败: {item.get('title', 'Unknown')[:50]} - {e}")
                        db.rollback()
                        continue
                
                # 最后更新时刻を記録（画面表示用）
                _record_synced_at(db, "collection")

                # 任务完成
                TaskManager.update_task(
                    db, task_id,
                    status="completed",
                    progress=100,
                    message=f"同步完成：新增 {added_count} 个，更新 {updated_count} 个",
                    result_data=f'{{"added_count": {added_count}, "updated_count": {updated_count}}}'
                )

                logger.info(f"同步任务完成：新增 {added_count} 个，更新 {updated_count} 个")
                
            except Exception as e:
                logger.error(f"同步任务失败: {e}")
                TaskManager.update_task(db, task_id, status="failed", error_message=str(e))
            finally:
                crawler.close()
                # 释放单例锁
                sync_singleton.finish_task(task_id)
        finally:
            if db:
                db.close()


def _record_synced_at(db: Session, which: str):
    """同期完了時刻を AppConfig に記録（which: "collection" | "recent"）。失敗しても本処理は妨げない。"""
    try:
        config = db.query(AppConfig).filter(AppConfig.id == "singleton").first()
        if not config:
            config = AppConfig(id="singleton")
            db.add(config)
        now = datetime.now()
        if which == "collection":
            config.collection_synced_at = now
        else:
            config.recent_synced_at = now
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"记录最后更新时刻失败({which}): {e}")

