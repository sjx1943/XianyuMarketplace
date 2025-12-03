#!/bin/bash

# ==========================================
# Replit PostgreSQL 数据迁移脚本
# ==========================================
# 功能: 从Replit开发环境导出PostgreSQL数据，用于VPS生产环境导入
# 用法: bash migrate-replit-to-vps.sh
# 输出: backup_replit_YYYYMMDD_HHMMSS.sql
# ==========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Replit → VPS PostgreSQL 数据迁移${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查环境变量
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}错误: DATABASE_URL 环境变量未设置${NC}"
    echo -e "${YELLOW}请在Replit Shell中运行此脚本${NC}"
    exit 1
fi

# 生成备份文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_replit_${TIMESTAMP}.sql"

echo -e "\n${YELLOW}[1/2] 使用Python安全解析DATABASE_URL并导出数据...${NC}"

# 使用Python脚本导出 - 使用urllib.parse安全解析URL，避免特殊字符问题
python3 << 'PYTHON_SCRIPT'
import os
import sys
from datetime import datetime
from urllib.parse import urlparse, unquote

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("错误: DATABASE_URL未设置")
    sys.exit(1)

# 安全解析URL (处理密码中的特殊字符)
parsed = urlparse(DATABASE_URL)
db_user = unquote(parsed.username) if parsed.username else ''
db_pass = unquote(parsed.password) if parsed.password else ''
db_host = parsed.hostname or 'localhost'
db_port = parsed.port or 5432
db_name = parsed.path.lstrip('/').split('?')[0] if parsed.path else ''

print(f"数据库信息:")
print(f"  用户: {db_user}")
print(f"  主机: {db_host}")
print(f"  端口: {db_port}")
print(f"  数据库: {db_name}")

# 使用SQLAlchemy导出
try:
    from sqlalchemy import create_engine, text, inspect
    
    engine = create_engine(DATABASE_URL)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'backup_replit_{timestamp}.sql'
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n发现 {len(tables)} 个表: {', '.join(tables)}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- Replit PostgreSQL Backup\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Source: {db_host}:{db_port}/{db_name}\n")
            f.write(f"-- Tables: {', '.join(tables)}\n\n")
            
            # 禁用外键检查
            f.write("SET session_replication_role = 'replica';\n\n")
            
            total_rows = 0
            for table_name in tables:
                print(f"导出表: {table_name}...", end=" ")
                
                # 获取表结构
                columns = inspector.get_columns(table_name)
                col_names = [c['name'] for c in columns]
                
                # 导出数据
                result = conn.execute(text(f'SELECT * FROM "{table_name}"'))
                rows = result.fetchall()
                
                print(f"{len(rows)} 行")
                total_rows += len(rows)
                
                if rows:
                    f.write(f"\n-- Table: {table_name} ({len(rows)} rows)\n")
                    for row in rows:
                        values = []
                        for i, val in enumerate(row):
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, str):
                                escaped = val.replace("'", "''").replace("\\", "\\\\")
                                values.append(f"'{escaped}'")
                            elif isinstance(val, datetime):
                                values.append(f"'{val.isoformat()}'")
                            elif isinstance(val, bool):
                                values.append('TRUE' if val else 'FALSE')
                            elif isinstance(val, bytes):
                                hex_str = val.hex()
                                values.append(f"'\\x{hex_str}'")
                            else:
                                values.append(str(val))
                        
                        cols_str = ', '.join([f'"{c}"' for c in col_names])
                        vals_str = ', '.join(values)
                        f.write(f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({vals_str}) ON CONFLICT DO NOTHING;\n')
            
            # 恢复外键检查
            f.write("\nSET session_replication_role = 'origin';\n")
    
    # 获取文件大小
    import os
    file_size = os.path.getsize(output_file)
    size_str = f"{file_size/1024:.1f}KB" if file_size < 1024*1024 else f"{file_size/1024/1024:.1f}MB"
    
    print(f"\n========================================")
    print(f"  导出完成!")
    print(f"========================================")
    print(f"备份文件: {output_file}")
    print(f"文件大小: {size_str}")
    print(f"总行数: {total_rows}")
    print(f"\n下一步操作:")
    print(f"1. 下载备份文件到本地 (从Replit Files面板)")
    print(f"2. 上传到VPS:")
    print(f"   scp {output_file} root@happepls.pics:/opt/secondhand-platform/")
    print(f"3. 在VPS上导入:")
    print(f"   docker exec -i secondhand-postgres psql -U secondhand_user -d secondhand_db < {output_file}")

except Exception as e:
    print(f"导出失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

echo -e "\n${GREEN}[2/2] 脚本执行完成${NC}"
