from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from .database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    location = Column(String, nullable=True)
    status = Column(String, nullable=False, default="success")  # success or failed
    time = Column(DateTime, nullable=False, index=True)

    # result of the risk engine
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)
    reasons = Column(Text, nullable=False)  # list of reasons saved as JSON text
