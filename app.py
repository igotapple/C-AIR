from flask import Flask
from config import Config
import oracledb
from flask_sqlalchemy import SQLAlchemy
from models import Customer, Airplane, Seat, Reservation, Cancellation
from routes.api import api
from routes.main import main

app = Flask(__name__)
app.config.from_object(Config)

# SQLAlchemy db 객체 초기화 (models.customer에서 db 객체 import)
from models.customer import db

db.init_app(app)


# Blueprint 등록 (API와 메인 라우트)
app.register_blueprint(api, url_prefix="/api")
app.register_blueprint(main)


def get_db_connection():
    """
    오라클 DB에 직접 연결하는 함수 (SQLAlchemy와 별개, 테스트/직접 쿼리용)
    """
    try:
        print(f"연결 시도 : {app.config['DB_HOST']}:{app.config['DB_PORT']}")

        # Thin 모드로 연결
        connection = oracledb.connect(
            user=app.config["DB_USER"],
            password=app.config["DB_PASSWORD"],
            host=app.config["DB_HOST"],
            port=app.config["DB_PORT"],
            service_name=app.config["DB_SERVICE"],
        )
        print("데이터베이스 연결 성공!")
        return connection

    except oracledb.Error as error:
        print(f"데이터베이스 연결 오류 : {error}")
        return None


# @app.route("/")
# def index():
# conn = get_db_connection()
# if conn:
# try:
# cursor = conn.cursor()
# cursor.execute("SELECT 1 FROM DUAL")
# result = cursor.fetchone()
# cursor.close()
# conn.close()
# return f"Oracle DB 연결 성공! 테스트 결과 : {result}"
# except oracledb.Error as error:
# return f"쿼리 실행 오류 : {error}"
# return "데이터베이스 연결 실패"


# Flask 앱 실행 (개발용 서버)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
