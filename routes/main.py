from flask import (
    Blueprint,
    render_template,
    session,
    request,
    redirect,
    url_for,
    jsonify,
)
from datetime import datetime
from models.airplane import Airplane
from models.cancellation import Cancellation
from models.reservation import Reservation
import io
import base64
import matplotlib
import seaborn as sns
import pandas as pd
from models.statistics import (
    get_group01_stats,
    get_group02_stats,
    get_window01_stats,
    get_window02_stats,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 웹페이지(HTML) 렌더링 전용 라우트

main = Blueprint("main", __name__)


@main.route("/")
def index():
    # 로그인 상태 확인
    user_cno = session.get("user_cno")
    if user_cno:
        # 로그인된 사용자는 index-login 페이지로 리다이렉트
        return redirect(url_for("main.index_login"))
    else:
        # 로그인되지 않은 사용자는 기본 index 페이지
        return render_template("index.html")


@main.route("/index-login")
def index_login():
    user_name = session.get("user_name", "회원")
    user_role = session.get("user_role", None)
    return render_template("index-login.html", user_name=user_name, user_role=user_role)


@main.route("/login", methods=["GET"])
def login_page():
    error = request.args.get("error")
    return render_template("login.html", error=error)


@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))


@main.route("/search", methods=["GET"])
def search_page():
    error = request.args.get("error")
    user_name = session.get("user_name", "회원")
    user_role = session.get("user_role", None)
    return render_template(
        "search.html", error=error, user_name=user_name, user_role=user_role
    )


@main.route("/reservation", methods=["GET"])
def reservation_page():
    # 세션에서 검색 결과 가져오기
    search_results = session.get("search_results", [])
    search_params = session.get("search_params", {})

    # 사용자 정보 가져오기
    user_name = session.get("user_name", "회원")
    user_role = session.get("user_role", None)

    # 검색 결과가 없으면 검색 페이지로 리다이렉트
    if not search_results:
        return redirect(url_for("main.search_page", error="검색 결과가 없습니다."))

    return render_template(
        "reservation.html",
        flights=search_results,
        search_params=search_params,
        user_name=user_name,
        user_role=user_role,
    )


@main.route("/payment", methods=["GET"])
def payment_page():
    # 로그인 상태 확인
    user_cno = session.get("user_cno")
    if not user_cno:
        # 로그인되지 않은 경우 로그인 페이지로 리다이렉트
        return redirect(
            url_for("main.login_page", error="결제를 위해 로그인이 필요합니다.")
        )

    # 사용자 정보 가져오기
    user_name = session.get("user_name", "회원")
    user_role = session.get("user_role", None)

    return render_template("payment.html", user_name=user_name, user_role=user_role)


@main.route("/payment-complete", methods=["GET"])
def payment_complete_page():
    # 사용자 정보 가져오기
    user_name = session.get("user_name", "회원")
    user_role = session.get("user_role", None)

    return render_template(
        "payment-complete.html", user_name=user_name, user_role=user_role
    )


@main.route("/history", methods=["GET"])
def history_search_page():
    """예약 내역 조회 검색 페이지"""
    return render_template("history-search.html")


@main.route("/history-result", methods=["GET"])
def history_result_page():
    """예약 내역 조회 결과 페이지"""
    # 로그인 상태 확인
    user_cno = session.get("user_cno")
    if not user_cno:
        return redirect(
            url_for("main.login_page", error="내역 조회를 위해 로그인이 필요합니다.")
        )

    # 조회 파라미터 가져오기
    search_type = request.args.get("searchType", "all")
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")

    reservations = []
    cancellations = []

    # 날짜 필터링을 위한 변환
    start_datetime = None
    end_datetime = None

    if start_date:
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end_datetime = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")

    # 예약 내역 조회
    if search_type in ["all", "reservation"]:
        query = Reservation.query.filter_by(cno=user_cno)

        if start_datetime:
            query = query.filter(Reservation.departure_date_time >= start_datetime)
        if end_datetime:
            query = query.filter(Reservation.departure_date_time <= end_datetime)

        reservations = query.order_by(Reservation.departure_date_time.desc()).all()

    # 취소 내역 조회
    if search_type in ["all", "cancellation"]:
        query = Cancellation.query.filter_by(cno=user_cno)

        if start_datetime:
            query = query.filter(Cancellation.departure_date_time >= start_datetime)
        if end_datetime:
            query = query.filter(Cancellation.departure_date_time <= end_datetime)

        cancellations = query.order_by(Cancellation.cancel_date_time.desc()).all()

    return render_template(
        "history-result.html",
        reservations=reservations,
        cancellations=cancellations,
        now=datetime.now(),
    )


@main.route("/statistics", methods=["GET"])
def statistics_page():
    # 관리자 권한 확인
    user_role = session.get("user_role", None)
    if user_role != "admin":
        return redirect(url_for("main.index"))
    user_name = session.get("user_name", "관리자")
    # 추후 통계 데이터 추가 가능
    return render_template("statistics.html", user_name=user_name, user_role=user_role)


@main.route("/statistics/data", methods=["GET"])
def statistics_data():
    stat_type = request.args.get("type")
    # Group 01: Total & Average Reservation Amount by Flight
    if stat_type == "group01":
        df = get_group01_stats()
        plt.figure(figsize=(14, 4))
        sns.barplot(x="flight_number", y="total_amount", data=df)
        plt.title("Total Reservation Amount by Flight")
        plt.xlabel("Flight Number")
        plt.ylabel("Total Reservation Amount")
        plt.xticks(rotation=45)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        return jsonify({"table": df.to_dict(orient="records"), "chart": img_base64})

    # Group 02: Total & Max Refund by Customer
    elif stat_type == "group02":
        df = get_group02_stats()
        plt.figure(figsize=(14, 4))
        sns.barplot(x="cno", y="total_refund", data=df)
        plt.title("Total Refund by Customer")
        plt.xlabel("Customer No (cno)")
        plt.ylabel("Total Refund")
        plt.xticks(rotation=45)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        return jsonify({"table": df.to_dict(orient="records"), "chart": img_base64})

    # Window 01: Cumulative Reservation Amount by Flight (Line Plot)
    elif stat_type == "window01":
        df = get_window01_stats()
        plt.figure(figsize=(14, 6))
        if not df.empty:
            for fn, g in df.groupby("flight_number"):
                plt.plot(
                    g["departure_date_time"],
                    g["cumulative_amount"],
                    marker="o",
                    label=fn,
                )
            plt.legend(
                loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=6, frameon=False
            )
        plt.title("Cumulative Reservation Amount by Flight")
        plt.xlabel("Departure DateTime")
        plt.ylabel("Cumulative Amount")
        plt.xticks(rotation=45)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        return jsonify({"table": df.to_dict(orient="records"), "chart": img_base64})

    # Window 02: Moving Average of Last 3 Reservations by Customer (Line Plot)
    elif stat_type == "window02":
        df = get_window02_stats()
        plt.figure(figsize=(10, 5))
        plt.bar(df["cno"], df["total_amount"])
        plt.title("Total Reservation Amount by Customer")
        plt.xlabel("Customer No (cno)")
        plt.ylabel("Total Reservation Amount")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        return jsonify({"table": df.to_dict(orient="records"), "chart": img_base64})

    return jsonify({"table": [], "chart": ""})
