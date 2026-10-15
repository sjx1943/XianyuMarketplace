-- 诊断脚本：查看 wechat_avatar 字段的实际值

-- 1. 查看表结构
\d xu_user

-- 2. 查看有头像的用户（前 5 个）
SELECT id, wechat_avatar, avatar_security_status FROM xu_user WHERE wechat_avatar IS NOT NULL LIMIT 5;

-- 3. 统计各种情况
SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN wechat_avatar IS NOT NULL THEN 1 END) as avatar_is_not_null,
    COUNT(CASE WHEN wechat_avatar = '' THEN 1 END) as avatar_is_empty_string,
    COUNT(CASE WHEN wechat_avatar IS NULL THEN 1 END) as avatar_is_null,
    COUNT(CASE WHEN TRIM(wechat_avatar) = '' THEN 1 END) as avatar_is_whitespace
FROM xu_user;

-- 4. 查看 wechat_avatar 的实际类型和长度
SELECT 
    id, 
    wechat_avatar,
    LENGTH(wechat_avatar) as length,
    '|' || wechat_avatar || '|' as with_pipes
FROM xu_user 
WHERE wechat_avatar IS NOT NULL 
LIMIT 5;
