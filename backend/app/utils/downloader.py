import os
import requests
import zipfile
from pathlib import Path
from typing import List, Dict
from PIL import Image
from io import BytesIO
from app.config import settings


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
    
    def download_manga(self, manga_title: str, images: List[Dict]) -> tuple[Optional[str], Optional[str]]:
        """
        下载漫画并打包为CBZ
        返回: (cbz_file_path, cover_image_path)
        """
        # 清理标题，用于文件名
        safe_title = "".join(c for c in manga_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        
        # 创建临时目录
        temp_dir = self.download_dir / safe_title
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 下载所有图片
            downloaded_files = []
            cover_path = None
            
            for img_info in images:
                img_url = img_info['url']
                filename = img_info['filename']
                file_path = temp_dir / filename
                
                if self.download_image(img_url, file_path):
                    downloaded_files.append(file_path)
                    
                    # 第一张图片作为封面
                    if not cover_path:
                        cover_path = self.cover_dir / f"{safe_title}_cover.{file_path.suffix}"
                        cover_path.parent.mkdir(parents=True, exist_ok=True)
                        import shutil
                        shutil.copy2(file_path, cover_path)
            
            if not downloaded_files:
                return None, None
            
            # 创建CBZ文件
            cbz_path = self.download_dir / f"{safe_title}.cbz"
            with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in downloaded_files:
                    zipf.write(file_path, file_path.name)
            
            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir)
            
            return str(cbz_path), str(cover_path) if cover_path else None
            
        except Exception as e:
            print(f"下载漫画失败: {e}")
            # 清理临时目录
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
            return None, None
    
    def get_file_size(self, file_path: str) -> int:
        """获取文件大小（字节）"""
        try:
            return os.path.getsize(file_path)
        except:
            return 0
