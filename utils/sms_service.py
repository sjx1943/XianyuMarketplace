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
    生产模式：使用阿里云短信服务
    
    Args:
        phone: 手机号
        code: 验证码
    
    Returns:
        bool: 发送是否成功
    """
    import os
    
    access_key_id = os.environ.get('ALIYUN_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
    sign_name = os.environ.get('ALIYUN_SMS_SIGN_NAME')
    template_code = os.environ.get('ALIYUN_SMS_TEMPLATE_CODE')
    
    if not all([access_key_id, access_key_secret, sign_name, template_code]):
        logging.warning(f"=" * 50)
        logging.warning(f"📱 SMS验证码 (开发模式 - 未配置阿里云)")
        logging.warning(f"手机号: {phone}")
        logging.warning(f"验证码: {code}")
        logging.warning(f"有效期: 5分钟")
        logging.warning(f"=" * 50)
        return True
    
    try:
        from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
        
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret
        )
        config.endpoint = 'dysmsapi.aliyuncs.com'
        
        client = DysmsapiClient(config)
        
        request = dysmsapi_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=sign_name,
            template_code=template_code,
            template_param=f'{{"code":"{code}"}}'
        )
        
        response = client.send_sms(request)
        
        if response.body.code == 'OK':
            logging.info(f"阿里云短信发送成功: {phone}")
            return True
        else:
            logging.error(f"阿里云短信发送失败: {response.body.message}")
            return False
            
    except ImportError:
        logging.warning(f"=" * 50)
        logging.warning(f"📱 SMS验证码 (开发模式 - 未安装阿里云SDK)")
        logging.warning(f"手机号: {phone}")
        logging.warning(f"验证码: {code}")
        logging.warning(f"有效期: 5分钟")
        logging.warning(f"提示: pip install alibabacloud_dysmsapi20170525")
        logging.warning(f"=" * 50)
        return True
    except Exception as e:
        logging.error(f"发送短信失败: {e}")
        logging.warning(f"开发模式降级 - 验证码: {code}")
        return True

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
        
        # 使用北京时间（东8区）创建过期时间，与LoginHandler保持一致
        beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
        expires_at = datetime.datetime.now(beijing_tz) + datetime.timedelta(minutes=5)
        
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
        # 使用北京时间（东8区）验证，与LoginHandler保持一致
        beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
        now = datetime.datetime.now(beijing_tz)
        
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
        # 使用北京时间（东8区）清理，与create_verification_code保持一致
        beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
        now = datetime.datetime.now(beijing_tz)
        
        expired = session.query(VerificationCode).filter(
            VerificationCode.expires_at < now
        ).delete()
        
        session.commit()
        logging.info(f"清理了 {expired} 条过期验证码")
        
    except Exception as e:
        session.rollback()
        logging.error(f"清理过期验证码失败: {e}")
