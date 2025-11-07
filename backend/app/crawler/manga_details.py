"""漫画详情和图片获取模块"""
import time
import re
from typing import List, Optional, Dict
from datetime import datetime
from selenium.webdriver.common.by import By
from app.utils.logger import logger


class MangaDetailsCrawler:
    """漫画详情爬取器 - 负责获取漫画详情和图片列表"""
    
    def __init__(self, browser_manager):
        self.browser = browser_manager
        self.driver = browser_manager.driver
    
    @property
    def base_url(self):
        """动态获取base_url，确保获取到最新值"""
        return self.browser.base_url
    
    def get_manga_details(self, manga_url: str) -> Optional[Dict]:
        """获取漫画详情（页数、更新日期、封面等）"""
        if not self.driver:
            return None
        
        try:
            self.driver.get(manga_url)
            time.sleep(3)
            
            # 获取标题
            title = None
            try:
                title_elem = self.driver.find_element(By.CSS_SELECTOR, "h2")
                title = title_elem.text.strip()
            except:
                pass
            
            # 获取页数（使用class名称，避免汉字字符串）
            page_count = None
            try:
                # 使用 p.l_detla class 查找页数信息
                page_elem = self.driver.find_element(By.CSS_SELECTOR, "p.l_detla")
                page_text = page_elem.text  # 例如: "頁數：20P"
                # 从文本中提取数字（格式：頁數：20 或 頁數：20P）
                page_match = re.search(r'(\d+)\s*P?', page_text)
                if page_match:
                    page_count = int(page_match.group(1))
            except Exception as e:
                logger.debug(f"    获取页数失败: {e}")
            
            # 获取上传日期（使用class名称，避免汉字字符串）
            updated_at = None
            try:
                # 查找图片列表项（使用 .gallary_item class）
                gallery_items = self.driver.find_elements(By.CSS_SELECTOR, ".gallary_item")
                if gallery_items:
                    # 从第一个图片项中提取日期（格式：YYYY-MM-DD）
                    first_item_text = gallery_items[0].text
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', first_item_text)
                    if date_match:
                        date_str = date_match.group(1)
                        updated_at = datetime.strptime(date_str, '%Y-%m-%d')
            except Exception as e:
                logger.debug(f"    获取上传日期失败: {e}")
            
            # 获取封面图片URL - 取第一张图片的缩略图
            cover_url = None
            try:
                # 查找所有图片，通常第一张是封面
                images = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='wnimg']")
                if images:
                    cover_url = images[0].get_attribute('src')
            except Exception as e:
                logger.debug(f"    获取封面失败: {e}")
            
            return {
                'title': title,
                'manga_url': manga_url,
                'page_count': page_count,
                'updated_at': updated_at,
                'cover_image_url': cover_url
            }
        except Exception as e:
            logger.error(f"获取漫画详情失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_manga_images(self, manga_url: str) -> List[Dict]:
        """获取漫画的所有图片URL，按显示顺序
        
        流程：
        1. 遍历漫画详情页的所有分页，收集所有图片查看链接 (photos-view-id-xxxxx.html)
        2. 逐个访问这些链接，从每个页面提取原图 URL
        3. 不使用"下拉阅读"，因为它是懒加载，大漫画会导致部分图片未加载
        """
        if not self.driver:
            return []
        
        try:
            logger.info(f"\n开始获取漫画图片: {manga_url}")
            
            # 第一步：收集所有图片查看链接
            # 重要：必须严格按照页面显示顺序收集，不能对链接进行任何排序！
            view_urls = []  # 保持页面顺序的链接列表
            view_urls_set = set()  # 用于快速去重
            page_num = 1
            
            # 从第一页开始
            current_url = manga_url
            visited_page_urls = set()
            
            while True:
                # 避免重复访问同一分页
                if current_url in visited_page_urls:
                    logger.info(f"  检测到重复URL，停止扫描")
                    break
                
                logger.info(f"  扫描第 {page_num} 页: {current_url}")
                self.driver.get(current_url)
                visited_page_urls.add(current_url)
                time.sleep(2)
                
                # 查找所有图片查看链接 (photos-view-id-xxxxx.html)
                # 注意：find_elements 返回的顺序就是页面上的显示顺序
                view_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-view-id-']")
                
                if not view_links:
                    if page_num == 1:
                        logger.warning(f"    ✗ 第 1 页没有找到图片链接")
                    else:
                        logger.info(f"    第 {page_num} 页没有更多图片，停止扫描")
                    break
                
                # 按照页面顺序提取链接，使用 set 快速去重
                page_view_count = 0
                for link in view_links:
                    url = link.get_attribute('href')
                    # 去重：只添加未见过的链接，但保持顺序
                    if url and 'photos-view-id-' in url and url not in view_urls_set:
                        view_urls.append(url)
                        view_urls_set.add(url)
                        page_view_count += 1
                
                logger.info(f"    找到 {page_view_count} 个图片链接（总计: {len(view_urls)}）")
                
                # 查找下一页链接（使用HTML元素和Class名称，避免汉字字符串）
                next_page_url = None
                try:
                    # 通过分页器结构查找（使用class名称）
                    paginator = self.driver.find_element(By.CSS_SELECTOR, ".paginator")
                    if paginator:
                        # 查找所有分页链接（在paginator内的a标签，包含photos-index和-page-）
                        page_links = paginator.find_elements(By.CSS_SELECTOR, "a[href*='photos-index'][href*='-page-']")
                        for link in page_links:
                            href = link.get_attribute('href')
                            if href and href not in visited_page_urls:
                                next_page_url = href
                                break
                except:
                    pass
                
                if not next_page_url:
                    try:
                        # 备用方法：直接查找所有符合条件的分页链接
                        all_page_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index'][href*='-page-']")
                        for link in all_page_links:
                            href = link.get_attribute('href')
                            if href and href not in visited_page_urls:
                                next_page_url = href
                                break
                    except:
                        pass
                
                if not next_page_url:
                    logger.info(f"    没有找到下一页链接，扫描完成")
                    break
                
                # 确保URL是完整的（处理相对路径）
                if not self.base_url:
                    logger.error("base_url未设置，无法处理下一页链接")
                    break
                if next_page_url.startswith('/'):
                    base = self.base_url.rstrip('/')
                    next_page_url = f"{base}{next_page_url}"
                elif not next_page_url.startswith('http'):
                    base = self.base_url.rstrip('/')
                    next_page_url = f"{base}/{next_page_url}"
                
                current_url = next_page_url
                if not current_url:
                    logger.warning(f"    下一页链接无效，停止扫描")
                    break
                
                page_num += 1
                
                # 安全限制：最多 100 页
                if page_num > 100:
                    logger.warning(f"    达到最大页数限制 (100 页)")
                    break
            
            logger.info(f"\n共收集到 {len(view_urls)} 个图片链接")
            
            if not view_urls:
                logger.warning("✗ 没有找到任何图片链接")
                return []
            
            # 第二步：逐个访问链接获取原图
            images = []
            
            for idx, view_url in enumerate(view_urls, 1):
                try:
                    logger.info(f"  [{idx}/{len(view_urls)}] 获取原图...")
                    self.driver.get(view_url)
                    time.sleep(1.5)
                    
                    # 查找原图
                    # 原图特征：src 包含 wnimg，且路径为 /data/.../xxx.jpg (不含 /t/)
                    img_elems = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='wnimg']")
                    original_url = None
                    
                    for img_elem in img_elems:
                        src = img_elem.get_attribute('src')
                        # 过滤掉缩略图 (包含 /t/) 和其他非原图
                        if src and '/data/' in src and '/t/' not in src:
                            original_url = src
                            break
                    
                    if original_url:
                        # 获取文件扩展名
                        ext = original_url.split('.')[-1].split('?')[0] if '.' in original_url else 'jpg'
                        images.append({
                            'index': idx,
                            'url': original_url,
                            'filename': f"{idx:04d}.{ext}"
                        })
                        logger.debug(f"    ✓ {original_url[:70]}...")
                    else:
                        logger.warning(f"    ✗ 未找到原图")
                        
                except Exception as e:
                    logger.warning(f"    ✗ 获取失败: {e}")
                    continue
            
            logger.info(f"\n✓ 成功获取 {len(images)}/{len(view_urls)} 张原图")
            return images
            
        except Exception as e:
            logger.error(f"获取漫画图片失败: {e}")
            import traceback
            traceback.print_exc()
            return []

