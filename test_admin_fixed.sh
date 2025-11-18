#!/bin/bash

# 管理员功能端到端测试（修复版）
BASE_URL="http://localhost:5000"
COOKIE_FILE="/tmp/admin_cookies.txt"
rm -f $COOKIE_FILE

echo "=========================================="
echo "管理员功能端到端测试（修复版）"
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

echo -e "\n=== 测试1: XSRF保护验证 ==="

# 1.1 无XSRF token登录应失败
echo "1.1 测试无XSRF token登录..."
HTTP_CODE=$(curl -s -o /tmp/no_xsrf_response.txt -w "%{http_code}" -X POST "$BASE_URL/admin/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"Zpepc001@"}')
RESPONSE=$(cat /tmp/no_xsrf_response.txt)
echo "HTTP状态码: $HTTP_CODE"
echo "响应内容: $RESPONSE"
# Tornado返回403错误
if [ "$HTTP_CODE" = "403" ] || echo "$RESPONSE" | grep -qi "xsrf\|forbidden"; then
    test_result 0 "无XSRF token应返回403/错误" "HTTP $HTTP_CODE"
else
    test_result 1 "无XSRF token应返回403/错误" "HTTP $HTTP_CODE - 未正确拒绝"
fi

echo -e "\n=== 测试2: 管理员登录 ==="

# 2.1 获取XSRF token
echo "2.1 获取XSRF token..."
curl -s -c $COOKIE_FILE "$BASE_URL/admin/login" > /tmp/login_page.html
if [ -f $COOKIE_FILE ] && grep -q "_xsrf" $COOKIE_FILE; then
    XSRF_TOKEN=$(grep "_xsrf" $COOKIE_FILE | awk '{print $7}')
    test_result 0 "获取XSRF token成功" "Token: ${XSRF_TOKEN:0:20}..."
else
    test_result 1 "获取XSRF token失败"
    echo "❌ 无法继续测试，退出"
    exit 1
fi

# 2.2 错误密码
echo -e "\n2.2 测试错误密码..."
RESPONSE=$(curl -s -b $COOKIE_FILE -X POST "$BASE_URL/admin/login" \
    -H "Content-Type: application/json" \
    -H "X-Xsrftoken: $XSRF_TOKEN" \
    -d "{\"username\":\"admin\",\"password\":\"wrongpassword\",\"_xsrf\":\"$XSRF_TOKEN\"}")
echo "响应: $RESPONSE"
echo "$RESPONSE" | grep -q '"success".*false' && test_result 0 "错误密码应拒绝" || test_result 1 "错误密码应拒绝"

# 2.3 正确密码
echo -e "\n2.3 测试正确密码..."
RESPONSE=$(curl -s -b $COOKIE_FILE -c $COOKIE_FILE -X POST "$BASE_URL/admin/login" \
    -H "Content-Type: application/json" \
    -H "X-Xsrftoken: $XSRF_TOKEN" \
    -d "{\"username\":\"admin\",\"password\":\"Zpepc001@\",\"_xsrf\":\"$XSRF_TOKEN\"}")
echo "响应: $RESPONSE"
echo "$RESPONSE" | grep -q '"success".*true' && test_result 0 "正确密码应成功登录" || test_result 1 "正确密码应成功登录"

# 2.4 检查登录后的cookies
if [ -f $COOKIE_FILE ] && grep -q "user_id" $COOKIE_FILE; then
    test_result 0 "登录应设置user_id cookie"
else
    test_result 1 "登录应设置user_id cookie"
    echo "❌ 无法继续测试，退出"
    exit 1
fi

echo -e "\n=== 测试3: Dashboard统计 ==="

# 3.1 访问Dashboard
echo "3.1 访问Dashboard..."
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/dashboard.html -w "%{http_code}" "$BASE_URL/admin/dashboard")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "Dashboard访问" "HTTP状态码: $HTTP_CODE"

# 3.2 检查统计数据
if [ -f /tmp/dashboard.html ] && [ "$HTTP_CODE" = "200" ]; then
    grep -q "总用户" /tmp/dashboard.html && grep -q "总商品" /tmp/dashboard.html
    test_result $? "Dashboard包含统计数据" "页面大小: $(wc -c < /tmp/dashboard.html) bytes"
fi

echo -e "\n=== 测试4: 用户管理 ==="

# 4.1 访问用户列表
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/users.html -w "%{http_code}" "$BASE_URL/admin/users")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "用户列表访问" "HTTP状态码: $HTTP_CODE"

# 4.2 分页测试
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/users?page=1")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "用户列表分页(page=1)" "HTTP状态码: $HTTP_CODE"

# 4.3 分页边界测试
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/users?page=999")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "分页边界处理(page=999)" "HTTP状态码: $HTTP_CODE"

echo -e "\n=== 测试5: 商品管理 ==="

# 5.1 访问商品列表
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/products.html -w "%{http_code}" "$BASE_URL/admin/products")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "商品列表访问" "HTTP状态码: $HTTP_CODE"

# 5.2-5.4 状态筛选
for status in "在售" "all" "已售完"; do
    HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/products?status=$status")
    test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "商品状态筛选($status)" "HTTP状态码: $HTTP_CODE"
done

echo -e "\n=== 测试6: 订单管理 ==="

# 6.1 访问订单列表
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/orders.html -w "%{http_code}" "$BASE_URL/admin/orders")
test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "订单列表访问" "HTTP状态码: $HTTP_CODE"

# 6.2-6.3 状态筛选
for status in "completed" "pending"; do
    HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/orders?status=$status")
    test_result $([ "$HTTP_CODE" = "200" ] && echo 0 || echo 1) "订单状态筛选($status)" "HTTP状态码: $HTTP_CODE"
done

echo -e "\n=== 测试7: 未授权访问保护 ==="

# 7.1-7.2 无cookies访问
for endpoint in "dashboard" "users"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/admin/$endpoint")
    test_result $([ "$HTTP_CODE" = "302" ] && echo 0 || echo 1) "未登录访问$endpoint应重定向" "HTTP状态码: $HTTP_CODE"
done

# 汇总结果
echo -e "\n=========================================="
echo "测试结果汇总"
echo "=========================================="
echo "总测试数: $TOTAL"
echo "通过: $PASSED"
echo "失败: $((TOTAL - PASSED))"
if [ $TOTAL -gt 0 ]; then
    PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")
else
    PASS_RATE="0.0"
fi
echo "通过率: $PASS_RATE%"

# 保存结果
cat > test_results_final.txt << RESULTS
========================================
管理员功能端到端测试结果（最终版）
时间: $(date '+%Y-%m-%d %H:%M:%S')
========================================

总测试数: $TOTAL
通过: $PASSED
失败: $((TOTAL - PASSED))
通过率: $PASS_RATE%

测试覆盖:
✓ XSRF保护（无token拒绝）
✓ 管理员登录（错误/正确密码）
✓ Dashboard统计数据
✓ 用户管理（列表、分页、边界）
✓ 商品管理（列表、状态筛选）
✓ 订单管理（列表、状态筛选）
✓ 未授权访问保护

未测试（需手动或代码审查）:
- POST操作（toggle/delete/restore）
RESULTS

echo -e "\n测试结果已保存到: test_results_final.txt"

# 清理
rm -f $COOKIE_FILE

# 返回退出码
[ $PASSED -eq $TOTAL ] && exit 0 || exit 1
