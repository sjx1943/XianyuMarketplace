// MongoDB 初始化脚本
// 当容器首次启动时自动运行

db = db.getSiblingDB('admin');

// 创建应用数据库和用户
db.createUser({
  user: 'chat_user',
  pwd: 'chat_password_change_me',
  roles: [
    { role: 'readWrite', db: 'chat_db' }
  ]
});

// 切换到chat_db
db = db.getSiblingDB('chat_db');

// 创建集合并设置索引
db.createCollection('chat_messages');
db.createCollection('conversations');
db.createCollection('message_read_status');

// 聊天消息集合索引
db.chat_messages.createIndex({ 'from_user_id': 1, 'to_user_id': 1, 'timestamp': 1 });
db.chat_messages.createIndex({ 'from_user_id': 1, 'timestamp': -1 });
db.chat_messages.createIndex({ 'to_user_id': 1, 'timestamp': -1 });
db.chat_messages.createIndex({ 'timestamp': 1 }, { expireAfterSeconds: 7776000 }); // 90天后过期
db.chat_messages.createIndex({ 'content': 'text' }); // 文本搜索索引

// 会话集合索引
db.conversations.createIndex({ 'user_id': 1, 'last_message_time': -1 });
db.conversations.createIndex({ 'user_id': 1, 'friend_id': 1 }, { unique: true });

// 消息已读状态集合索引
db.message_read_status.createIndex({ 'user_id': 1, 'friend_id': 1 });
db.message_read_status.createIndex({ 'last_read_timestamp': -1 });

// 授予权限
db.grantRolesToUser('chat_user', [{ role: 'readWrite', db: 'chat_db' }]);

print('✅ MongoDB 初始化完成');
print('✅ 已创建数据库: chat_db');
print('✅ 已创建用户: chat_user');
print('✅ 已创建必要的集合和索引');
