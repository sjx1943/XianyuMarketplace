"""
图片处理工具模块
提供缩略图生成等功能
"""

import os
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)

THUMB_WIDTH = 360  # 列表页缩略图宽度
MEDIUM_WIDTH = 720  # 详情页中等尺寸图片宽度
THUMB_QUALITY = 70  # 缩略图质量
MEDIUM_QUALITY = 80  # 中等尺寸图片质量


def generate_medium_image(image_data: bytes, original_filename: str, upload_path: str) -> str:
    """
    生成中等尺寸图片（用于详情页展示）
    
    Args:
        image_data: 原始图片的二进制数据
        original_filename: 原始文件名（如 "123_0_image.jpg"）
        upload_path: 图片存储目录
    
    Returns:
        中等尺寸图片文件名，如 "medium_123_0_image.jpg"
        如果生成失败返回 None
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        width, height = img.size
        if width <= MEDIUM_WIDTH:
            return None
        
        ratio = MEDIUM_WIDTH / width
        new_height = int(height * ratio)
        new_size = (MEDIUM_WIDTH, new_height)
        
        img.thumbnail(new_size, Image.Resampling.LANCZOS)
        
        name, ext = os.path.splitext(original_filename)
        medium_filename = f"medium_{name}.jpg"
        medium_path = os.path.join(upload_path, medium_filename)
        
        img.save(medium_path, 'JPEG', quality=MEDIUM_QUALITY, optimize=True)
        
        logger.info(f"生成中等尺寸图片成功: {medium_filename} ({new_size[0]}x{new_size[1]})")
        return medium_filename
        
    except Exception as e:
        logger.error(f"生成中等尺寸图片失败: {e}")
        return None


def generate_thumbnail(image_data: bytes, original_filename: str, upload_path: str) -> str:
    """
    生成缩略图
    
    Args:
        image_data: 原始图片的二进制数据
        original_filename: 原始文件名（如 "123_0_image.jpg"）
        upload_path: 图片存储目录
    
    Returns:
        缩略图文件名，如 "thumb_123_0_image.jpg"
        如果生成失败返回 None
    """
    try:
        # 打开图片
        img = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB模式（处理RGBA/P模式的PNG）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 计算缩略图尺寸（保持宽高比）
        width, height = img.size
        if width <= THUMB_WIDTH:
            # 图片已经足够小，直接使用原图
            return None
        
        # 计算新尺寸
        ratio = THUMB_WIDTH / width
        new_height = int(height * ratio)
        new_size = (THUMB_WIDTH, new_height)
        
        # 生成缩略图
        img.thumbnail(new_size, Image.Resampling.LANCZOS)
        
        # 生成缩略图文件名
        name, ext = os.path.splitext(original_filename)
        thumb_filename = f"thumb_{name}.jpg"  # 统一使用jpg格式
        thumb_path = os.path.join(upload_path, thumb_filename)
        
        # 保存缩略图
        img.save(thumb_path, 'JPEG', quality=THUMB_QUALITY, optimize=True)
        
        logger.info(f"生成缩略图成功: {thumb_filename} ({new_size[0]}x{new_size[1]})")
        return thumb_filename
        
    except Exception as e:
        logger.error(f"生成缩略图失败: {e}")
        return None
