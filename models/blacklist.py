# models/blacklist.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Sequence
from base.base import Base

class Blacklist(Base):
    __tablename__ = 'xu_blacklist'

    id = Column(Integer, Sequence('blacklist_id_seq'), primary_key=True)
    
    # The user who is performing the block action
    blocker_id = Column(Integer, ForeignKey('xu_user.id'), nullable=False, index=True)
    
    # The user who is being blocked
    blocked_id = Column(Integer, ForeignKey('xu_user.id'), nullable=False, index=True)

    # Ensure that a user can only block another user once.
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='_blocker_blocked_uc'),
    )

    def __repr__(self):
        return f"<Blacklist(blocker_id={self.blocker_id}, blocked_id={self.blocked_id})>"

# After creating this file, you can use the following lines in a separate script
# or uncomment them temporarily to create the table in your database.
# from base.base import engine
# from models.user import User  # <-- Import the User model
# 
# if __name__ == '__main__':
#     print("Creating blacklist table...")
#     Base.metadata.create_all(engine)
#     print("Table created.")
