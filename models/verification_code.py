import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Sequence, Column, DateTime
from sqlalchemy.types import Integer, String
from sqlalchemy.sql import func
from base.base import Base

class VerificationCode(Base):
    __tablename__ = 'xu_verification_code'
    
    id = Column(Integer, Sequence('verification_code_id_seq'), primary_key=True)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Integer, default=0)
    
    def __init__(self, phone, code, expires_at):
        self.phone = phone
        self.code = code
        self.expires_at = expires_at
        self.is_used = 0
    
    def __repr__(self):
        return f"<VerificationCode(phone={self.phone}, code={self.code}, is_used={self.is_used})>"
