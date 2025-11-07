"""收藏夹爬取模块"""
import time
import re
from typing import Dict, Generator
from selenium.webdriver.common.by import By
from app.utils.logger import logger, get_error_message


class CollectionCrawler:
    """收藏夹爬取器 - 负责从收藏夹获取漫画列表"""
    
    def __init__(self, browser_manager):
        self.browser = browser_manager
        self.driver = browser_manager.driver
    
    @property
    def base_url(self):
        """动态获取base_url，确保获取到最新值"""
        return self.browser.base_url
    
    def get_collection_stream(self) -> Generator[Dict, None, None]:
        """
        获取收藏夹中的所有漫画（生成器版本）
        边爬取边返回，不等待全部完成，实现真正的实时同步
        
        Yields:
            dict: 漫画信息字典 {'title', 'author', 'manga_url', 'page_count'}
        """
        if not self.driver:
            return
        
        # 确保base_url已设置
        if not self.base_url:
            logger.error("base_url未设置，无法获取收藏夹")
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
                    # 🔥 关键改进：先缓存下一页链接，再遍历当前页，避免stale element reference
                    next_page_url = None  # 缓存的下一页链接
                    
                    while True:
                        if current_url in visited_urls:
                            logger.info(f"  检测到重复URL，停止翻页")
                            break
                        
                        logger.info(f"  访问第 {page_num} 页: {current_url}")
                        self.driver.get(current_url)
                        visited_urls.add(current_url)
                        time.sleep(2)
                        
                        # 🔥 第一步：立即查找并缓存下一页链接（在遍历漫画之前）
                        if not next_page_url:  # 如果还没有缓存下一页链接，现在查找
                            logger.debug(f"    查找下一页链接...")
                            
                            try:
                                # 根据MCP确认的结构：分页器有class "paginator"
                                paginator = self.driver.find_element(By.CSS_SELECTOR, ".paginator")
                                logger.debug(f"    ✓ 找到分页器元素 (class: paginator)")
                                
                                # 🔥 只使用 ".next > a"（"後頁>"链接）来获取下一页
                                try:
                                    next_span = paginator.find_element(By.CSS_SELECTOR, ".next")
                                    if next_span:
                                        next_link = next_span.find_element(By.CSS_SELECTOR, "a")
                                        if next_link:
                                            href = next_link.get_attribute('href')
                                            if href:
                                                # 处理相对路径
                                                if not self.base_url:
                                                    logger.error("base_url未设置，无法处理下一页链接")
                                                else:
                                                    if href.startswith('/'):
                                                        base = self.base_url.rstrip('/')
                                                        full_url = f"{base}{href}"
                                                    elif not href.startswith('http'):
                                                        base = self.base_url.rstrip('/')
                                                        full_url = f"{base}/{href}"
                                                    else:
                                                        full_url = href
                                                    
                                                    # 验证URL是否符合条件
                                                    if ('users-users_fav' in full_url and 
                                                        '-page-' in full_url and 
                                                        f'c-{category_id}' in full_url and
                                                        full_url not in visited_urls):
                                                        next_page_url = full_url
                                                        logger.info(f"    ✓ 通过'.next > a'找到下一页: {next_page_url[:80]}")
                                                    else:
                                                        logger.debug(f"    '.next > a'链接不符合条件或已访问: {full_url[:80]}")
                                            else:
                                                logger.debug(f"    '.next > a'链接没有href属性")
                                        else:
                                            logger.debug(f"    '.next'内未找到<a>标签")
                                    else:
                                        logger.debug(f"    未找到'.next'元素")
                                except Exception as e:
                                    logger.debug(f"    未找到'.next > a'链接: {get_error_message(e)}")
                                
                                if not next_page_url:
                                    logger.info(f"    ⚠️  未找到'.next > a'链接，这是最后一页，遍历完当前页后将结束")
                            except Exception as e:
                                logger.warning(f"    查找分页器失败: {get_error_message(e)}")
                                pass
                        
                        # 🔥 第二步：遍历当前页面的漫画（此时下一页链接已缓存）
                        manga_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index-aid-']")
                        logger.info(f"    🔍 CSS找到 {len(manga_links)} 个链接")
                        
                        # 立即提取所有链接信息，避免stale element reference
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
                        
                        # 处理提取的信息列表
                        page_manga_count = 0
                        empty_count = 0
                        dup_count = 0
                        
                        for idx, manga_info in enumerate(manga_info_list, 1):
                            try:
                                manga_url = manga_info['url']
                                title = manga_info['title']
                                page_count = manga_info.get('page_count')
                                
                                if not title or not manga_url:
                                    empty_count += 1
                                    continue
                                
                                # 去重
                                if manga_url in manga_urls_set:
                                    dup_count += 1
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
                                logger.warning(f"    处理漫画失败: {get_error_message(e)}")
                                continue
                        
                        logger.info(f"    第 {page_num} 页：找到 {page_manga_count} 个漫画（总计: {total_count}）")
                        logger.debug(f"    📊 跳过：空标题/URL={empty_count}, 重复={dup_count}")
                        
                        if page_manga_count == 0:
                            logger.info(f"    第 {page_num} 页没有找到漫画，停止翻页")
                            break
                        
                        # 🔥 第三步：检查是否有下一页链接
                        # 如果找不到'.next > a'链接，说明已经到最后一页，遍历完当前页后结束，继续下一个作者
                        if not next_page_url:
                            logger.info(f"    ✓ 已到最后一页（未找到'.next > a'链接），结束当前作者，继续下一个作者")
                            break
                        
                        # 保存当前缓存的下一页链接
                        current_url = next_page_url
                        next_page_url = None  # 清空缓存，准备查找新的下一页
                        
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
                        logger.warning(f"处理漫画失败: {get_error_message(e)}")
                        continue
            
            logger.info(f"\n✓ 收藏夹爬取完成，总共 {total_count} 个漫画")
            
        except Exception as e:
            logger.error(f"获取收藏夹失败: {get_error_message(e)}")
            return

