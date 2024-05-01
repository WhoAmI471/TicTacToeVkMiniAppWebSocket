from sqlalchemy import Column, Integer, String
from config.database import Base

class Leaderboard(Base):
    __tablename__ = 'leaderboard'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    position = Column(Integer)
    name = Column(String)
    last_name = Column(String)
    img_url = Column(String)
    score = Column(Integer)