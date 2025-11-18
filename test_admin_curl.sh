#!/bin/bash

# 管理员功能端到端测试脚本（使用curl）
BASE_URL="http://localhost:5000"
COOKIE_FILE="/tmp/admin_cookies.txt"
rm -f $COOKIE_FILE

echo "=========================================="
echo "管理员功能端到端测试"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 测试计数器
TOTAL=0
PASSED=0

test_result() {
    TOTAL=$((TOTAL + 1))
    if [ $1 -eq 0 ]; then
        PASSED=$((PASSED + 1))
        echo "✅ PASS - $2"
    else
        echo "❌ FAIL - $2"
    fi
    [ -n "$3" ] && echo "    $3"
}

echo -e "\n=== 测试1: 管理员登录 ==="

# 1.1 错误密码
echo "1.1 测试错误密码..."
RESPONSE=$(curl -s -X POST "$BASE_URL/admin/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrongpassword"}')
echo "响应: $RESPONSE"
echo "$RESPONSE" | grep -q '"success".*false' && test_result 0 "错误密码应拒绝" || test_result 1 "错误密码应拒绝" "响应: $RESPONSE"

# 1.2 正确密码
echo -e "\n1.2 测试正确密码..."
RESPONSE=$(curl -s -c $COOKIE_FILE -X POST "$BASE_URL/admin/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"Zpepc001@"}')
echo "响应: $RESPONSE"
echo "$RESPONSE" | grep -q '"success".*true' && test_result 0 "正确密码应成功" || test_result 1 "正确密码应成功" "响应: $RESPONSE"

# 检查cookies是否设置
if [ -f $COOKIE_FILE ] && grep -q "user_id" $COOKIE_FILE; then
    test_result 0 "登录应设置cookies"
    echo "Cookies内容:"
    cat $COOKIE_FILE | grep -v "^#"
else
    test_result 1 "登录应设置cookies" "Cookie文件不存在或为空"
    echo "❌ 无法继续测试，退出"
    exit 1
fi

echo -e "\n=== 测试2: Dashboard统计 ==="

# 2.1 访问Dashboard
echo "2.1 访问Dashboard..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/dashboard.html -w "%{http_code}" "$BASE_URL/admin/dashboard")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "Dashboard访问" "HTTP状态码: $HTTP_CODE"

# 2.2 检查统计数据
if [ -f /tmp/dashboard.html ]; then
    grep -q "总用户" /tmp/dashboard.html && grep -q "总商品" /tmp/dashboard.html && grep -q "总订单" /tmp/dashboard.html
    test_result $? "Dashboard包含统计数据" "页面大小: $(wc -c < /tmp/dashboard.html) bytes"
fi

echo -e "\n=== 测试3: 用户管理 ==="

# 3.1 访问用户列表
echo "3.1 访问用户列表..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/users.html -w "%{http_code}" "$BASE_URL/admin/users")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "用户列表访问" "HTTP状态码: $HTTP_CODE"

# 3.2 分页测试
echo "3.2 测试分页..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/users?page=1")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "用户列表分页" "HTTP状态码: $HTTP_CODE"

echo -e "\n=== 测试4: 商品管理 ==="

# 4.1 访问商品列表
echo "4.1 访问商品列表..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/products.html -w "%{http_code}" "$BASE_URL/admin/products")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "商品列表访问" "HTTP状态码: $HTTP_CODE"

# 4.2 状态筛选 - 在售
echo "4.2 状态筛选(在售)..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/products?status=在售")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "商品状态筛选(在售)" "HTTP状态码: $HTTP_CODE"

# 4.3 状态筛选 - 全部
echo "4.3 状态筛选(全部)..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/products?status=all")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "商品状态筛选(全部)" "HTTP状态码: $HTTP_CODE"

echo -e "\n=== 测试5: 订单管理 ==="

# 5.1 访问订单列表
echo "5.1 访问订单列表..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/orders.html -w "%{http_code}" "$BASE_URL/admin/orders")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "订单列表访问" "HTTP状态码: $HTTP_CODE"

# 5.2 状态筛选
echo "5.2 状态筛选(completed)..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/orders?status=completed")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "订单状态筛选(completed)" "HTTP状态码: $HTTP_CODE"

echo -e "\n=== 测试6: 未授权访问 ==="

# 6.1 无cookies访问Dashboard
echo "6.1 未登录访问Dashboard..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/admin/dashboard")
test_result $([ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "303" ] && echo 0 || echo 1) "未登录应重定向" "HTTP状态码: $HTTP_CODE"

# 6.2 无cookies访问用户管理
echo "6.2 未登录访问用户管理..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/admin/users")
test_result $([ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "303" ] && echo 0 || echo 1) "未登录应重定向" "HTTP状态码: $HTTP_CODE"

# 汇总结果
echo -e "\n=========================================="
echo "测试结果汇总"
echo "=========================================="
echo "总测试数: $TOTAL"
echo "通过: $PASSED"
echo "失败: $((TOTAL - PASSED))"
PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")
echo "通过率: $PASS_RATE%"

# 保存结果
cat > test_results_curl.txt << RESULTS
========================================
管理员功能测试结果
时间: $(date '+%Y-%m-%d %H:%M:%S')
========================================

总测试数: $TOTAL
通过: $PASSED
失败: $((TOTAL - PASSED))
通过率: $PASS_RATE%

详细日志已保存到:
- Dashboard: /tmp/dashboard.html
- 用户列表: /tmp/users.html
- 商品列表: /tmp/products.html
- 订单列表: /tmp/orders.html
- Cookies: $COOKIE_FILE
RESULTS

echo -e "\n测试结果已保存到: test_results_curl.txt"

# 清理
rm -f $COOKIE_FILE

# 返回退出码
[ $PASSED -eq $TOTAL ] && exit 0 || exit 1
