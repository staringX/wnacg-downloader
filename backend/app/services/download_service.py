"""下载业务服务"""
import os
import requests
import zipfile
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Manga
from app.crawler.base import MangaCrawler
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
        下载漫画（生成器版本）- 支持断点续传和实时保存
        
        Args:
            manga_title: 漫画标题
            images: 图片列表 [{'url': ..., 'filename': ..., 'index': ...}]
            author: 作者名称（用于创建分类文件夹）
            resume: 是否断点续传（检查已下载的文件）
            progress_callback: 进度回调函数 callback(downloaded_count, total_count, status_message)
        
        Yields:
            dict: 进度信息 {'index', 'total', 'filename', 'status', 'message'}
        """
        # 清理标题，用于文件名
        safe_title = "".join(c for c in manga_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        
        # 清理作者名，用于文件夹名（处理特殊字符）
        safe_author = "".join(c for c in author if c.isalnum() or c in (' ', '-', '_', '（', '）', '(', ')')).strip()
        safe_author = safe_author.replace(' ', '_') if safe_author else "未知作者"
        
        # 按作者分类创建目录结构：downloads/作者名/漫画标题/
        author_dir = self.download_dir / safe_author
        temp_dir = author_dir / safe_title
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_count = 0
        cover_path = None
        
        try:
            # 边下载边保存，每张图片立即写入磁盘
            for img_info in images:
                img_url = img_info['url']
                filename = img_info['filename']
                img_index = img_info.get('index', 0)
                file_path = temp_dir / filename
                
                # 🔥 断点续传：检查文件是否已存在
                if resume and file_path.exists() and file_path.stat().st_size > 0:
                    downloaded_count += 1
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
                    
                    continue
                
                # 下载图片
                logger.debug(f"  [{img_index}/{len(images)}] ⬇️  下载: {filename}")
                
                if self.download_image(img_url, file_path):
                    downloaded_count += 1
                    logger.debug(f"  [{img_index}/{len(images)}] ✅ 完成: {filename}")
                    
                    yield {
                        'index': img_index,
                        'total': len(images),
                        'filename': filename,
                        'status': 'success',
                        'message': f'下载成功: {filename}',
                        'downloaded_count': downloaded_count
                    }
                    
                    # 第一张图片作为封面
                    if not cover_path:
                        cover_path = self.cover_dir / f"{safe_title}_cover{file_path.suffix}"
                        cover_path.parent.mkdir(parents=True, exist_ok=True)
                        import shutil
                        shutil.copy2(file_path, cover_path)
                    
                    # 调用进度回调
                    if progress_callback:
                        progress_callback(downloaded_count, len(images), f"已下载 {downloaded_count}/{len(images)}")
                else:
                    logger.error(f"  [{img_index}/{len(images)}] ❌ 失败: {filename}")
                    
                    yield {
                        'index': img_index,
                        'total': len(images),
                        'filename': filename,
                        'status': 'failed',
                        'message': f'下载失败: {filename}'
                    }
            
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
                    from app.utils.comic_info import generate_comic_info_xml
                    from datetime import datetime
                    
                    # 准备 ComicInfo.xml 数据
                    comic_info_kwargs = {}
                    
                    # 从 manga_metadata 中提取信息
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
                    
                    comic_info_xml = generate_comic_info_xml(
                        title=manga_title,
                        author=author,
                        page_count=len(images),
                        updated_at=updated_at,
                        manga_url=manga_url,
                        is_manga=True,  # 默认是漫画，从右到左阅读
                        language_iso="zh-CN",  # 默认中文
                        **comic_info_kwargs
                    )
                    
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
                
                # 获取图片列表
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
                
                # 准备元数据（用于 ComicInfo.xml）
                manga_metadata = details if details else {}
                if manga_metadata:
                    # 确保包含 manga_url
                    manga_metadata['manga_url'] = manga.manga_url
                
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

