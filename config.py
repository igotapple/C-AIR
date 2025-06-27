import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Oracle DB 설정 (환경변수에서 값 읽어옴)
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_SERVICE = os.getenv("DB_SERVICE")

    # Oracle DB 연결 문자열 (SQLAlchemy용, Thin 모드)
    SQLALCHEMY_DATABASE_URI = f"oracle+oracledb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/?service_name={DB_SERVICE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # SQLAlchemy 이벤트 시스템 비활성화(권장)

    # Flask SECRET_KEY (세션 암호화용)
    SECRET_KEY = os.getenv("SECRET_KEY")

    # 이메일 설정 (기본값: 네이버 SMTP)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.naver.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "scw0629@naver.com")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "singsung9206")
