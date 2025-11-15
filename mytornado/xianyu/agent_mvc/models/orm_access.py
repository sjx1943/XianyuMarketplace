#model相关的sql操作

from product import Product
from user import User
from chat import Chat
from sqlalchemy.orm import sessionmaker,declarative_base
from sqlalchemy import create_engine
from MVC.base.base import Base, engine
# Update the connection URL to use PyMySQL (`+pymysql`)

#Base.metadata.create_all(engine)


# Create a session
Session = sessionmaker(bind=engine)
session = Session()


#添加用户
# new_user = User(id=3, username='sgg', password='password', email='sgg@example.com')
# session.add(new_user)
# session.commit()

# # 查询用户
# user = session.query(User).filter_by(username='john').first()
# print(user)
# 添加商品
new_product = Product(
        name="气球",
        description="这是一个示例商品描述",
        price=199.99,
        user_id=2,  # 假设用户ID为1
        tag="生活用品",
        image="https://img2.baidu.com/it/u=1301655116,4209223946&fm=253&fmt=auto&app=120&f=JPEG?w=679&h=500"
)
session.add(new_product)
session.commit()

#修改商品
# product_to_update = session.query(Product).filter_by(name='iPhone 13 Pro Max').first()
# product_to_update.name = "iPhone 13"  # 修改价格
# session.commit()

# # 删除商品
# product_to_delete = session.query(Product).filter_by(name='iPhone 13').first()
# session.delete(product_to_delete)
# session.commit()

# # 查询商品
# product = session.query(Product).filter_by(name='iPhone 15 Pro Max').first()
# print(product)
#
# # 添加聊天
# new_chat = Chat(user1_id=2, user2_id=3, message='Hola!')
# session.add(new_chat)
# session.commit()
#
# # 查询聊天
# chat = session.query(Chat).filter_by(id=4).first()
# print(chat)
#
# # 关闭会话
session.close()
# Base.metadata.drop_all(engine)
