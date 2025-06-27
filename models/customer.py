from config import Config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String

# Flask 앱과 DB 객체는 app.py에서 생성된다고 가정
# 여기서는 모델 클래스만 정의

# SQLAlchemy DB 객체 생성 (app.py에서 init_app으로 초기화)
db = SQLAlchemy()


class Customer(db.Model):
    __tablename__ = "CUSTOMER"

    # 고객 정보 컬럼 정의
    cno = Column("CNO", String(20), primary_key=True)  # 회원번호
    password = Column("PASSWORD", String(60), nullable=False)  # 비밀번호
    name = Column("NAME", String(60), nullable=False)  # 이름
    email = Column("EMAIL", String(100), unique=True, nullable=False)  # 이메일
    passport = Column("PASSPORT", String(20), unique=True, nullable=False)  # 여권번호

    def __repr__(self):
        return f"<Customer {self.cno}>"
