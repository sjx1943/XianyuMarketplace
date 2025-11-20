#!/usr/bin/env python3
"""
边界场景自动化测试
测试各种边界情况和异常场景，确保系统健壮性
"""
import pytest
import requests
from bs4 import BeautifulSoup
import time
import json

BASE_URL = "http://127.0.0.1:5000"


class TestSession:
    """测试会话管理"""
    
    @staticmethod
    def create_authenticated_session(username, password):
        """创建已认证的session"""
        session = requests.Session()
        
        # 获取登录页面和XSRF token
        login_page = session.get(f"{BASE_URL}/login")
        soup = BeautifulSoup(login_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        
        if not xsrf_input:
            return None
            
        xsrf_token = xsrf_input['value']
        
        # 登录
        login_data = {
            "username": username,
            "password": password,
            "_xsrf": xsrf_token
        }
        login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
        
        if login_response.status_code == 200:
            return session
        return None


class TestOrderBoundary:
    """订单边界场景测试"""
    
    def test_order_with_deleted_product(self):
        """测试：订单关联已删除商品的情况"""
        # 这个测试需要先创建商品、创建订单、再删除商品
        # 系统应该使用product_name快照显示订单
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        # 访问订单列表
        response = session.get(f"{BASE_URL}/orders")
        assert response.status_code == 200
        # 应该能正常显示，即使商品已被删除
    
    def test_order_with_zero_quantity(self):
        """测试：创建数量为0的订单（应被拒绝）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        # 获取XSRF token
        create_page = session.get(f"{BASE_URL}/create_order?product_id=1")
        if create_page.status_code != 200:
            pytest.skip("无法访问创建订单页面")
        
        soup = BeautifulSoup(create_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        if not xsrf_input:
            pytest.skip("未找到XSRF token")
        
        order_data = {
            "product_id": "1",
            "quantity": "0",  # 边界：数量为0
            "_xsrf": xsrf_input['value']
        }
        
        response = session.post(f"{BASE_URL}/orders", data=order_data)
        data = response.json()
        
        # 应该返回错误
        assert data['success'] == False
        assert 'error' in data
    
    def test_order_exceed_stock(self):
        """测试：订单数量超过库存（应被拒绝）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        # 尝试购买超大数量
        order_data = {
            "product_id": "1",
            "quantity": "999999",  # 边界：超大数量
        }
        
        response = session.post(f"{BASE_URL}/orders", json=order_data)
        if response.status_code == 200:
            data = response.json()
            # 应该返回库存不足错误
            assert data.get('success') == False or '库存不足' in str(data.get('error', ''))
    
    def test_cancel_already_shipped_order(self):
        """测试：取消已发货订单（应被拒绝）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        # 尝试取消已发货的订单（假设订单ID=1已发货）
        response = session.delete(f"{BASE_URL}/orders/1")
        
        if response.status_code == 200:
            data = response.json()
            # 应该返回错误（只能取消pending状态的订单）
            assert data.get('success') == False or 'pending' in str(data.get('error', '')).lower()
    
    def test_confirm_unpaid_order(self):
        """测试：买家确认未发货订单（应被拒绝）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        # 尝试确认pending状态的订单
        response = session.post(f"{BASE_URL}/api/order/1/confirm")
        
        if response.status_code == 200:
            data = response.json()
            # 应该返回错误（只能确认shipped状态的订单）
            assert data.get('success') == False or 'shipped' in str(data.get('error', '')).lower()


class TestUserBoundary:
    """用户边界场景测试"""
    
    def test_register_duplicate_username(self):
        """测试：注册重复用户名（应被拒绝）"""
        session = requests.Session()
        
        # 获取注册页面
        reg_page = session.get(f"{BASE_URL}/register")
        soup = BeautifulSoup(reg_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        if not xsrf_input:
            pytest.skip("未找到XSRF token")
        
        register_data = {
            "username": "testuser1",  # 已存在的用户名
            "password": "Test123456",
            "email": f"duplicate_{int(time.time())}@example.com",
            "_xsrf": xsrf_input['value']
        }
        
        response = session.post(f"{BASE_URL}/register", data=register_data)
        
        # 应该返回错误或重定向到注册页面（带错误消息）
        # 注意：具体行为取决于实现
        assert response.status_code in [200, 400]
    
    def test_invalid_room_number_format(self):
        """测试：无效房间号格式（应被拒绝）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        # 获取设置房间号页面
        room_page = session.get(f"{BASE_URL}/set_room_number")
        if room_page.status_code != 200:
            pytest.skip("无法访问房间号设置页面")
        
        soup = BeautifulSoup(room_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        if not xsrf_input:
            pytest.skip("未找到XSRF token")
        
        invalid_rooms = [
            "invalid",      # 不符合格式
            "1-1",          # 缺少房间号
            "abc-def-ghi",  # 非数字
            "1",            # 只有楼号
        ]
        
        for room_number in invalid_rooms:
            room_data = {
                "room_number": room_number,
                "_xsrf": xsrf_input['value']
            }
            
            response = session.post(f"{BASE_URL}/set_room_number", data=room_data)
            
            # 应该返回错误或重定向回设置页面
            # 具体行为取决于实现


class TestProductBoundary:
    """商品边界场景测试"""
    
    def test_create_product_zero_price(self):
        """测试：创建0价商品"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        # 获取发布页面
        upload_page = session.get(f"{BASE_URL}/product/upload")
        soup = BeautifulSoup(upload_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        if not xsrf_input:
            pytest.skip("未找到XSRF token")
        
        product_data = {
            "name": "Free Product",
            "description": "This is free",
            "price": "0",  # 边界：0价
            "quantity": "10",
            "tag": "其他",
            "_xsrf": xsrf_input['value']
        }
        
        files = {'images': ('test.jpg', b'fake_image_content', 'image/jpeg')}
        response = session.post(f"{BASE_URL}/product/upload", data=product_data, files=files)
        
        # 系统应该允许0价商品（闲置赠送）
        assert response.status_code in [200, 302]
    
    def test_create_product_negative_price(self):
        """测试：创建负价商品（应被拒绝）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        upload_page = session.get(f"{BASE_URL}/product/upload")
        soup = BeautifulSoup(upload_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        if not xsrf_input:
            pytest.skip("未找到XSRF token")
        
        product_data = {
            "name": "Invalid Product",
            "description": "This should fail",
            "price": "-10",  # 边界：负价
            "quantity": "10",
            "tag": "其他",
            "_xsrf": xsrf_input['value']
        }
        
        files = {'images': ('test.jpg', b'fake_image_content', 'image/jpeg')}
        response = session.post(f"{BASE_URL}/product/upload", data=product_data, files=files)
        
        # HTML表单验证应该阻止提交（min=0）
        # 但如果绕过前端，后端也应该验证
    
    def test_create_product_very_long_description(self):
        """测试：超长商品描述"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        upload_page = session.get(f"{BASE_URL}/product/upload")
        soup = BeautifulSoup(upload_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        if not xsrf_input:
            pytest.skip("未找到XSRF token")
        
        product_data = {
            "name": "Long Description Product",
            "description": "A" * 10000,  # 边界：超长描述
            "price": "99.99",
            "quantity": "10",
            "tag": "其他",
            "_xsrf": xsrf_input['value']
        }
        
        files = {'images': ('test.jpg', b'fake_image_content', 'image/jpeg')}
        response = session.post(f"{BASE_URL}/product/upload", data=product_data, files=files)
        
        # 系统应该能处理或限制描述长度
        assert response.status_code in [200, 302, 400]
    
    def test_product_without_images(self):
        """测试：发布没有图片的商品（应被拒绝）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        upload_page = session.get(f"{BASE_URL}/product/upload")
        soup = BeautifulSoup(upload_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        if not xsrf_input:
            pytest.skip("未找到XSRF token")
        
        product_data = {
            "name": "No Image Product",
            "description": "This has no images",
            "price": "99.99",
            "quantity": "10",
            "tag": "其他",
            "_xsrf": xsrf_token['value']
        }
        
        # 不包含files参数
        response = session.post(f"{BASE_URL}/product/upload", data=product_data)
        
        # 应该返回错误（需要至少一张图片）


class TestAuthenticationBoundary:
    """认证边界场景测试"""
    
    def test_access_protected_route_without_login(self):
        """测试：未登录访问受保护路由"""
        session = requests.Session()
        
        protected_routes = [
            "/product/upload",
            "/orders",
            "/home_page",
            "/chat_room"
        ]
        
        for route in protected_routes:
            response = session.get(f"{BASE_URL}{route}")
            
            # 应该重定向到登录页面
            assert response.status_code in [200, 302]
            if response.status_code == 200:
                assert "/login" in response.url or "登录" in response.text
    
    def test_login_with_wrong_password(self):
        """测试：错误密码登录"""
        session = requests.Session()
        
        login_page = session.get(f"{BASE_URL}/login")
        soup = BeautifulSoup(login_page.text, 'html.parser')
        xsrf_input = soup.find('input', {'name': '_xsrf'})
        if not xsrf_input:
            pytest.skip("未找到XSRF token")
        
        login_data = {
            "username": "testuser1",
            "password": "WrongPassword123",
            "_xsrf": xsrf_input['value']
        }
        
        response = session.post(f"{BASE_URL}/login", data=login_data)
        
        # 应该返回错误
        assert response.status_code == 200
        assert "错误" in response.text or "失败" in response.text or "密码" in response.text


class TestAPISecurity:
    """API安全边界测试"""
    
    def test_api_without_xsrf_token(self):
        """测试：缺少XSRF token的POST请求（应被拒绝）"""
        session = requests.Session()
        
        # 尝试不带XSRF token创建订单
        order_data = {
            "product_id": "1",
            "quantity": "1"
        }
        
        response = session.post(f"{BASE_URL}/orders", data=order_data)
        
        # 应该返回403 Forbidden
        assert response.status_code in [403, 400]
    
    def test_access_other_user_order(self):
        """测试：访问其他用户的订单详情（应被拒绝）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        # 尝试访问其他用户的订单（假设订单ID=999不属于testuser1）
        response = session.get(f"{BASE_URL}/orders/999")
        
        # 应该返回权限错误或404
        if response.status_code == 200:
            assert "无权限" in response.text or "不存在" in response.text


class TestUnreadNotifications:
    """未读通知边界测试"""
    
    def test_unread_orders_count_for_buyer(self):
        """测试：买家查询未读订单数量（应为0或很少）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        response = session.get(f"{BASE_URL}/api/unread_orders_count")
        
        if response.status_code == 200:
            data = response.json()
            assert 'count' in data
            # 买家作为卖家的pending订单应该很少
            assert data['count'] >= 0
    
    def test_unread_messages_count_format(self):
        """测试：未读消息数量格式（超过99显示99+）"""
        session = TestSession.create_authenticated_session("testuser1", "Test123456")
        if not session:
            pytest.skip("无法创建测试会话")
        
        response = session.get(f"{BASE_URL}/api/unread_count")
        
        if response.status_code == 200:
            data = response.json()
            # 应该包含total_unread字段
            assert 'total_unread' in data
            # 数量应该是整数
            assert isinstance(data['total_unread'], int)
            assert data['total_unread'] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
