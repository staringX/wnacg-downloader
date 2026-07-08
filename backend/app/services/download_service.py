"""下载业务服务"""
import os
import requests
import zipfile
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Manga
from app.crawler.base import MangaCrawler
from app.crawler.rate_limiter import image_limiter
from app.config import settings
from app.utils.logger import logger, get_error_message
from app.services.task_manager import TaskManager
from app.services.download_queue import download_queue_manager

# 可选的PIL导入
try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def sanitize_title(title: str) -> str:
    """清理标题用于文件名（一括下载和逐页下载共用）"""
    safe = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    return safe.replace(' ', '_')


def sanitize_author(author: str) -> str:
    """清理作者名用于文件夹名（处理特殊字符）"""
    safe = "".join(c for c in author if c.isalnum() or c in (' ', '-', '_', '（', '）', '(', ')')).strip()
    return safe.replace(' ', '_') if safe else "未知作者"


def build_comic_info_xml(manga_title: str, author: str, page_count: int,
                         manga_metadata: Optional[Dict] = None) -> str:
    """从漫画元数据生成 ComicInfo.xml 内容（一括下载和逐页下载共用）"""
    from app.utils.comic_info import generate_comic_info_xml

    comic_info_kwargs = {}
    updated_at = datetime.now()
    manga_url = None
    tags_list = []

    if manga_metadata:
        # 更新日期
        if manga_metadata.get('updated_at'):
            updated_at = manga_metadata['updated_at']

        # 漫画URL
        if manga_metadata.get('manga_url'):
            manga_url = manga_metadata['manga_url']

        # 标签
        if manga_metadata.get('tags'):
            tags_list = manga_metadata['tags']
            if isinstance(tags_list, list):
                comic_info_kwargs['tags'] = ', '.join(tags_list)

        # 分类/流派
        if manga_metadata.get('category'):
            category = manga_metadata['category']
            # 尝试从分类中提取流派信息
            if '雜誌' in category or '杂志' in category:
                comic_info_kwargs['genre'] = '杂志'
            elif '同人' in category:
                comic_info_kwargs['genre'] = '同人'
            elif '單行本' in category or '单行本' in category:
                comic_info_kwargs['genre'] = '单行本'

        # 简介
        if manga_metadata.get('summary'):
            comic_info_kwargs['summary'] = manga_metadata['summary']

        # 上传者作为译者或编辑
        if manga_metadata.get('uploader'):
            # 如果标签中有"中文翻譯"，则上传者可能是译者
            if tags_list and any('翻譯' in tag or '翻译' in tag for tag in tags_list):
                comic_info_kwargs['translator'] = manga_metadata['uploader']
            else:
                comic_info_kwargs['editor'] = manga_metadata['uploader']

    return generate_comic_info_xml(
        title=manga_title,
        author=author,
        page_count=page_count,
        updated_at=updated_at,
        manga_url=manga_url,
        is_manga=True,  # 默认是漫画，从右到左阅读
        language_iso="zh-CN",  # 默认中文
        **comic_info_kwargs
    )


class MangaDownloader:
    """漫画下载器（从utils移入）"""
    
    def __init__(self):
        self.download_dir = Path(settings.download_dir)
        self.cover_dir = Path(settings.cover_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.cover_dir.mkdir(parents=True, exist_ok=True)
    
    def download_image(self, url: str, save_path: Path) -> bool:
        """下载单张图片"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            image_limiter.acquire()  # CDN 负载配慮: 最小间隔を空ける
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 确保目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存图片
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            logger.error(f"下载图片失败 {url}: {e}")
            return False
    
    def download_manga_stream(self, manga_title: str, images: List[Dict], 
                             author: str = "", resume: bool = True, progress_callback=None,
                             manga_metadata: Optional[Dict] = None):
        """
        下载漫画（生成器版本）- 支持断点续传和多线程并发下载
        
        Args:
            manga_title: 漫画标题
            images: 图片列表 [{'url': ..., 'filename': ..., 'index': ...}]
            author: 作者名称（用于创建分类文件夹）
            resume: 是否断点续传（检查已下载的文件）
            progress_callback: 进度回调函数 callback(downloaded_count, total_count, status_message)
        
        Yields:
            dict: 进度信息 {'index', 'total', 'filename', 'status', 'message'}
        """
        # 清理标题/作者名，用于文件名（与一括下载共用）
        safe_title = sanitize_title(manga_title)
        safe_author = sanitize_author(author)
        
        # 按作者分类创建目录结构：downloads/作者名/漫画标题/
        author_dir = self.download_dir / safe_author
        temp_dir = author_dir / safe_title
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 用于线程安全的计数器
        downloaded_count = 0
        download_lock = threading.Lock()
        cover_path = None
        cover_lock = threading.Lock()
        
        try:
            # 第一步：处理断点续传，收集需要下载的图片
            download_tasks = []  # 需要下载的任务列表
            skipped_count = 0
            
            for img_info in images:
                img_url = img_info['url']
                filename = img_info['filename']
                img_index = img_info.get('index', 0)
                file_path = temp_dir / filename
                
                # 🔥 断点续传：检查文件是否已存在
                if resume and file_path.exists() and file_path.stat().st_size > 0:
                    skipped_count += 1
                    logger.debug(f"  [{img_index}/{len(images)}] ⏭️  跳过（已存在）: {filename}")
                    
                    yield {
                        'index': img_index,
                        'total': len(images),
                        'filename': filename,
                        'status': 'skipped',
                        'message': f'跳过已下载: {filename}'
                    }
                    
                    # 第一张图片作为封面
                    if not cover_path:
                        cover_path = self.cover_dir / f"{safe_title}_cover{file_path.suffix}"
                        cover_path.parent.mkdir(parents=True, exist_ok=True)
                        import shutil
                        if not cover_path.exists():
                            shutil.copy2(file_path, cover_path)
                else:
                    # 需要下载的图片加入任务列表
                    download_tasks.append((img_info, file_path))
            
            # 如果所有图片都已存在，直接跳到打包
            if not download_tasks:
                downloaded_count = skipped_count
                logger.info(f"所有图片已存在，跳过下载步骤")
            else:
                # 第二步：使用多线程并发下载
                thread_count = settings.download_threads
                logger.info(f"开始使用 {thread_count} 个线程并发下载 {len(download_tasks)} 张图片...")
                
                # 用于跟踪新下载成功的数量（不包括跳过的）
                new_downloaded_count = 0
                
                def download_single_image(img_info, file_path):
                    """下载单张图片的线程函数"""
                    nonlocal new_downloaded_count
                    img_url = img_info['url']
                    filename = img_info['filename']
                    img_index = img_info.get('index', 0)
                    
                    logger.debug(f"  [{img_index}/{len(images)}] ⬇️  下载: {filename}")
                    
                    success = self.download_image(img_url, file_path)
                    
                    if success:
                        with download_lock:
                            new_downloaded_count += 1
                            current_count = new_downloaded_count + skipped_count
                        
                        logger.debug(f"  [{img_index}/{len(images)}] ✅ 完成: {filename}")
                        
                        # 第一张成功下载的图片作为封面
                        with cover_lock:
                            nonlocal cover_path
                            if not cover_path:
                                cover_path = self.cover_dir / f"{safe_title}_cover{file_path.suffix}"
                                cover_path.parent.mkdir(parents=True, exist_ok=True)
                                import shutil
                                shutil.copy2(file_path, cover_path)
                        
                        return {
                            'index': img_index,
                            'total': len(images),
                            'filename': filename,
                            'status': 'success',
                            'message': f'下载成功: {filename}',
                            'downloaded_count': current_count
                        }
                    else:
                        logger.error(f"  [{img_index}/{len(images)}] ❌ 失败: {filename}")
                        return {
                            'index': img_index,
                            'total': len(images),
                            'filename': filename,
                            'status': 'failed',
                            'message': f'下载失败: {filename}'
                        }
                
                # 使用线程池并发下载
                # 注意：with 块会确保所有任务完成后再继续
                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    # 提交所有下载任务
                    future_to_task = {
                        executor.submit(download_single_image, img_info, file_path): img_info
                        for img_info, file_path in download_tasks
                    }
                    
                    # 等待所有任务完成，并实时yield进度
                    for future in as_completed(future_to_task):
                        try:
                            result = future.result()
                            yield result
                            
                            # 调用进度回调
                            if progress_callback and result.get('status') == 'success':
                                total_downloaded = result.get('downloaded_count', 0)
                                progress_callback(total_downloaded, len(images), f"已下载 {total_downloaded}/{len(images)}")
                        except Exception as e:
                            logger.error(f"下载任务异常: {e}")
                            img_info = future_to_task[future]
                            yield {
                                'index': img_info.get('index', 0),
                                'total': len(images),
                                'filename': img_info.get('filename', ''),
                                'status': 'failed',
                                'message': f'下载异常: {str(e)}'
                            }
                
                # 更新最终下载计数（包括跳过的）
                downloaded_count = new_downloaded_count + skipped_count
                logger.info(f"✅ 所有图片下载完成，共 {downloaded_count}/{len(images)} 张（新下载: {new_downloaded_count}，跳过: {skipped_count}）")
            
            # 所有图片下载完成，打包CBZ
            logger.info(f"开始打包 CBZ 文件...")
            # CBZ文件保存在作者文件夹下
            cbz_path = author_dir / f"{safe_title}.cbz"
            
            # 获取所有已下载的文件（按文件名排序）
            downloaded_files = sorted(temp_dir.glob("*"))
            
            if not downloaded_files:
                yield {
                    'status': 'error',
                    'message': '没有可打包的文件'
                }
                return
            
            # 创建CBZ文件
            with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加所有图片文件
                for file_path in downloaded_files:
                    if file_path.is_file():
                        zipf.write(file_path, file_path.name)
                
                # 添加 ComicInfo.xml 文件
                try:
                    comic_info_xml = build_comic_info_xml(
                        manga_title, author, len(images), manga_metadata)
                    # 将 XML 内容写入 ZIP
                    zipf.writestr("ComicInfo.xml", comic_info_xml.encode('utf-8'))
                    logger.info(f"✅ ComicInfo.xml 已添加到 CBZ 文件")
                except Exception as e:
                    logger.warning(f"⚠️  添加 ComicInfo.xml 失败: {get_error_message(e)}")
                    # 即使失败也继续创建 CBZ
            
            logger.info(f"✅ CBZ 文件已创建: {cbz_path}")
            
            # 获取文件大小
            file_size = cbz_path.stat().st_size
            
            yield {
                'status': 'completed',
                'message': '打包完成',
                'cbz_path': str(cbz_path),
                'cover_path': str(cover_path) if cover_path else None,
                'file_size': file_size,
                'downloaded_count': downloaded_count
            }
            
            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir)
            logger.debug(f"🧹 临时目录已清理")
            
        except Exception as e:
            logger.error(f"❌ 下载漫画失败: {e}")
            yield {
                'status': 'error',
                'message': f'下载失败: {str(e)}'
            }
    
    def convert_zip_to_cbz(self, zip_path, manga_title: str, author: str = "",
                           manga_metadata: Optional[Dict] = None) -> Optional[Dict]:
        """将一括下载的 ZIP 转换为 CBZ（追加 ComicInfo.xml + 提取封面，不重新压缩）

        ZIP 内容为扁平的连番图片（001.jpg...，2026-07 实站验证）。
        追加 ComicInfo.xml 后原地改名为 downloads/{作者}/{标题}.cbz。

        返回: {'cbz_path', 'cover_path', 'file_size', 'page_count'}，失败返回 None。
        """
        from app.crawler.archive_download import zip_image_names

        zip_path = Path(zip_path)
        image_names = zip_image_names(zip_path)
        if not image_names:
            logger.error(f"ZIP 中没有图片，无法转换为 CBZ: {zip_path}")
            return None
        page_count = len(image_names)

        safe_title = sanitize_title(manga_title)
        safe_author = sanitize_author(author)
        author_dir = self.download_dir / safe_author
        author_dir.mkdir(parents=True, exist_ok=True)

        # 提取第一张图片作为封面（沿用现有封面命名规则）
        cover_path = None
        try:
            first = image_names[0]
            suffix = Path(first).suffix or ".jpg"
            cover_path = self.cover_dir / f"{safe_title}_cover{suffix}"
            cover_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path) as zf:
                cover_path.write_bytes(zf.read(first))
        except Exception as e:
            logger.warning(f"⚠️  提取封面失败: {get_error_message(e)}")
            cover_path = None

        # 追加 ComicInfo.xml（append 模式，避免重新压缩大文件）
        try:
            comic_info_xml = build_comic_info_xml(
                manga_title, author, page_count, manga_metadata)
            with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zf:
                if "ComicInfo.xml" not in zf.namelist():
                    zf.writestr("ComicInfo.xml", comic_info_xml.encode('utf-8'))
            logger.info(f"✅ ComicInfo.xml 已添加到 CBZ 文件")
        except Exception as e:
            logger.warning(f"⚠️  添加 ComicInfo.xml 失败: {get_error_message(e)}")
            # 即使失败也继续创建 CBZ

        cbz_path = author_dir / f"{safe_title}.cbz"
        zip_path.replace(cbz_path)
        logger.info(f"✅ CBZ 文件已创建: {cbz_path}")
        return {
            'cbz_path': str(cbz_path),
            'cover_path': str(cover_path) if cover_path else None,
            'file_size': cbz_path.stat().st_size,
            'page_count': page_count,
        }

    def download_manga(self, manga_title: str, images: List[Dict], author: str = "") -> tuple[Optional[str], Optional[str]]:
        """
        下载漫画并打包为CBZ（兼容旧版本）
        返回: (cbz_file_path, cover_image_path)
        """
        cbz_path = None
        cover_path = None
        
        # 使用生成器版本
        for progress in self.download_manga_stream(manga_title, images, author=author, resume=False):
            if progress.get('status') == 'completed':
                cbz_path = progress.get('cbz_path')
                cover_path = progress.get('cover_path')
        
        return cbz_path, cover_path
    
    def get_file_size(self, file_path: str) -> int:
        """获取文件大小（字节）"""
        try:
            return os.path.getsize(file_path)
        except:
            return 0


class DownloadService:
    """下载业务服务类"""
    
    @staticmethod
    def download_executor(db: Session = None):
        """下载执行器 - 从队列中取出任务执行（单例模式）"""
        if not db:
            db = SessionLocal()
        
        try:
            # 检查执行器是否已经在运行
            if download_queue_manager.is_executing():
                logger.debug("下载执行器已在运行，跳过")
                return
            
            # 循环处理队列中的任务
            while True:
                # 获取队列中的下一个任务
                next_task = download_queue_manager.get_next_task(db)
                
                if not next_task:
                    # 队列为空，退出
                    logger.info("下载队列为空，执行器退出")
                    break
                
                # 尝试启动执行
                if not download_queue_manager.start_execution(next_task.id):
                    # 执行器已被其他线程启动，退出
                    logger.debug("执行器已被其他线程启动，退出")
                    break
                
                try:
                    # 执行下载任务
                    DownloadService.execute_download_task(next_task.id, next_task.manga_id, db)
                finally:
                    # 释放执行器锁
                    download_queue_manager.finish_execution(next_task.id)
                    
                    # 短暂休眠，避免CPU占用过高
                    time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"下载执行器错误: {e}")
        finally:
            if db:
                db.close()
    
    @staticmethod
    def execute_download_task(task_id: str, manga_id: str, db: Session = None):
        """执行下载任务（后台任务）"""
        if not db:
            db = SessionLocal()
        
        try:
            # 更新任务状态为running
            TaskManager.update_task(db, task_id, status="running", message=f"开始下载...")
            
            manga = db.query(Manga).filter(Manga.id == manga_id).first()
            if not manga:
                TaskManager.update_task(db, task_id, status="failed", error_message="漫画不存在")
                return
            
            # 检查是否已完全下载
            if manga.download_status == "completed" and manga.is_downloaded:
                TaskManager.update_task(
                    db, task_id,
                    status="completed",
                    progress=100,
                    message="漫画已下载",
                    result_data=f'{{"file_path": "{manga.cbz_file_path}"}}'
                )
                return
            
            TaskManager.update_task(db, task_id, message=f"开始下载: {manga.title}")
            
            crawler = MangaCrawler()
            downloader = MangaDownloader()
            
            try:
                # 登录
                if not crawler.login(settings.manga_username, settings.manga_password):
                    TaskManager.update_task(db, task_id, status="failed", error_message="登录失败")
                    return
                
                # 标记为下载中
                manga.download_status = "downloading"
                manga.downloaded_pages = manga.downloaded_pages or 0
                db.commit()
                
                # 获取漫画详情
                details = None
                if not manga.page_count or not manga.cover_image_url:
                    TaskManager.update_task(db, task_id, message="获取漫画详情...")
                    details = crawler.get_manga_details(manga.manga_url)
                    if details:
                        if details.get('page_count'):
                            manga.page_count = details['page_count']
                        if details.get('updated_at'):
                            manga.updated_at = details['updated_at']
                        if details.get('cover_image_url'):
                            manga.cover_image_url = details['cover_image_url']
                        db.commit()
                else:
                    # 即使已有基本信息，也获取完整详情以用于 ComicInfo.xml
                    TaskManager.update_task(db, task_id, message="获取漫画详情...")
                    details = crawler.get_manga_details(manga.manga_url)
                
                # 准备元数据（用于 ComicInfo.xml，一括/逐页两种方式共用）
                manga_metadata = details if details else {}
                manga_metadata['manga_url'] = manga.manga_url

                # 主经路：一括ZIP下载（2026-07 站点改版新增的「下載漫畫」按钮）
                if settings.archive_download_enabled:
                    if DownloadService._try_archive_download(
                            db, task_id, manga, crawler, downloader, manga_metadata):
                        return
                    # 全部线路失败 → 回退到传统的逐页下载（救济措施）
                    logger.warning(f"一括下载失败，回退到逐页下载: {manga.title}")
                    TaskManager.update_task(
                        db, task_id, message="一括下载失败，改用逐页下载...")

                # 救济经路：获取图片列表（逐页下载）
                TaskManager.update_task(db, task_id, message="获取图片列表...")
                images = crawler.get_manga_images(manga.manga_url)

                if not images:
                    manga.download_status = "failed"
                    db.commit()
                    TaskManager.update_task(db, task_id, status="failed", error_message="无法获取图片列表")
                    return

                total_images = len(images)
                TaskManager.update_task(
                    db, task_id,
                    total_items=total_images,
                    message=f"开始下载 {total_images} 张图片..."
                )

                cbz_path = None
                cover_path = None

                for progress in downloader.download_manga_stream(
                    manga.title, images, 
                    author=manga.author, 
                    resume=True,
                    manga_metadata=manga_metadata
                ):
                    status = progress.get('status')
                    
                    # 更新下载进度
                    if 'downloaded_count' in progress:
                        downloaded_count = progress['downloaded_count']
                        manga.downloaded_pages = downloaded_count
                        db.commit()
                        
                        # 更新任务进度
                        progress_percent = int((downloaded_count / total_images) * 90)  # 90%用于下载，10%用于打包
                        TaskManager.update_task(
                            db, task_id,
                            progress=progress_percent,
                            completed_items=downloaded_count,
                            message=f"已下载 {downloaded_count}/{total_images} 张图片"
                        )
                    
                    # 下载完成
                    if status == 'completed':
                        cbz_path = progress.get('cbz_path')
                        cover_path = progress.get('cover_path')
                        file_size = progress.get('file_size', 0)
                        
                        # 更新数据库
                        manga.is_downloaded = True
                        manga.download_status = "completed"
                        manga.downloaded_at = datetime.now()
                        manga.cbz_file_path = cbz_path
                        manga.cover_image_path = cover_path
                        manga.file_size = file_size
                        manga.downloaded_pages = total_images
                        db.commit()
                        
                        TaskManager.update_task(
                            db, task_id,
                            status="completed",
                            progress=100,
                            message=f"下载完成: {manga.title}",
                            result_data=f'{{"file_path": "{cbz_path}", "file_size": {file_size}}}'
                        )
                        
                        logger.info(f"✅ 下载完成: {manga.title}")
                    
                    # 下载失败
                    elif status == 'error':
                        manga.download_status = "failed"
                        db.commit()
                        TaskManager.update_task(
                            db, task_id,
                            status="failed",
                            error_message=progress.get('message', '下载失败')
                        )
                        return
                
                if not cbz_path:
                    manga.download_status = "failed"
                    db.commit()
                    TaskManager.update_task(db, task_id, status="failed", error_message="下载失败")
                    
            except Exception as e:
                logger.error(f"下载任务失败: {e}")
                manga.download_status = "failed"
                db.commit()
                TaskManager.update_task(db, task_id, status="failed", error_message=str(e))
            finally:
                crawler.close()
        finally:
            if db:
                db.close()

    @staticmethod
    def _try_archive_download(db: Session, task_id: str, manga: Manga,
                              crawler: MangaCrawler, downloader: MangaDownloader,
                              manga_metadata: Dict) -> bool:
        """尝试一括ZIP下载（主经路）。成功返回 True，失败返回 False（回退逐页下载）

        流程: 解析下载页线路 → 按顺序下载 ZIP（失败切换线路）→ 转换为 CBZ。
        进度: 0-90% 按字节数，90-100% 为转换阶段。
        """
        try:
            routes = crawler.get_download_routes(manga.manga_url)
            if not routes:
                logger.info(f"未检测到一括下载线路: {manga.manga_url}")
                return False

            TaskManager.update_task(
                db, task_id, message=f"检测到 {len(routes)} 条一括下载线路，开始下载...")

            safe_title = sanitize_title(manga.title)
            safe_author = sanitize_author(manga.author)
            zip_part = downloader.download_dir / safe_author / f"{safe_title}.zip.part"

            # 进度回调（按字节数更新 task，节流为每 2% 一次，避免频繁写 DB）
            last_percent = {'value': -1}

            def progress_cb(done: int, total: int):
                percent = int(done / total * 90) if total else 0
                if percent - last_percent['value'] >= 2:
                    last_percent['value'] = percent
                    total_mb = f"{total / 1048576:.1f}MB" if total else "?"
                    TaskManager.update_task(
                        db, task_id, progress=percent,
                        message=f"一括下载中 {done / 1048576:.1f}MB/{total_mb}")

            if not crawler.download_archive(routes, zip_part, progress_cb):
                return False

            TaskManager.update_task(db, task_id, progress=92, message="转换为 CBZ...")
            result = downloader.convert_zip_to_cbz(
                zip_part, manga.title, manga.author, manga_metadata)
            if not result:
                zip_part.unlink(missing_ok=True)
                return False

            # 更新数据库（与逐页下载完成时相同的字段）
            manga.is_downloaded = True
            manga.download_status = "completed"
            manga.downloaded_at = datetime.now()
            manga.cbz_file_path = result['cbz_path']
            manga.cover_image_path = result['cover_path']
            manga.file_size = result['file_size']
            manga.page_count = result['page_count']
            manga.downloaded_pages = result['page_count']
            db.commit()

            TaskManager.update_task(
                db, task_id,
                status="completed",
                progress=100,
                total_items=result['page_count'],
                completed_items=result['page_count'],
                message=f"下载完成: {manga.title}",
                result_data=f'{{"file_path": "{result["cbz_path"]}", "file_size": {result["file_size"]}}}'
            )
            logger.info(f"✅ 一括下载完成: {manga.title}")
            return True
        except Exception as e:
            logger.warning(f"一括下载出现异常: {get_error_message(e)}")
            return False

