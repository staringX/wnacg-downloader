"""搜索功能模块"""
import time
import re
from typing import List, Dict
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs, urlencode
from selenium.webdriver.common.by import By
from app.utils.logger import logger


class SearchCrawler:
    """搜索爬取器 - 负责搜索作者并获取更新"""
    
    def __init__(self, browser_manager):
        self.browser = browser_manager
        self.driver = browser_manager.driver
        self.base_url = browser_manager.base_url
    
    def search_author_updates(self, author_name: str, since_date: datetime) -> List[Dict]:
        """
        搜索作者并获取更新
        
        Args:
            author_name: 作者名称
            since_date: 截止日期，只返回晚于此日期的漫画
            
        Returns:
            漫画列表，每个包含 title, manga_url, updated_at, page_count, cover_image_url, author
        """
        if not self.driver:
            logger.error("浏览器驱动未初始化")
            return []
        
        try:
            base = self.base_url.rstrip('/')
            # 构造搜索URL（使用正确的搜索格式）
            encoded_author = quote(author_name)
            search_url = f"{base}/q/?q={encoded_author}&f=_all&s=create_time_DESC&syn=yes"
            logger.info(f"搜索作者: {author_name}, URL: {search_url}")
            
            visited_urls = set()
            current_url = search_url
            page_num = 1
            all_mangas = []
            
            # 遍历所有搜索结果页面
            while True:
                if current_url in visited_urls:
                    logger.info(f"  检测到重复URL，停止翻页")
                    break
                
                logger.info(f"  访问第 {page_num} 页: {current_url}")
                self.driver.get(current_url)
                visited_urls.add(current_url)
                time.sleep(2)
                
                # 查找漫画列表容器（使用正确的选择器）
                manga_info_list = []
                try:
                    # 查找 ul.col_2 容器
                    container = self.driver.find_element(By.CSS_SELECTOR, "ul.col_2")
                    # 查找所有 li.cate-* 项
                    manga_items = container.find_elements(By.CSS_SELECTOR, "li[class*='cate-']")
                    logger.info(f"    找到 {len(manga_items)} 个漫画项")
                    
                    for item in manga_items:
                        try:
                            # 查找漫画链接
                            manga_link = item.find_element(By.CSS_SELECTOR, "a[href*='photos-index-aid-']")
                            manga_url = manga_link.get_attribute('href')
                            title = manga_link.text.strip()
                            
                            if not manga_url or not title:
                                continue
                            
                            # 确保URL完整
                            if manga_url.startswith('/'):
                                manga_url = f"{base}{manga_url}"
                            elif not manga_url.startswith('http'):
                                manga_url = f"{base}/{manga_url}"
                            
                            # 获取创建时间和页数（从 span.info 中提取）
                            updated_at = None
                            page_count = None
                            try:
                                info_span = item.find_element(By.CSS_SELECTOR, "span.info")
                                info_text = info_span.text
                                
                                # 提取日期：创建于2024-09-21 01:45:25
                                date_match = re.search(r'创建于(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})', info_text)
                                if date_match:
                                    date_str = f"{date_match.group(1)} {date_match.group(2)}"
                                    updated_at = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                                else:
                                    # 尝试只提取日期
                                    date_match = re.search(r'创建于(\d{4}-\d{2}-\d{2})', info_text)
                                    if date_match:
                                        date_str = date_match.group(1)
                                        updated_at = datetime.strptime(date_str, '%Y-%m-%d')
                                
                                # 提取页数：55张图片
                                page_match = re.search(r'(\d+)张图片', info_text)
                                if page_match:
                                    page_count = int(page_match.group(1))
                            except:
                                pass
                            
                            # 获取封面图片URL
                            cover_image_url = None
                            try:
                                img = item.find_element(By.CSS_SELECTOR, "img[src*='wnimg'], img[src*='qy0']")
                                cover_image_url = img.get_attribute('src')
                                if cover_image_url:
                                    if cover_image_url.startswith('//'):
                                        cover_image_url = f"https:{cover_image_url}"
                                    elif cover_image_url.startswith('/'):
                                        cover_image_url = f"{base}{cover_image_url}"
                                    elif not cover_image_url.startswith('http'):
                                        cover_image_url = f"{base}/{cover_image_url}"
                            except:
                                pass
                            
                            manga_info_list.append({
                                'url': manga_url,
                                'title': title,
                                'updated_at': updated_at,
                                'page_count': page_count,
                                'cover_image_url': cover_image_url
                            })
                        except Exception as e:
                            logger.warning(f"    提取漫画信息失败: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"    查找漫画列表失败: {e}")
                    # 备用方法：直接查找所有漫画链接
                    manga_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index-aid-']")
                    logger.info(f"    备用方法找到 {len(manga_links)} 个漫画链接")
                    for manga_link in manga_links:
                        try:
                            manga_url = manga_link.get_attribute('href')
                            title = manga_link.text.strip()
                            if manga_url and title:
                                if manga_url.startswith('/'):
                                    manga_url = f"{base}{manga_url}"
                                manga_info_list.append({
                                    'url': manga_url,
                                    'title': title,
                                    'updated_at': None,
                                    'page_count': None,
                                    'cover_image_url': None
                                })
                        except:
                            continue
                
                if len(manga_info_list) == 0:
                    logger.info(f"    第 {page_num} 页没有找到漫画，停止翻页")
                    break
                
                # 筛选出晚于截止日期的漫画，同时检查是否遇到早于截止日期的漫画
                # 由于搜索结果按时间倒序排列，一旦遇到早于截止日期的漫画，后面的都是更旧的，可以停止翻页
                should_stop = False
                for manga_info in manga_info_list:
                    if manga_info['updated_at']:
                        if manga_info['updated_at'] > since_date:
                            # 晚于截止日期，添加到结果
                            all_mangas.append({
                                'title': manga_info['title'],
                                'manga_url': manga_info['url'],
                                'updated_at': manga_info['updated_at'],
                                'page_count': manga_info['page_count'],
                                'cover_image_url': manga_info['cover_image_url'],
                                'author': author_name
                            })
                        else:
                            # 早于或等于截止日期，由于结果按时间倒序，后面的都是更旧的，可以停止翻页
                            logger.info(f"    遇到早于截止日期的漫画（{manga_info['updated_at']} <= {since_date}），停止翻页")
                            should_stop = True
                            break
                
                # 如果遇到早于截止日期的漫画，停止翻页
                if should_stop:
                    break
                
                # 查找下一页链接（搜索页面可能使用不同的翻页方式）
                next_page_url = None
                try:
                    # 方法1：查找 .paginator 中的链接
                    paginator = self.driver.find_element(By.CSS_SELECTOR, ".paginator")
                    if paginator:
                        page_links = paginator.find_elements(By.CSS_SELECTOR, "a[href*='q=']")
                        for link in page_links:
                            href = link.get_attribute('href')
                            if href and href not in visited_urls and 'q=' in href:
                                next_page_url = href
                                break
                except:
                    pass
                
                # 方法2：如果没有找到，尝试通过URL参数翻页（添加 p=2, p=3 等）
                if not next_page_url:
                    # 检查当前页面是否有更多结果
                    if len(manga_info_list) > 0:
                        # 尝试构造下一页URL
                        parsed = urlparse(current_url)
                        params = parse_qs(parsed.query)
                        next_page = page_num + 1
                        params['p'] = [str(next_page)]
                        new_query = urlencode(params, doseq=True)
                        next_page_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
                        logger.info(f"    尝试构造下一页URL: {next_page_url}")
                    else:
                        logger.info(f"    当前页没有找到漫画，停止翻页")
                        break
                
                if not next_page_url:
                    logger.info(f"    没有找到下一页链接，停止翻页")
                    break
                
                # 确保URL是完整的
                if next_page_url.startswith('/'):
                    next_page_url = f"{base}{next_page_url}"
                elif not next_page_url.startswith('http'):
                    next_page_url = f"{base}/{next_page_url}"
                
                current_url = next_page_url
                page_num += 1
                
                if page_num > 100:  # 限制最大页数
                    logger.warning(f"    已达到最大页数限制(100页)，停止翻页")
                    break
            
            logger.info(f"  作者 {author_name} 共找到 {len(all_mangas)} 个新更新")
            return all_mangas
            
        except Exception as e:
            logger.error(f"搜索作者 {author_name} 失败: {e}")
            import traceback
            traceback.print_exc()
            return []

