#coding=utf-8
"""
微信小程序订阅消息服务
调用微信官方接口发送订阅消息通知
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone, timedelta

WX_MINIPROGRAM_APP_ID = os.environ.get('WX_MINIPROGRAM_APP_ID', '')
WX_MINIPROGRAM_APP_SECRET = os.environ.get('WX_MINIPROGRAM_APP_SECRET', '')

MINIPROGRAM_STATE = os.environ.get('MINIPROGRAM_STATE', 'trial')

TEMPLATE_IDS = {
    'ORDER_STATUS': 'k4RD1_bIRofb3DEjFX8hntwUzXnz5RyQ2pr0UGl51VM',
    'NEW_MESSAGE': 'rjOrDn_8fVDXDAUGD4gG2ZKAYb9BuKzBW_ajM46hRyw',
    'PRODUCT_SOLD': 'vl_2Uka9BE2-qgP9Snbse4IFSO6mUe5rPnQxzjcFEXk'
}

_access_token_cache = {
    'token': None,
    'expires_at': 0
}

def clear_access_token_cache():
    """清除access_token缓存，用于token失效时强制刷新"""
    _access_token_cache['token'] = None
    _access_token_cache['expires_at'] = 0

def get_access_token(force_refresh=False):
    """
    获取微信小程序access_token（带缓存）
    """
    now = datetime.now().timestamp()
    
    if not force_refresh and _access_token_cache['token'] and _access_token_cache['expires_at'] > now + 300:
        return _access_token_cache['token']
    
    if not WX_MINIPROGRAM_APP_ID or not WX_MINIPROGRAM_APP_SECRET:
        logging.warning('微信小程序凭证未配置，无法获取access_token')
        return None
    
    try:
        url = 'https://api.weixin.qq.com/cgi-bin/token'
        params = {
            'grant_type': 'client_credential',
            'appid': WX_MINIPROGRAM_APP_ID,
            'secret': WX_MINIPROGRAM_APP_SECRET
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'access_token' in data:
            _access_token_cache['token'] = data['access_token']
            _access_token_cache['expires_at'] = now + data.get('expires_in', 7200)
            logging.info('获取微信access_token成功')
            return data['access_token']
        else:
            logging.error(f'获取access_token失败: {data}')
            return None
            
    except Exception as e:
        logging.error(f'获取access_token异常: {e}')
        return None


def send_subscribe_message(openid, template_type, data, page=None, retry=True, miniprogram_state=None):
    """
    发送订阅消息（带自动重试机制）
    
    参数:
        openid: 用户的openid
        template_type: 模板类型 ('ORDER_STATUS', 'NEW_MESSAGE', 'PRODUCT_SOLD')
        data: 消息数据字典，格式为 {key: value} 或 {key: {'value': value}}
        page: 点击消息跳转的小程序页面路径（可选）
        retry: 是否在token失效时自动重试（默认True）
        miniprogram_state: 小程序类型 ('developer'开发版, 'trial'体验版, 'formal'正式版)
    
    返回:
        dict: {'success': bool, 'error': str}
    """
    if not openid:
        return {'success': False, 'error': '用户openid为空'}
    
    template_id = TEMPLATE_IDS.get(template_type)
    if not template_id:
        return {'success': False, 'error': f'未知的模板类型: {template_type}'}
    
    access_token = get_access_token()
    if not access_token:
        return {'success': False, 'error': '无法获取access_token'}
    
    formatted_data = {}
    for key, value in data.items():
        if isinstance(value, dict) and 'value' in value:
            formatted_data[key] = value
        else:
            formatted_data[key] = {'value': str(value)}
    
    try:
        url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'
        
        state = miniprogram_state or MINIPROGRAM_STATE
        
        payload = {
            'touser': openid,
            'template_id': template_id,
            'data': formatted_data,
            'miniprogram_state': state
        }
        
        if page:
            payload['page'] = page
        
        logging.info(f'发送订阅消息: template={template_type}, state={state}, data={formatted_data}')
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        logging.info(f'微信订阅消息API响应: {result}')
        
        errcode = result.get('errcode', 0)
        
        if errcode == 0:
            logging.info(f'订阅消息发送成功: {template_type} -> {openid[:10]}...')
            return {'success': True}
        
        # access_token 无效或过期，尝试刷新后重试
        if errcode in (40001, 40014, 42001) and retry:
            logging.warning(f'access_token无效(errcode={errcode})，刷新后重试')
            clear_access_token_cache()
            return send_subscribe_message(openid, template_type, data, page, retry=False, miniprogram_state=state)
        
        error_msg = result.get('errmsg', '未知错误')
        
        # 用户未订阅消息（静默处理，不算错误）
        if errcode == 43101:
            logging.info(f'用户未订阅该消息: {template_type} (openid={openid[:10]}...)')
            return {'success': False, 'error': '用户未订阅该消息', 'errcode': errcode, 'silent': True}
        
        # 用户拒绝接收消息
        if errcode == 43104:
            logging.info(f'用户拒绝接收消息: {template_type}')
            return {'success': False, 'error': '用户拒绝接收消息', 'errcode': errcode, 'silent': True}
        
        logging.warning(f'订阅消息发送失败: {errcode} - {error_msg}')
        return {'success': False, 'error': error_msg, 'errcode': errcode}
                
    except requests.exceptions.Timeout:
        logging.error(f'发送订阅消息超时: {template_type}')
        return {'success': False, 'error': '请求超时'}
    except requests.exceptions.RequestException as e:
        logging.error(f'发送订阅消息网络异常: {e}')
        return {'success': False, 'error': f'网络异常: {str(e)}'}
    except Exception as e:
        logging.error(f'发送订阅消息异常: {e}')
        return {'success': False, 'error': str(e)}


def send_order_status_notification(openid, order_number, product_name, status_text, remark='请查看订单详情', page=None):
    """
    发送订单状态变更通知
    
    参数:
        openid: 用户openid
        order_number: 订单编号
        product_name: 商品名称
        status_text: 状态文本（如"待处理"、"已发货"、"已完成"）- 最多5个汉字
        remark: 备注信息（最多20个字符）
        page: 跳转页面
    
    模板字段:
        character_string2: 订单编号
        thing7: 备注
        phrase10: 订单状态
        thing11: 商品名称
    """
    data = {
        'character_string2': str(order_number)[:32],
        'thing7': remark[:20] if len(remark) > 20 else remark,
        'phrase10': status_text[:5] if len(status_text) > 5 else status_text,
        'thing11': product_name[:20] if len(product_name) > 20 else product_name
    }
    
    return send_subscribe_message(openid, 'ORDER_STATUS', data, page)


def send_new_message_notification(openid, sender_name, reminder_text, send_time, page=None):
    """
    发送新消息提醒
    
    参数:
        openid: 用户openid
        sender_name: 发送者名称（房号）
        reminder_text: 温馨提示（如"请点击查看详情查阅消息内容"）
        send_time: 发送时间
        page: 跳转页面
    
    模板字段:
        thing2: 发送人
        thing3: 温馨提示
        time1: 发送时间
    """
    # 限制 thing 字段：20个以内字符，不能包含换行，不能包含空格
    sender_clean = str(sender_name).replace(' ', '').replace('\n', '').replace('\r', '')[:20]
    reminder_clean = str(reminder_text).replace(' ', '').replace('\n', '').replace('\r', '')[:20]
    
    # 限制 time 字段：格式化时间，如 2023-12-25 14:30
    try:
        if isinstance(send_time, str):
            # 尝试统一格式
            time_str = send_time.replace('年', '-').replace('月', '-').replace('日', '')
            if len(time_str) > 16:
                time_str = time_str[:16]
        else:
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    except:
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    data = {
        'thing2': sender_clean if sender_clean else '邻居',
        'thing3': reminder_clean if reminder_clean else '您有新消息',
        'time1': time_str
    }
    
    logging.info(f'[NEW_MESSAGE] 发送数据: openid={openid[:10]}..., data={data}')
    return send_subscribe_message(openid, 'NEW_MESSAGE', data, page)


def send_product_sold_notification(openid, product_name, buyer_name, sold_time, reminder_text='您的商品已售出', page=None):
    """
    发送商品售出通知
    
    参数:
        openid: 用户openid
        product_name: 商品名称
        buyer_name: 买家名称（房号）
        sold_time: 售出时间
        reminder_text: 温馨提示
        page: 跳转页面
    
    模板字段:
        thing2: 物品名称
        thing3: 买家
        time5: 拍下时间
        thing6: 温馨提示
    """
    # 限制 thing 字段：20个以内字符，不能包含换行，不能包含空格
    product_clean = str(product_name).replace(' ', '').replace('\n', '').replace('\r', '')[:20]
    buyer_clean = str(buyer_name).replace(' ', '').replace('\n', '').replace('\r', '')[:20]
    reminder_clean = str(reminder_text).replace(' ', '').replace('\n', '').replace('\r', '')[:20]
    
    # 限制 time 字段：格式化时间
    try:
        if isinstance(sold_time, str):
            time_str = sold_time.replace('年', '-').replace('月', '-').replace('日', '')
            if len(time_str) > 16:
                time_str = time_str[:16]
        else:
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    except:
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    data = {
        'thing2': product_clean if product_clean else '商品',
        'thing3': buyer_clean if buyer_clean else '买家',
        'time5': time_str,
        'thing6': reminder_clean if reminder_clean else '请及时处理'
    }
    
    logging.info(f'[PRODUCT_SOLD] 发送数据: openid={openid[:10]}..., data={data}')
    return send_subscribe_message(openid, 'PRODUCT_SOLD', data, page)


def get_beijing_time_str():
    """获取北京时间字符串"""
    china_tz = timezone(timedelta(hours=8))
    now = datetime.now(china_tz)
    return now.strftime('%Y-%m-%d %H:%M')
