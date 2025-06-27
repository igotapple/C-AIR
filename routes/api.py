from flask import Blueprint, request, session, jsonify, redirect, url_for
from models.customer import Customer
from models.customer import db
from models.airplane import Airplane
from models.seat import Seat
from models.reservation import Reservation
from models.cancellation import Cancellation
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


# API (서버-클라이언트 데이터 통신) 전용 라우트

api = Blueprint("api", __name__)


@api.route("/login", methods=["POST"])
def login():
    if request.is_json:
        data = request.get_json()
        cno = data.get("cno")
        password = data.get("password")
    else:
        cno = request.form.get("cno")
        password = request.form.get("password")

    if not cno or not password:
        if request.is_json:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "회원번호와 비밀번호를 모두 입력해주세요.",
                    }
                ),
                400,
            )
        else:
            return redirect(
                url_for(
                    "main.login_page", error="회원번호와 비밀번호를 모두 입력해주세요."
                )
            )

    user = Customer.query.filter_by(cno=cno, password=password).first()

    if user:
        session["user_cno"] = user.cno
        session["user_name"] = user.name
        # 관리자/고객 구분
        if user.cno.startswith("C0"):
            session["user_role"] = "admin"
        elif user.cno.startswith("C"):
            session["user_role"] = "customer"
        else:
            session["user_role"] = "unknown"
        if request.is_json:
            return jsonify(
                {
                    "success": True,
                    "message": f"{user.name}님 환영합니다!",
                    "role": session["user_role"],
                }
            )
        else:
            return redirect(url_for("main.index_login"))
    else:
        if request.is_json:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "회원번호 또는 비밀번호가 올바르지 않습니다.",
                    }
                ),
                401,
            )
        else:
            return redirect(url_for("main.login_page"))


@api.route("/logout", methods=["GET"])
def logout():
    session.pop("user_cno", None)
    session.pop("user_name", None)
    session.pop("user_role", None)
    return redirect(url_for("main.index"))


@api.route("/search", methods=["GET"])
def search_page():
    """항공기 검색 API"""
    # URL 파라미터에서 검색 조건 가져오기
    departure_date = request.args.get("departure_date")
    departure_airport = request.args.get("departure_airport")
    arrival_airport = request.args.get("arrival_airport")
    seat_class = request.args.get("seat_class")

    try:
        # SQLAlchemy 모델을 사용한 검색
        search_results = Airplane.search_flights(
            departure_date=departure_date,
            departure_airport=departure_airport,
            arrival_airport=arrival_airport,
            seat_class=seat_class,
        )

        # 결과를 딕셔너리 형태로 변환
        flights = []
        for row in search_results:
            flights.append(
                {
                    "airline": row[0],
                    "flight_number": row[1],
                    "departure_date_time": (
                        row[2].strftime("%Y-%m-%d %H:%M") if row[2] else None
                    ),
                    "departure_airport": row[3],
                    "arrival_date_time": (
                        row[4].strftime("%Y-%m-%d %H:%M") if row[4] else None
                    ),
                    "arrival_airport": row[5],
                    "seat_class": row[6],
                    "number_of_seats": row[7],
                    "price": row[8],
                }
            )

        # JSON 요청인 경우 JSON 응답 반환
        if request.headers.get("Accept") == "application/json":
            return jsonify({"success": True, "flights": flights, "count": len(flights)})
        else:
            # HTML 요청인 경우 검색 결과를 세션에 저장하고 reservation 페이지로 리다이렉트
            session["search_results"] = flights
            session["search_params"] = {
                "departure_date": departure_date,
                "departure_airport": departure_airport,
                "arrival_airport": arrival_airport,
                "seat_class": seat_class,
            }
            return redirect(url_for("main.reservation_page"))

    except Exception as e:
        if request.headers.get("Accept") == "application/json":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"검색 중 오류가 발생했습니다: {str(e)}",
                    }
                ),
                500,
            )
        else:
            return redirect(
                url_for(
                    "main.search_page", error=f"검색 중 오류가 발생했습니다: {str(e)}"
                )
            )


@api.route("/reserve", methods=["POST"])
def reserve_flight():
    """항공편 예약 API"""
    # 로그인 상태 확인
    if "user_cno" not in session:
        return (
            jsonify({"success": False, "message": "로그인이 필요한 서비스입니다."}),
            401,
        )

    # JSON 데이터 파싱
    if not request.is_json:
        return jsonify({"success": False, "message": "잘못된 요청 형식입니다."}), 400

    data = request.get_json()
    flight_number = data.get("flight_number")
    departure_date_time = data.get("departure_date_time")
    seat_class = data.get("seat_class")
    price = data.get("price")

    # 필수 파라미터 검증
    if not all([flight_number, departure_date_time, seat_class, price]):
        return (
            jsonify({"success": False, "message": "모든 예약 정보를 입력해주세요."}),
            400,
        )

    try:
        # 날짜 시간 파싱
        departure_datetime = datetime.strptime(departure_date_time, "%Y-%m-%d %H:%M")

        # 예약 생성
        reservation, message = Reservation.create_reservation(
            cno=session["user_cno"],
            flight_number=flight_number,
            departure_date_time=departure_datetime,
            seat_class=seat_class,
            payment=price,
        )

        if reservation:
            # 고객 정보 가져오기
            customer = Customer.query.filter_by(cno=session["user_cno"]).first()
            if not customer:
                return (
                    jsonify(
                        {"success": False, "message": "고객 정보를 찾을 수 없습니다."}
                    ),
                    400,
                )

            # 항공편 정보 가져오기
            airplane = Airplane.query.filter_by(
                flight_number=flight_number, departure_date_time=departure_datetime
            ).first()

            # 이메일 전송을 위한 항공편 정보 구성
            flight_info = {
                "flight_number": flight_number,
                "airline": airplane.airline if airplane else "알 수 없음",
                "departure_date_time": departure_date_time,
                "departure_airport": (
                    airplane.departure_airport if airplane else "알 수 없음"
                ),
                "arrival_date_time": (
                    airplane.arrival_date_time.strftime("%Y-%m-%d %H:%M")
                    if airplane
                    else "알 수 없음"
                ),
                "arrival_airport": (
                    airplane.arrival_airport if airplane else "알 수 없음"
                ),
                "seat_class": seat_class,
                "price": price,
            }

            # 이메일 전송
            email_success, email_message = send_reservation_email(
                customer.email, customer.name, flight_info
            )

            return jsonify(
                {
                    "success": True,
                    "message": message,
                    "email_sent": email_success,
                    "email_message": email_message,
                    "reservation_id": f"{reservation.cno}_{reservation.flight_number}_{reservation.departure_date_time}",
                }
            )
        else:
            return jsonify({"success": False, "message": message}), 400

    except ValueError:
        return jsonify({"success": False, "message": "잘못된 날짜 형식입니다."}), 400
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"예약 처리 중 오류가 발생했습니다: {str(e)}",
                }
            ),
            500,
        )


def send_reservation_email(customer_email, customer_name, flight_info):
    """
    예약 완료 이메일 전송
    """
    try:
        # 이메일 설정 (config.py에서 가져오기)
        smtp_server = Config.SMTP_SERVER
        smtp_port = Config.SMTP_PORT
        sender_email = Config.SENDER_EMAIL
        sender_password = Config.SENDER_PASSWORD

        # 이메일 내용 구성
        subject = f"[C-AIR] {customer_name}님의 항공편 예약이 완료되었습니다"

        html_content = f"""
        <html>
        <body>
            <h2>C-AIR 항공편 예약 완료</h2>
            <p>{customer_name}님, 안녕하세요!</p>
            <p>항공편 예약이 성공적으로 완료되었습니다.</p>
            
            <h3>예약 정보</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; background-color: #f2f2f2;"><strong>운항편명</strong></td>
                    <td style="padding: 8px;">{flight_info['flight_number']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #f2f2f2;"><strong>항공사</strong></td>
                    <td style="padding: 8px;">{flight_info['airline']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #f2f2f2;"><strong>출발일시</strong></td>
                    <td style="padding: 8px;">{flight_info['departure_date_time']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #f2f2f2;"><strong>출발공항</strong></td>
                    <td style="padding: 8px;">{flight_info['departure_airport']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #f2f2f2;"><strong>도착일시</strong></td>
                    <td style="padding: 8px;">{flight_info['arrival_date_time']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #f2f2f2;"><strong>도착공항</strong></td>
                    <td style="padding: 8px;">{flight_info['arrival_airport']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #f2f2f2;"><strong>좌석등급</strong></td>
                    <td style="padding: 8px;">{flight_info['seat_class']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #f2f2f2;"><strong>결제금액</strong></td>
                    <td style="padding: 8px;">{flight_info['price']:,}원</td>
                </tr>
            </table>
            
            <p style="margin-top: 20px;">
                안전하고 즐거운 여행 되시길 바랍니다.<br>
                감사합니다.
            </p>
            
            <p style="color: #666; font-size: 12px;">
                본 이메일은 자동으로 발송되었습니다.<br>
                문의사항이 있으시면 고객센터로 연락해 주세요.
            </p>
        </body>
        </html>
        """

        # 이메일 메시지 생성
        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = customer_email
        msg["Subject"] = subject

        # HTML 내용 추가
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # SMTP 서버 연결 및 이메일 전송
        if smtp_port == 465:
            # SSL 사용 (네이버 메일 등)
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # TLS 사용 (Gmail 등)
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()

        server.login(sender_email, sender_password)

        text = msg.as_string()
        server.sendmail(sender_email, customer_email, text)
        server.quit()

        return True, "이메일이 성공적으로 전송되었습니다."

    except Exception as e:
        return False, f"이메일 전송 중 오류가 발생했습니다: {str(e)}"


@api.route("/cancel-reservation", methods=["POST"])
def cancel_reservation():
    """예약 취소 API"""
    # 로그인 상태 확인
    if "user_cno" not in session:
        return (
            jsonify({"success": False, "message": "로그인이 필요한 서비스입니다."}),
            401,
        )

    # JSON 데이터 파싱
    if not request.is_json:
        return jsonify({"success": False, "message": "잘못된 요청 형식입니다."}), 400

    data = request.get_json()
    flight_number = data.get("flight_number")
    departure_date_time = data.get("departure_date_time")
    seat_class = data.get("seat_class")

    # 필수 파라미터 검증
    if not all([flight_number, departure_date_time, seat_class]):
        return (
            jsonify({"success": False, "message": "모든 취소 정보를 입력해주세요."}),
            400,
        )

    try:
        # 날짜 시간 파싱
        departure_datetime = datetime.fromisoformat(
            departure_date_time.replace("Z", "+00:00")
        )

        # 예약 존재 확인
        reservation = Reservation.query.filter_by(
            cno=session["user_cno"],
            flight_number=flight_number,
            departure_date_time=departure_datetime,
            seat_class=seat_class,
        ).first()

        if not reservation:
            return (
                jsonify({"success": False, "message": "해당 예약을 찾을 수 없습니다."}),
                404,
            )

        # 출발 시간 확인 (출발 시간이 지난 경우 취소 불가)
        if departure_datetime <= datetime.now():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "출발 시간이 지난 항공편은 취소할 수 없습니다.",
                    }
                ),
                400,
            )

        # 예약 취소 실행
        cancellation, message = Cancellation.cancel_reservation_with_fee(
            cno=session["user_cno"],
            flight_number=flight_number,
            departure_date_time=departure_datetime,
            seat_class=seat_class,
            original_payment=reservation.payment,
        )

        if cancellation:
            # 고객 정보 가져오기
            customer = Customer.query.filter_by(cno=session["user_cno"]).first()
            if not customer:
                return (
                    jsonify(
                        {"success": False, "message": "고객 정보를 찾을 수 없습니다."}
                    ),
                    400,
                )

            # 항공편 정보 가져오기
            airplane = Airplane.query.filter_by(
                flight_number=flight_number, departure_date_time=departure_datetime
            ).first()

            return jsonify(
                {
                    "success": True,
                    "message": message,
                    "refund_amount": cancellation.refund,
                    "cancellation_id": f"{cancellation.cno}_{cancellation.flight_number}_{cancellation.departure_date_time}",
                }
            )
        else:
            return jsonify({"success": False, "message": message}), 400

    except ValueError:
        return jsonify({"success": False, "message": "잘못된 날짜 형식입니다."}), 400
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"취소 처리 중 오류가 발생했습니다: {str(e)}",
                }
            ),
            500,
        )
