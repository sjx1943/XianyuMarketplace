#!/bin/bash

# 数据库迁移脚本：从Replit导出到VPS
# 用法: bash migrate-db.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}数据库迁移工具 (Replit → VPS)${NC}"
echo -e "${BLUE}======================================${NC}"

# 配置变量
REPLIT_DB_URL="${REPLIT_DATABASE_URL:-}"
VPS_DB_URL="${VPS_DATABASE_URL:-}"
REPLIT_MONGO_URI="${REPLIT_MONGODB_URI:-}"
VPS_MONGO_URI="${VPS_MONGODB_URI:-}"

BACKUP_DIR="./db_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo -e "\n${YELLOW}[第1步]${NC} 检查环境配置..."

if [ -z "$REPLIT_DB_URL" ]; then
    echo -e "${RED}❌ 错误: REPLIT_DATABASE_URL 未设置${NC}"
    echo "请在Replit环境中设置: export REPLIT_DATABASE_URL='postgres://...'"
    exit 1
fi

if [ -z "$VPS_DB_URL" ]; then
    echo -e "${RED}❌ 错误: VPS_DATABASE_URL 未设置${NC}"
    echo "请设置: export VPS_DATABASE_URL='postgres://...'"
    exit 1
fi

echo -e "${GREEN}✅ 环境检查通过${NC}"

echo -e "\n${YELLOW}[第2步]${NC} 导出 PostgreSQL 数据..."

# 提取Replit数据库连接信息
REPLIT_PGHOST=$(echo "$REPLIT_DB_URL" | sed -E 's/.*@([^:]+).*/\1/')
REPLIT_PGPORT=$(echo "$REPLIT_DB_URL" | sed -E 's/.*:([0-9]+)\/.*/\1/')
REPLIT_PGUSER=$(echo "$REPLIT_DB_URL" | sed -E 's/postgres:\/\/([^:]+).*/\1/')
REPLIT_PGPASSWORD=$(echo "$REPLIT_DB_URL" | sed -E 's/.*:([^@]+)@.*/\1/')
REPLIT_PGDATABASE=$(echo "$REPLIT_DB_URL" | sed -E 's/.*\/([^?]+).*/\1/')

echo "连接信息:"
echo "  Host: $REPLIT_PGHOST"
echo "  Port: $REPLIT_PGPORT"
echo "  User: $REPLIT_PGUSER"
echo "  Database: $REPLIT_PGDATABASE"

# 导出数据
PGPASSWORD="$REPLIT_PGPASSWORD" pg_dump \
    -h "$REPLIT_PGHOST" \
    -p "$REPLIT_PGPORT" \
    -U "$REPLIT_PGUSER" \
    -d "$REPLIT_PGDATABASE" \
    --no-password \
    > "$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PostgreSQL 导出成功: $BACKUP_DIR/postgres_backup_$TIMESTAMP.sql${NC}"
else
    echo -e "${RED}❌ PostgreSQL 导出失败${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[第3步]${NC} 导出 MongoDB 数据..."

if [ ! -z "$REPLIT_MONGO_URI" ]; then
    mongodump --uri="$REPLIT_MONGO_URI" --out="$BACKUP_DIR/mongo_backup_$TIMESTAMP"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ MongoDB 导出成功: $BACKUP_DIR/mongo_backup_$TIMESTAMP${NC}"
    else
        echo -e "${YELLOW}⚠️  MongoDB 导出失败（可能是没有mongodump工具）${NC}"
        echo "请手动备份MongoDB或使用: mongodump --uri='$REPLIT_MONGO_URI'"
    fi
else
    echo -e "${YELLOW}⚠️  MONGODB_URI 未设置，跳过MongoDB备份${NC}"
fi

echo -e "\n${YELLOW}[第4步]${NC} 导入到VPS PostgreSQL..."

# 提取VPS数据库连接信息
VPS_PGHOST=$(echo "$VPS_DB_URL" | sed -E 's/.*@([^:]+).*/\1/')
VPS_PGPORT=$(echo "$VPS_DB_URL" | sed -E 's/.*:([0-9]+)\/.*/\1/')
VPS_PGUSER=$(echo "$VPS_DB_URL" | sed -E 's/postgres:\/\/([^:]+).*/\1/')
VPS_PGPASSWORD=$(echo "$VPS_DB_URL" | sed -E 's/.*:([^@]+)@.*/\1/')
VPS_PGDATABASE=$(echo "$VPS_DB_URL" | sed -E 's/.*\/([^?]+).*/\1/')

echo "导入到:"
echo "  Host: $VPS_PGHOST"
echo "  Database: $VPS_PGDATABASE"

# 导入前先清空目标数据库
PGPASSWORD="$VPS_PGPASSWORD" psql \
    -h "$VPS_PGHOST" \
    -p "$VPS_PGPORT" \
    -U "$VPS_PGUSER" \
    -d "$VPS_PGDATABASE" \
    --no-password \
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 导入数据
PGPASSWORD="$VPS_PGPASSWORD" psql \
    -h "$VPS_PGHOST" \
    -p "$VPS_PGPORT" \
    -U "$VPS_PGUSER" \
    -d "$VPS_PGDATABASE" \
    --no-password \
    < "$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PostgreSQL 导入成功${NC}"
else
    echo -e "${RED}❌ PostgreSQL 导入失败${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[第5步]${NC} 导入到VPS MongoDB..."

if [ -d "$BACKUP_DIR/mongo_backup_$TIMESTAMP" ]; then
    mongorestore --uri="$VPS_MONGO_URI" --drop "$BACKUP_DIR/mongo_backup_$TIMESTAMP"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ MongoDB 导入成功${NC}"
    else
        echo -e "${RED}❌ MongoDB 导入失败${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  MongoDB备份不存在，跳过导入${NC}"
fi

echo -e "\n${YELLOW}[第6步]${NC} 验证迁移..."

# 验证PostgreSQL
PGPASSWORD="$VPS_PGPASSWORD" psql \
    -h "$VPS_PGHOST" \
    -p "$VPS_PGPORT" \
    -U "$VPS_PGUSER" \
    -d "$VPS_PGDATABASE" \
    --no-password \
    -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema='public';"

echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}✅ 数据库迁移完成！${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "\n${YELLOW}备份文件位置:${NC}"
echo "  PostgreSQL: $BACKUP_DIR/postgres_backup_$TIMESTAMP.sql"
echo "  MongoDB: $BACKUP_DIR/mongo_backup_$TIMESTAMP"
echo -e "\n${YELLOW}后续步骤:${NC}"
echo "1. 验证VPS中的数据完整性"
echo "2. 更新.env.prod中的数据库URL"
echo "3. 启动VPS应用并测试"
echo "4. 如无问题，更新小程序API地址指向VPS"
echo "5. 删除旧备份: rm -rf $BACKUP_DIR/postgres_backup_* $BACKUP_DIR/mongo_backup_*"
