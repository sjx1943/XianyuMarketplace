#!/usr/bin/env python3
"""
管理员功能端到端测试脚本
测试所有管理员功能，包括登录、Dashboard、用户/商品/订单管理
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000"

# 测试结果记录
test_results = []

def log_test(name, passed, message=""):
    """记录测试结果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({
        "name": name,
        "passed": passed,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    print(f"{status} - {name}")
    if message:
        print(f"    {message}")

def test_admin_login():
    """测试1: 管理员登录"""
    print("\n=== 测试1: 管理员登录 ===")
    
    # 1.1 错误的密码
    response = requests.post(f"{BASE_URL}/admin/login", 
                            json={"username": "admin", "password": "wrongpassword"},
                            headers={"Content-Type": "application/json"})
    data = response.json()
    log_test("1.1 错误密码应拒绝", 
             not data.get('success'), 
             f"响应: {data}")
    
    # 1.2 正确的密码
    response = requests.post(f"{BASE_URL}/admin/login",
                            json={"username": "admin", "password": "Zpepc001@"},
                            headers={"Content-Type": "application/json"})
    data = response.json()
    log_test("1.2 正确密码应成功", 
             data.get('success') == True,
             f"响应: {data}")
    
    # 保存cookies for后续测试
    if data.get('success'):
        return response.cookies
    return None

def test_dashboard(cookies):
    """测试2: Dashboard统计"""
    print("\n=== 测试2: Dashboard统计 ===")
    
    response = requests.get(f"{BASE_URL}/admin/dashboard", cookies=cookies)
    log_test("2.1 Dashboard访问", 
             response.status_code == 200,
             f"状态码: {response.status_code}")
    
    # 检查页面包含统计数据
    content = response.text
    has_stats = all(key in content for key in ['总用户', '总商品', '总订单'])
    log_test("2.2 Dashboard包含统计数据", 
             has_stats,
             f"页面长度: {len(content)} bytes")

def test_user_management(cookies):
    """测试3: 用户管理"""
    print("\n=== 测试3: 用户管理 ===")
    
    # 3.1 访问用户列表
    response = requests.get(f"{BASE_URL}/admin/users", cookies=cookies)
    log_test("3.1 用户列表访问", 
             response.status_code == 200,
             f"状态码: {response.status_code}")
    
    # 3.2 分页测试
    response = requests.get(f"{BASE_URL}/admin/users?page=1", cookies=cookies)
    log_test("3.2 用户列表分页", 
             response.status_code == 200 and '分页' in response.text or 'page' in response.text.lower(),
             f"状态码: {response.status_code}")

def test_product_management(cookies):
    """测试4: 商品管理"""
    print("\n=== 测试4: 商品管理 ===")
    
    # 4.1 访问商品列表
    response = requests.get(f"{BASE_URL}/admin/products", cookies=cookies)
    log_test("4.1 商品列表访问", 
             response.status_code == 200,
             f"状态码: {response.status_code}")
    
    # 4.2 状态筛选 - 在售
    response = requests.get(f"{BASE_URL}/admin/products?status=在售", cookies=cookies)
    log_test("4.2 商品状态筛选(在售)", 
             response.status_code == 200,
             f"状态码: {response.status_code}")
    
    # 4.3 状态筛选 - 全部
    response = requests.get(f"{BASE_URL}/admin/products?status=all", cookies=cookies)
    log_test("4.3 商品状态筛选(全部)", 
             response.status_code == 200,
             f"状态码: {response.status_code}")

def test_order_management(cookies):
    """测试5: 订单管理"""
    print("\n=== 测试5: 订单管理 ===")
    
    # 5.1 访问订单列表
    response = requests.get(f"{BASE_URL}/admin/orders", cookies=cookies)
    log_test("5.1 订单列表访问", 
             response.status_code == 200,
             f"状态码: {response.status_code}")
    
    # 5.2 状态筛选
    response = requests.get(f"{BASE_URL}/admin/orders?status=completed", cookies=cookies)
    log_test("5.2 订单状态筛选(completed)", 
             response.status_code == 200,
             f"状态码: {response.status_code}")

def test_unauthorized_access():
    """测试6: 未授权访问"""
    print("\n=== 测试6: 未授权访问 ===")
    
    # 6.1 无cookies访问Dashboard应重定向
    response = requests.get(f"{BASE_URL}/admin/dashboard", allow_redirects=False)
    log_test("6.1 未登录访问Dashboard应重定向", 
             response.status_code in [301, 302, 303],
             f"状态码: {response.status_code}, Location: {response.headers.get('Location')}")
    
    # 6.2 无cookies访问用户管理应重定向
    response = requests.get(f"{BASE_URL}/admin/users", allow_redirects=False)
    log_test("6.2 未登录访问用户管理应重定向", 
             response.status_code in [301, 302, 303],
             f"状态码: {response.status_code}")

def main():
    """主测试流程"""
    print("=" * 60)
    print("管理员功能端到端测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 测试6: 未授权访问（先测试，不需要cookies）
        test_unauthorized_access()
        
        # 测试1: 登录
        cookies = test_admin_login()
        if not cookies:
            print("\n❌ 登录失败，无法继续后续测试")
            return False
        
        # 测试2-5: 需要登录状态
        test_dashboard(cookies)
        test_user_management(cookies)
        test_product_management(cookies)
        test_order_management(cookies)
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 无法连接到服务器: {BASE_URL}")
        print("请确保服务器正在运行")
        return False
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for t in test_results if t['passed'])
    total = len(test_results)
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {pass_rate:.1f}%")
    
    # 保存详细结果到JSON
    with open("test_results.json", "w", encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": pass_rate
            },
            "tests": test_results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细结果已保存到: test_results.json")
    
    return pass_rate == 100.0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
