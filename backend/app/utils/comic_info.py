"""ComicInfo.xml 生成工具"""
from typing import Optional, Dict
from datetime import datetime
from xml.etree.ElementTree import Element, tostring
from xml.dom import minidom


def generate_comic_info_xml(
    title: str,
    author: str = "",
    page_count: Optional[int] = None,
    updated_at: Optional[datetime] = None,
    manga_url: Optional[str] = None,
    **kwargs
) -> str:
    """
    生成 ComicInfo.xml 内容
    
    Args:
        title: 漫画标题
        author: 作者名称
        page_count: 页数
        updated_at: 更新日期
        manga_url: 漫画URL
        **kwargs: 其他可选字段（Series, Volume, Number, Summary, Publisher, Genre, Tags等）
    
    Returns:
        ComicInfo.xml 的字符串内容
    """
    # 创建根元素
    comic_info = Element("ComicInfo")
    comic_info.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    comic_info.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")
    
    # 基本信息
    if title:
        title_elem = Element("Title")
        title_elem.text = title
        comic_info.append(title_elem)
    
    if author:
        writer_elem = Element("Writer")
        writer_elem.text = author
        comic_info.append(writer_elem)
    
    # 系列信息（从标题中提取，如果有分隔符）
    if kwargs.get("series"):
        series_elem = Element("Series")
        series_elem.text = kwargs["series"]
        comic_info.append(series_elem)
    elif "_" in title or " " in title:
        # 尝试从标题中提取系列名（假设格式为"系列名_卷号"或"系列名 卷号"）
        parts = title.replace("_", " ").split()
        if len(parts) > 1:
            series_elem = Element("Series")
            series_elem.text = parts[0]
            comic_info.append(series_elem)
    
    # 卷号和期号
    if kwargs.get("volume"):
        volume_elem = Element("Volume")
        volume_elem.text = str(kwargs["volume"])
        comic_info.append(volume_elem)
    
    if kwargs.get("number"):
        number_elem = Element("Number")
        number_elem.text = str(kwargs["number"])
        comic_info.append(number_elem)
    
    # 页数
    if page_count:
        page_count_elem = Element("PageCount")
        page_count_elem.text = str(page_count)
        comic_info.append(page_count_elem)
    
    # 日期信息
    if updated_at:
        year_elem = Element("Year")
        year_elem.text = str(updated_at.year)
        comic_info.append(year_elem)
        
        month_elem = Element("Month")
        month_elem.text = str(updated_at.month)
        comic_info.append(month_elem)
        
        day_elem = Element("Day")
        day_elem.text = str(updated_at.day)
        comic_info.append(day_elem)
    
    # 摘要
    if kwargs.get("summary"):
        summary_elem = Element("Summary")
        summary_elem.text = kwargs["summary"]
        comic_info.append(summary_elem)
    
    # 出版商
    if kwargs.get("publisher"):
        publisher_elem = Element("Publisher")
        publisher_elem.text = kwargs["publisher"]
        comic_info.append(publisher_elem)
    
    # 类型/流派
    if kwargs.get("genre"):
        genre_elem = Element("Genre")
        genre_elem.text = kwargs["genre"]
        comic_info.append(genre_elem)
    
    # 标签
    if kwargs.get("tags"):
        tags_elem = Element("Tags")
        tags_elem.text = kwargs["tags"]
        comic_info.append(tags_elem)
    
    # 语言
    language_elem = Element("LanguageISO")
    if kwargs.get("language_iso"):
        language_elem.text = kwargs["language_iso"]
    else:
        # 默认使用中文
        language_elem.text = "zh-CN"
    comic_info.append(language_elem)
    
    # 年龄评级
    if kwargs.get("age_rating"):
        age_rating_elem = Element("AgeRating")
        age_rating_elem.text = kwargs["age_rating"]
        comic_info.append(age_rating_elem)
    
    # 网页链接
    if manga_url:
        web_elem = Element("Web")
        web_elem.text = manga_url
        comic_info.append(web_elem)
    
    # 漫画阅读方向（从右到左）
    if kwargs.get("manga") or kwargs.get("is_manga"):
        manga_elem = Element("Manga")
        manga_elem.text = "YesAndRightToLeft"
        comic_info.append(manga_elem)
    
    # 其他创作者信息
    if kwargs.get("penciller"):
        penciller_elem = Element("Penciller")
        penciller_elem.text = kwargs["penciller"]
        comic_info.append(penciller_elem)
    
    if kwargs.get("inker"):
        inker_elem = Element("Inker")
        inker_elem.text = kwargs["inker"]
        comic_info.append(inker_elem)
    
    if kwargs.get("colorist"):
        colorist_elem = Element("Colorist")
        colorist_elem.text = kwargs["colorist"]
        comic_info.append(colorist_elem)
    
    if kwargs.get("letterer"):
        letterer_elem = Element("Letterer")
        letterer_elem.text = kwargs["letterer"]
        comic_info.append(letterer_elem)
    
    if kwargs.get("cover_artist"):
        cover_artist_elem = Element("CoverArtist")
        cover_artist_elem.text = kwargs["cover_artist"]
        comic_info.append(cover_artist_elem)
    
    if kwargs.get("editor"):
        editor_elem = Element("Editor")
        editor_elem.text = kwargs["editor"]
        comic_info.append(editor_elem)
    
    if kwargs.get("translator"):
        translator_elem = Element("Translator")
        translator_elem.text = kwargs["translator"]
        comic_info.append(translator_elem)
    
    # 系列分组
    if kwargs.get("series_group"):
        series_group_elem = Element("SeriesGroup")
        series_group_elem.text = kwargs["series_group"]
        comic_info.append(series_group_elem)
    
    # 转换为格式化的 XML 字符串
    rough_string = tostring(comic_info, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

