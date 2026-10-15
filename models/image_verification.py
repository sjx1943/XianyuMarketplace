#coding=utf-8
"""
图片安全验证记录
用于跟踪 WeChat mediaCheckAsync 异步检测结果
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Column, String, DateTime, Integer, Enum, Text
from sqlalchemy.sql import func
from base.base import Base, engine
import enum


class VerificationStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class BizType(enum.Enum):
    AVATAR = 'avatar'
    PRODUCT = 'product'
    CHAT = 'chat'


class ImageVerification(Base):
    __tablename__ = 'image_verifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_user_id = Column(Integer, nullable=True, index=True)
    biz_type = Column(String(50), nullable=False, default='avatar')
    biz_id = Column(Integer, nullable=True)
    file_url = Column(String(500), nullable=True)
    image_url = Column(Text, nullable=True)
    trace_id = Column(String(100), nullable=True, index=True)
    status = Column(String(20), nullable=False, default='pending')
    reason_label = Column(Integer, nullable=True)
    wechat_suggest = Column(String(20), nullable=True)
    reject_reason = Column(Text, nullable=True)
    owner_product_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    reviewed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ImageVerification(id={self.id}, user={self.owner_user_id}, status={self.status}, trace_id={self.trace_id})>"

    def to_dict(self):
        return {
            'id': self.id,
            'owner_user_id': self.owner_user_id,
            'biz_type': self.biz_type,
            'biz_id': self.biz_id,
            'file_url': self.file_url,
            'trace_id': self.trace_id,
            'status': self.status,
            'reason_label': self.reason_label,
            'wechat_suggest': self.wechat_suggest,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at is not None else None
        }
