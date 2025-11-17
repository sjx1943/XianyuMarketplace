import random
import datetime
import logging
from sqlalchemy.orm import Session
from models.verification_code import VerificationCode

def generate_verification_code():
    """生成6位随机验证码"""
    return str(random.randint(100000, 999999))

def send_sms(phone, code):
    """
    发送短信验证码
    
    开发模式：直接在控制台输出验证码
    生产模式：集成真实SMS服务（Twilio、阿里云短信等）
    
    Args:
        phone: 手机号
        code: 验证码
    
    Returns:
        bool: 发送是否成功
    """
    try:
        logging.warning(f"=" * 50)
        logging.warning(f"📱 SMS验证码 (开发模式)")
        logging.warning(f"手机号: {phone}")
        logging.warning(f"验证码: {code}")
        logging.warning(f"有效期: 5分钟")
        logging.warning(f"=" * 50)
        
        return True
    except Exception as e:
        logging.error(f"发送短信失败: {e}")
        return False

def create_verification_code(session: Session, phone: str):
    """
    创建验证码记录
    
    Args:
        session: 数据库会话
        phone: 手机号
    
    Returns:
        str: 验证码，如果失败返回None
    """
    try:
        code = generate_verification_code()
        
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=5)
        
        verification = VerificationCode(
            phone=phone,
            code=code,
            expires_at=expires_at
        )
        session.add(verification)
        session.commit()
        
        if send_sms(phone, code):
            return code
        else:
            return None
            
    except Exception as e:
        session.rollback()
        logging.error(f"创建验证码失败: {e}")
        return None

def verify_code(session: Session, phone: str, code: str):
    """
    验证手机号和验证码
    
    Args:
        session: 数据库会话
        phone: 手机号
        code: 验证码
    
    Returns:
        bool: 验证是否成功
    """
    try:
        now = datetime.datetime.now()
        
        verification = session.query(VerificationCode).filter(
            VerificationCode.phone == phone,
            VerificationCode.code == code,
            VerificationCode.is_used == 0,
            VerificationCode.expires_at > now
        ).order_by(VerificationCode.created_at.desc()).first()
        
        if verification:
            verification.is_used = 1
            session.commit()
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"验证失败: {e}")
        return False

def cleanup_expired_codes(session: Session):
    """
    清理过期的验证码（可以通过定时任务调用）
    """
    try:
        now = datetime.datetime.now()
        
        expired = session.query(VerificationCode).filter(
            VerificationCode.expires_at < now
        ).delete()
        
        session.commit()
        logging.info(f"清理了 {expired} 条过期验证码")
        
    except Exception as e:
        session.rollback()
        logging.error(f"清理过期验证码失败: {e}")
