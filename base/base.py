#数据库连接的基本操作
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
import configparser
import os

# 读取配置文件
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../config.ini'))

# 优先使用环境变量DATABASE_URL (PostgreSQL on Replit)
# 否则尝试MySQL配置
if os.environ.get('DATABASE_URL'):
    conn_url = os.environ.get('DATABASE_URL')
elif os.environ.get('MYSQL_HOST'):
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_port = int(os.environ.get('MYSQL_PORT', 3306))
    mysql_database = os.environ.get('MYSQL_DATABASE')
    mysql_charset = os.environ.get('MYSQL_CHARSET', 'utf8mb4')
    conn_url = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset={mysql_charset}'
else:
    try:
        mysql_user = config.get('mysql', 'user')
        mysql_password = config.get('mysql', 'password')
        mysql_host = config.get('mysql', 'host')
        mysql_port = config.getint('mysql', 'port')
        mysql_database = config.get('mysql', 'database')
        mysql_charset = config.get('mysql', 'charset')
        conn_url = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset={mysql_charset}'
    except:
        conn_url = 'sqlite:///xianyu.db'

engine = create_engine(conn_url, echo=True, pool_recycle=3600)
Base = declarative_base()