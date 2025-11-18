#!/bin/bash
set -e  # Exit on error

BASE_URL="http://localhost:5000"
COOKIE_FILE="/tmp/admin_cookies.txt"
rm -f $COOKIE_FILE

echo "管理员功能端到端测试（最终版）"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

TOTAL=0
PASSED=0

pass_test() {
    TOTAL=$((TOTAL + 1))
    PASSED=$((PASSED + 1))
    echo "✅ PASS - $1"
}

fail_test() {
    TOTAL=$((TOTAL + 1))
    echo "❌ FAIL - $1"
    [ -n "$2" ] && echo "    理由: $2"
}

# 测试1: XSRF保护
echo -e "\n=== 测试1: XSRF保护 ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/admin/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"test"}')
if [ "$HTTP_CODE" = "403" ]; then
    pass_test "无XSRF token返回403"
else
    fail_test "无XSRF token返回403" "实际: $HTTP_CODE"
fi

# 测试2: 获取XSRF token
echo -e "\n=== 测试2: 获取XSRF token ==="
curl -s -c $COOKIE_FILE "$BASE_URL/admin/login" > /tmp/login_page.html
if grep -q "_xsrf" $COOKIE_FILE; then
    XSRF_TOKEN=$(grep "_xsrf" $COOKIE_FILE | awk '{print $7}')
    pass_test "获取XSRF token成功"
else
    fail_test "获取XSRF token" && exit 1
fi

# 测试3: 错误密码
echo -e "\n=== 测试3: 错误密码登录 ==="
RESP=$(curl -s -b $COOKIE_FILE -X POST "$BASE_URL/admin/login" \
    -H "Content-Type: application/json" \
    -H "X-Xsrftoken: $XSRF_TOKEN" \
    -d "{\"username\":\"admin\",\"password\":\"wrong\",\"_xsrf\":\"$XSRF_TOKEN\"}")
if echo "$RESP" | grep -q '"success".*false'; then
    pass_test "错误密码被拒绝"
else
    fail_test "错误密码被拒绝" "响应: $RESP"
fi

# 测试4: 正确密码
echo -e "\n=== 测试4: 正确密码登录 ==="
RESP=$(curl -s -b $COOKIE_FILE -c $COOKIE_FILE -X POST "$BASE_URL/admin/login" \
    -H "Content-Type: application/json" \
    -H "X-Xsrftoken: $XSRF_TOKEN" \
    -d "{\"username\":\"admin\",\"password\":\"Zpepc001@\",\"_xsrf\":\"$XSRF_TOKEN\"}")
if echo "$RESP" | grep -q '"success".*true'; then
    pass_test "正确密码登录成功"
else
    fail_test "正确密码登录成功" "响应: $RESP"
fi

# 测试5: Cookies设置
if grep -q "user_id" $COOKIE_FILE; then
    pass_test "登录设置user_id cookie"
else
    fail_test "登录设置user_id cookie" && exit 1
fi

# 测试6-8: Dashboard
echo -e "\n=== 测试6-8: Dashboard ==="
HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /tmp/dashboard.html -w "%{http_code}" "$BASE_URL/admin/dashboard")
[ "$HTTP_CODE" = "200" ] && pass_test "Dashboard访问(200)" || fail_test "Dashboard访问" "$HTTP_CODE"

if grep -q "总用户" /tmp/dashboard.html; then
    pass_test "Dashboard包含统计数据"
else
    fail_test "Dashboard包含统计数据"
fi

# 测试9-11: 用户管理
echo -e "\n=== 测试9-11: 用户管理 ==="
for test in "列表访问:users" "分页:users?page=1" "边界:users?page=999"; do
    name=$(echo $test | cut -d: -f1)
    url=$(echo $test | cut -d: -f2)
    HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/$url")
    [ "$HTTP_CODE" = "200" ] && pass_test "用户管理$name" || fail_test "用户管理$name" "$HTTP_CODE"
done

# 测试12-15: 商品管理
echo -e "\n=== 测试12-15: 商品管理 ==="
for status in "列表:products" "在售:products?status=在售" "全部:products?status=all" "已售完:products?status=已售完"; do
    name=$(echo $status | cut -d: -f1)
    url=$(echo $status | cut -d: -f2)
    HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/$url")
    [ "$HTTP_CODE" = "200" ] && pass_test "商品管理$name" || fail_test "商品管理$name" "$HTTP_CODE"
done

# 测试16-18: 订单管理
echo -e "\n=== 测试16-18: 订单管理 ==="
for status in "列表:orders" "completed:orders?status=completed" "pending:orders?status=pending"; do
    name=$(echo $status | cut -d: -f1)
    url=$(echo $status | cut -d: -f2)
    HTTP_CODE=$(curl -s -b $COOKIE_FILE -o /dev/null -w "%{http_code}" "$BASE_URL/admin/$url")
    [ "$HTTP_CODE" = "200" ] && pass_test "订单管理$name" || fail_test "订单管理$name" "$HTTP_CODE"
done

# 测试19-20: 未授权访问
echo -e "\n=== 测试19-20: 未授权访问 ==="
for endpoint in "dashboard" "users"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/admin/$endpoint")
    [ "$HTTP_CODE" = "302" ] && pass_test "未登录访问$endpoint重定向" || fail_test "未登录访问$endpoint重定向" "$HTTP_CODE"
done

# 汇总
echo -e "\n=========================================="
echo "测试结果汇总"
echo "=========================================="
echo "总测试数: $TOTAL"
echo "通过: $PASSED"
echo "失败: $((TOTAL - PASSED))"
PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")
echo "通过率: $PASS_RATE%"

# 保存
cat > test_results_final.txt << RESULTS
管理员功能端到端测试结果
时间: $(date '+%Y-%m-%d %H:%M:%S')

总测试数: $TOTAL
通过: $PASSED
失败: $((TOTAL - PASSED))
通过率: $PASS_RATE%

测试覆盖:
✓ XSRF保护（403验证）
✓ 管理员登录（错误/正确密码）
✓ Dashboard统计数据
✓ 用户管理（列表、分页、边界）
✓ 商品管理（列表、状态筛选）
✓ 订单管理（列表、状态筛选）
✓ 未授权访问保护

未测试:
- POST操作（toggle/delete/restore）需代码审查或手动测试
RESULTS

echo "结果已保存到: test_results_final.txt"

# 返回码
[ $PASSED -eq $TOTAL ] && exit 0 || exit 1
