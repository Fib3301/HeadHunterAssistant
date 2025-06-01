from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    extension_user_id = Column(String, nullable=False)
    encrypted_access_token = Column(String, nullable=False)
    encrypted_refresh_token = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserToken(user_id={self.user_id}, extension_user_id={self.extension_user_id})>"

class EmployerInfo(Base):
    __tablename__ = "employer_info"

    id = Column(String, primary_key=True)
    extension_user_id = Column(String, nullable=False, unique=True)
    employer_id = Column(String, nullable=False)
    employer_name = Column(String, nullable=False)
    manager_id = Column(String, nullable=False)
    manager_email = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<EmployerInfo(employer_id={self.employer_id}, manager_id={self.manager_id})>" 