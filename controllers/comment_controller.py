#coding=utf-8

import tornado.web
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session, sessionmaker
from models.comment import Comment
from models.user import User
from models.product import Product
from models.friendship import Friendship
from base.base import engine
from sqlalchemy import desc

Session = sessionmaker(bind=engine)


# 定义一个简单的敏感词过滤器
SENSITIVE_WORDS = ["坏蛋", "骗子", "垃圾"]

def filter_sensitive_words(content):
    for word in SENSITIVE_WORDS:
        content = content.replace(word, "**")
    return content

class CommentHandler(tornado.web.RequestHandler):
    """评价管理处理器"""
    
    def initialize(self):
        self.session = Session()

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def get(self, product_id=None):
        """获取商品评价列表"""
        try:
            if product_id:
                comments = self.session.query(Comment).filter_by(product_id=product_id).order_by(desc(Comment.created_at)).all()
                
                comments_data = []
                for comment in comments:
                    user = self.session.query(User).filter_by(id=comment.user_id).first()
                    # 修复：使用 comment.text 并进行敏感词过滤
                    filtered_content = filter_sensitive_words(comment.text)
                    comments_data.append({
                        'id': comment.id,
                        'content': filtered_content,
                        'rating': comment.rating,
                        'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'user_name': user.username if user else '匿名用户'
                    })
                
                self.write(json.dumps({'success': True, 'comments': comments_data}))
            else:
                # ... (省略部分代码)
                pass
                
        except Exception as e:
            self.write(json.dumps({'success': False, 'error': str(e)}))

    def post(self):
        """发布评价"""
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return

            product_id = int(self.get_argument("product_id"))
            content = self.get_argument("content")
            rating = float(self.get_argument("rating", 5.0))

            from models.blacklist import Blacklist

# ... (inside CommentHandler.post method)
            product = self.session.query(Product).filter_by(id=product_id).first()
            if not product:
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                return

            # Check if the product owner has blocked the commenter
            is_blocked = self.session.query(Blacklist).filter_by(
                blocker_id=product.user_id,
                blocked_id=user.id
            ).first()

            if is_blocked:
                self.write(json.dumps({'success': False, 'error': '您已被卖家拉黑，无法评价'}))
                return

            # 修复：移除重复评价的检查
            # existing_comment = ... (整段逻辑已删除)

            # 修复：使用 text 字段来创建新评价
            new_comment = Comment(
                user_id=user.id,
                product_id=product_id,
                text=content,
                rating=rating
            )
            
            self.session.add(new_comment)
            self.session.commit()
            
            self.write(json.dumps({
                'success': True, 
                'message': '评价发布成功',
                'comment_id': new_comment.id
            }))
            
        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))


    def delete(self, comment_id):
        """删除评价（仅限评价作者或商品所有者）"""
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return

            comment = self.session.query(Comment).filter_by(id=comment_id).first()
            if not comment:
                self.write(json.dumps({'success': False, 'error': '评价不存在'}))
                return

            product = self.session.query(Product).filter_by(id=comment.product_id).first()
            if not product:
                self.write(json.dumps({'success': False, 'error': '评价关联的商品不存在'}))
                return

            # 评价作者或商品所有者可以删除
            if comment.user_id != user.id and product.user_id != user.id:
                self.write(json.dumps({'success': False, 'error': '您没有权限删除此评价'}))
                return

            self.session.delete(comment)
            self.session.commit()
            
            self.write(json.dumps({'success': True, 'message': '评价删除成功'}))
            
        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))

    def on_finish(self):
        self.session.close()


class ProductRatingHandler(tornado.web.RequestHandler):
    """商品评分统计处理器"""
    
    def initialize(self):
        self.session = Session()

    def get(self, product_id):
        """获取商品评分统计"""
        try:
            # 计算平均评分和评价数量
            from sqlalchemy import func
            result = self.session.query(
                func.avg(Comment.rating).label('avg_rating'),
                func.count(Comment.id).label('comment_count')
            ).filter_by(product_id=product_id).first()
            
            avg_rating = round(float(result.avg_rating), 1) if result.avg_rating else 0
            comment_count = result.comment_count or 0
            
            # 获取评分分布
            rating_distribution = {}
            for i in range(1, 6):
                count = self.session.query(Comment).filter_by(
                    product_id=product_id
                ).filter(Comment.rating == i).count()
                rating_distribution[i] = count
            
            self.write(json.dumps({
                'success': True,
                'avg_rating': avg_rating,
                'comment_count': comment_count,
                'rating_distribution': rating_distribution
            }))
            
        except Exception as e:
            self.write(json.dumps({'success': False, 'error': str(e)}))

    def on_finish(self):
        self.session.close()
