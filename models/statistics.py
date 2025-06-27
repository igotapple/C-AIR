from models.reservation import Reservation
from models.cancellation import Cancellation
from models.customer import Customer, db
import pandas as pd
from sqlalchemy import func, desc, over, text


def get_group01_stats():
    q = (
        db.session.query(
            Reservation.flight_number.label("flight_number"),
            Reservation.departure_date_time.label("departure_date_time"),
            func.sum(Reservation.payment).label("total_amount"),
            func.avg(Reservation.payment).label("avg_amount"),
            func.count().label("reservation_count"),
        )
        .group_by(Reservation.flight_number, Reservation.departure_date_time)
        .order_by(func.sum(Reservation.payment).desc())
    )
    df = pd.read_sql(q.statement, db.engine)
    df.columns = [
        "flight_number",
        "departure_date_time",
        "total_amount",
        "avg_amount",
        "reservation_count",
    ]
    # 컬럼 순서 변경
    df = df[
        [
            "flight_number",
            "departure_date_time",
            "reservation_count",
            "total_amount",
            "avg_amount",
        ]
    ]
    return df


def get_group02_stats():
    q = (
        db.session.query(
            Cancellation.cno.label("cno"),
            Customer.name.label("name"),
            func.sum(Cancellation.refund).label("total_refund"),
            func.max(Cancellation.refund).label("max_refund"),
            func.count().label("cancel_count"),
        )
        .join(Customer, Customer.cno == Cancellation.cno)
        .group_by(Cancellation.cno, Customer.name)
        .having(func.sum(Cancellation.refund) > 0)
        .order_by(func.sum(Cancellation.refund).desc())
    )
    df = pd.read_sql(q.statement, db.engine)
    df.columns = ["cno", "name", "total_refund", "max_refund", "cancel_count"]
    # name 컬럼은 내부적으로만 사용, 반환 시에는 제거
    df = df[["cno", "name", "cancel_count", "total_refund", "max_refund"]]
    return df


def get_window01_stats():
    q = db.session.query(
        Reservation.flight_number.label("flight_number"),
        Reservation.departure_date_time.label("departure_date_time"),
        Reservation.payment.label("amount"),
        func.sum(Reservation.payment)
        .over(
            partition_by=[Reservation.flight_number, Reservation.departure_date_time],
            order_by=Reservation.reserve_date_time,
        )
        .label("cumulative_amount"),
        func.rank()
        .over(
            partition_by=[Reservation.flight_number, Reservation.departure_date_time],
            order_by=desc(Reservation.payment),
        )
        .label("amount_rank"),
    )
    df = pd.read_sql(q.statement, db.engine)
    df.columns = [
        "flight_number",
        "departure_date_time",
        "amount",
        "cumulative_amount",
        "amount_rank",
    ]
    # 컬럼 순서 변경
    df = df[
        [
            "flight_number",
            "departure_date_time",
            "cumulative_amount",
            "amount",
            "amount_rank",
        ]
    ]
    return df


def get_window02_stats():
    sql = """
    SELECT
        c.cno,
        c.name,
        SUM(r.payment) AS total_amount,
        RANK() OVER (ORDER BY SUM(r.payment) DESC) AS total_rank
    FROM customer c
    JOIN reservation r ON c.cno = r.cno
    GROUP BY c.cno, c.name
    ORDER BY total_rank
    """
    df = pd.read_sql(text(sql), db.engine)
    df.columns = ["cno", "name", "total_amount", "total_rank"]
    df = df[["cno", "name", "total_amount", "total_rank"]]
    return df
