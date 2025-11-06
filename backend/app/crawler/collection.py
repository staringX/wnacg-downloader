"""收藏夹爬取模块"""
import time
import re
from typing import Dict, Generator
from selenium.webdriver.common.by import By
from app.utils.logger import logger


class CollectionCrawler:
    """收藏夹爬取器 - 负责从收藏夹获取漫画列表"""
    
    def __init__(self, browser_manager):
        self.browser = browser_manager
        self.driver = browser_manager.driver
        self.base_url = browser_manager.base_url
    
    def get_collection_stream(self) -> Generator[Dict, None, None]:
        """
        获取收藏夹中的所有漫画（生成器版本）
        边爬取边返回，不等待全部完成，实现真正的实时同步
        
        Yields:
            dict: 漫画信息字典 {'title', 'author', 'manga_url', 'page_count'}
        """
        if not self.driver:
            return
        
        try:
            manga_urls_set = set()  # 用于去重
            base = self.base_url.rstrip('/')
            
            # 正确的书架URL
            bookshelf_url = f"{base}/users-users_fav.html"
            logger.info(f"访问书架页面: {bookshelf_url}")
            self.driver.get(bookshelf_url)
            time.sleep(5)
            
            # 检查页面是否成功加载
            current_url = self.driver.current_url
            page_title = self.driver.title
            logger.info(f"当前页面URL: {current_url}")
            logger.info(f"页面标题: {page_title}")
            
            if "404" in page_title.lower() or "404" in self.driver.page_source[:1000].lower():
                logger.warning(f"书架页面返回404")
                return
            
            # 查找分类链接
            category_links = {}
            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a")
            
            for link in all_links:
                href = link.get_attribute('href') or ''
                text = link.text.strip()
                
                if 'users-users_fav-c-' in href and text:
                    if text not in ["全部", "管理分類", "書架", "书架", "我的書架"]:
                        category_links[text] = href
                        logger.info(f"找到分类: {text} -> {href}")
            
            logger.info(f"共找到 {len(category_links)} 个作者分类\n")
            
            total_count = 0
            
            # 如果有分类，按分类获取漫画
            if category_links:
                for author_idx, (author, category_url) in enumerate(category_links.items(), 1):
                    logger.info(f"[{author_idx}/{len(category_links)}] 处理作者分类: {author}")
                    
                    # 提取分类ID
                    category_id_match = re.search(r'users-users_fav-c-(\d+)\.html', category_url)
                    if not category_id_match:
                        logger.warning(f"  无法提取分类ID，跳过")
                        continue
                    
                    category_id = category_id_match.group(1)
                    page_num = 1
                    author_manga_count = 0
                    
                    current_url = category_url
                    visited_urls = set()
                    
                    # 遍历所有分页
                    while True:
                        if current_url in visited_urls:
                            logger.info(f"  检测到重复URL，停止翻页")
                            break
                        
                        logger.info(f"  访问第 {page_num} 页: {current_url}")
                        self.driver.get(current_url)
                        visited_urls.add(current_url)
                        time.sleep(2)
                        
                        # 查找该页面下的所有漫画链接
                        manga_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index-aid-']")
                        logger.info(f"    🔍 CSS找到 {len(manga_links)} 个链接")
                        
                        # 🔥 关键修复：立即提取所有链接信息，避免stale element reference
                        manga_info_list = []
                        for manga_link in manga_links:
                            try:
                                manga_url = manga_link.get_attribute('href')
                                title = manga_link.text.strip()
                                
                                # 尝试获取页数信息（使用class名称，避免汉字字符串）
                                page_count = None
                                try:
                                    # 查找包含漫画链接的父容器，然后查找 p.l_detla 元素
                                    parent_container = manga_link.find_element(By.XPATH, "./ancestor::*[contains(@class, 'u_listcon') or contains(@class, 'box_cel')]")
                                    page_elem = parent_container.find_element(By.CSS_SELECTOR, "p.l_detla")
                                    if page_elem:
                                        page_text = page_elem.text
                                        # 从文本中提取数字（格式：頁數：20 或 頁數：20P）
                                        page_match = re.search(r'(\d+)\s*P?', page_text)
                                        if page_match:
                                            page_count = int(page_match.group(1))
                                except:
                                    pass
                                
                                if manga_url and title:
                                    manga_info_list.append({
                                        'url': manga_url,
                                        'title': title,
                                        'page_count': page_count
                                    })
                            except Exception as e:
                                # 如果获取信息失败，跳过这个链接
                                continue
                        
                        # 现在处理提取的信息列表
                        page_manga_count = 0
                        empty_count = 0
                        dup_count = 0
                        
                        for idx, manga_info in enumerate(manga_info_list, 1):
                            try:
                                manga_url = manga_info['url']
                                title = manga_info['title']
                                page_count = manga_info.get('page_count')
                                
                                if idx <= 3:  # 打印前3个
                                    logger.debug(f"      [{idx}] URL={manga_url[-30:]}, Title='{title[:50]}'")
                                
                                if not title or not manga_url:
                                    empty_count += 1
                                    if idx <= 3:
                                        logger.debug(f"      [{idx}] ❌ 跳过：标题或URL为空")
                                    continue
                                
                                # 去重
                                if manga_url in manga_urls_set:
                                    dup_count += 1
                                    if idx <= 3:
                                        logger.debug(f"      [{idx}] ⏭️  跳过：重复")
                                    continue
                                
                                # ✨ 关键：立即 yield，不等待后续爬取
                                manga_urls_set.add(manga_url)
                                page_manga_count += 1
                                author_manga_count += 1
                                total_count += 1
                                
                                yield {
                                    'title': title,
                                    'author': author,
                                    'manga_url': manga_url,
                                    'page_count': page_count
                                }
                                
                            except Exception as e:
                                logger.warning(f"    处理漫画失败: {e}")
                                continue
                        
                        logger.info(f"    第 {page_num} 页：找到 {page_manga_count} 个漫画（总计: {total_count}）")
                        logger.debug(f"    📊 跳过：空标题/URL={empty_count}, 重复={dup_count}")
                        
                        if page_manga_count == 0:
                            logger.info(f"    第 {page_num} 页没有找到漫画，停止翻页")
                            break
                        
                        # 查找下一页链接（使用HTML元素和Class名称，避免汉字字符串）
                        next_page_url = None
                        
                        # 🔥 关键修复：先收集所有可能的翻页链接URL，避免stale element reference
                        candidate_urls = []
                        
                        try:
                            # 方法1：通过分页器结构查找（使用class名称）
                            paginator = self.driver.find_element(By.CSS_SELECTOR, ".paginator")
                            if paginator:
                                # 查找所有分页链接（在paginator内的a标签）
                                page_links = paginator.find_elements(By.CSS_SELECTOR, f"a[href*='users-users_fav'][href*='-page-']")
                                for link in page_links:
                                    href = link.get_attribute('href')
                                    # 必须包含 users-users_fav 和 page，且未访问过，且包含当前category_id
                                    if href and href not in visited_urls and '-page-' in href and f'c-{category_id}' in href:
                                        candidate_urls.append(href)
                        except Exception as e:
                            pass
                        
                        if not candidate_urls:
                            try:
                                # 方法2：直接查找所有符合条件的分页链接（备用方法）
                                all_page_links = self.driver.find_elements(By.CSS_SELECTOR, f"a[href*='users-users_fav'][href*='c-{category_id}'][href*='-page-']")
                                for link in all_page_links:
                                    href = link.get_attribute('href')
                                    if href and href not in visited_urls:
                                        candidate_urls.append(href)
                            except Exception as e:
                                pass
                        
                        # 从候选中选择第一个未访问的URL
                        if candidate_urls:
                            next_page_url = candidate_urls[0]
                            # 🔥 确保URL是完整的（处理相对路径）
                            if next_page_url.startswith('/'):
                                base = self.base_url.rstrip('/')
                                next_page_url = f"{base}{next_page_url}"
                            elif not next_page_url.startswith('http'):
                                base = self.base_url.rstrip('/')
                                next_page_url = f"{base}/{next_page_url}"
                            logger.debug(f"    找到下一页链接: {next_page_url[:80]}")
                        
                        if not next_page_url:
                            logger.info(f"    没有找到下一页链接，停止翻页")
                            break
                        
                        current_url = next_page_url
                        if not current_url:
                            logger.warning(f"    下一页链接无效，停止翻页")
                            break
                        
                        page_num += 1
                        
                        if page_num > 100:
                            logger.warning(f"    已达到最大页数限制(100页)，停止翻页")
                            break
                    
                    logger.info(f"  {author} 总共获取 {author_manga_count} 个漫画\n")
            else:
                # 如果没有找到分类链接，直接从当前页面获取所有漫画
                logger.info("未找到分类链接，从当前页面直接获取漫画...")
                manga_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index-aid-']")
                logger.info(f"找到 {len(manga_links)} 个漫画链接")
                
                for manga_link in manga_links:
                    try:
                        manga_url = manga_link.get_attribute('href')
                        title = manga_link.text.strip()
                        
                        if title and manga_url and manga_url not in manga_urls_set:
                            author = "未知"
                            try:
                                parent = manga_link.find_element(By.XPATH, "./ancestor::*[position()<=5]")
                                author_elem = parent.find_elements(By.XPATH, ".//*[contains(@href, 'users-users_fav-c-')]")
                                if author_elem:
                                    author = author_elem[0].text.strip() or "未知"
                            except:
                                pass
                            
                            page_count = None
                            try:
                                # 查找包含漫画链接的父容器，然后查找 p.l_detla 元素
                                parent_container = manga_link.find_element(By.XPATH, "./ancestor::*[contains(@class, 'u_listcon') or contains(@class, 'box_cel')]")
                                page_elem = parent_container.find_element(By.CSS_SELECTOR, "p.l_detla")
                                if page_elem:
                                    page_text = page_elem.text
                                    # 从文本中提取数字（格式：頁數：20 或 頁數：20P）
                                    page_match = re.search(r'(\d+)\s*P?', page_text)
                                    if page_match:
                                        page_count = int(page_match.group(1))
                            except:
                                pass
                            
                            manga_urls_set.add(manga_url)
                            total_count += 1
                            
                            yield {
                                'title': title,
                                'author': author,
                                'manga_url': manga_url,
                                'page_count': page_count
                            }
                    except Exception as e:
                        logger.warning(f"处理漫画失败: {e}")
                        continue
            
            logger.info(f"\n✓ 收藏夹爬取完成，总共 {total_count} 个漫画")
            
        except Exception as e:
            logger.error(f"获取收藏夹失败: {e}")
            import traceback
            traceback.print_exc()
            return

