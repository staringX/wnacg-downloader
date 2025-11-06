import os
import requests
import zipfile
from pathlib import Path
from typing import List, Dict, Optional
from app.config import settings
from app.utils.logger import logger

# 可选的PIL导入
try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告: Pillow未安装，某些图片处理功能将不可用")


class MangaDownloader:
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
            print(f"下载图片失败 {url}: {e}")
            return False
    
    def download_manga_stream(self, manga_title: str, images: List[Dict], 
                             author: str = "", resume: bool = True, progress_callback=None):
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
                    print(f"  [{img_index}/{len(images)}] ⏭️  跳过（已存在）: {filename}")
                    
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
                print(f"  [{img_index}/{len(images)}] ⬇️  下载: {filename}")
                
                if self.download_image(img_url, file_path):
                    downloaded_count += 1
                    print(f"  [{img_index}/{len(images)}] ✅ 完成: {filename}")
                    
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
                    print(f"  [{img_index}/{len(images)}] ❌ 失败: {filename}")
                    
                    yield {
                        'index': img_index,
                        'total': len(images),
                        'filename': filename,
                        'status': 'failed',
                        'message': f'下载失败: {filename}'
                    }
            
            # 所有图片下载完成，打包CBZ
            print(f"\n开始打包 CBZ 文件...")
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
                for file_path in downloaded_files:
                    if file_path.is_file():
                        zipf.write(file_path, file_path.name)
            
            print(f"✅ CBZ 文件已创建: {cbz_path}")
            
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
            print(f"🧹 临时目录已清理")
            
        except Exception as e:
            print(f"❌ 下载漫画失败: {e}")
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
