#mysql数据库连接的基本操作
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
import configparser
import os

# 读取配置文件
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../config.ini'))

# 优先从环境变量获取MySQL连接信息，否则从配置文件读取
mysql_user = os.environ.get('MYSQL_USER', config.get('mysql', 'user'))
mysql_password = os.environ.get('MYSQL_PASSWORD', config.get('mysql', 'password'))
mysql_host = os.environ.get('MYSQL_HOST', config.get('mysql', 'host'))
mysql_port = int(os.environ.get('MYSQL_PORT', config.getint('mysql', 'port')))
mysql_database = os.environ.get('MYSQL_DATABASE', config.get('mysql', 'database'))
mysql_charset = os.environ.get('MYSQL_CHARSET', config.get('mysql', 'charset'))

conn_url = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset={mysql_charset}'
engine = create_engine(conn_url, echo=True, pool_recycle=3600)
Base = declarative_base()