from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from models.customer import db
from models.seat import Seat
from datetime import datetime


class Reservation(db.Model):
    __tablename__ = "RESERVATION"

    # 예약 정보 컬럼 정의
    cno = Column("CNO", String(20), primary_key=True)  # 회원번호
    flight_number = Column("FLIGHT_NUMBER", String(20), primary_key=True)  # 운항편명
    departure_date_time = Column(
        "DEPARTURE_DATE_TIME", DateTime, primary_key=True
    )  # 출발일시
    seat_class = Column("SEAT_CLASS", String(20), primary_key=True)  # 좌석등급
    payment = Column("PAYMENT", Integer, nullable=False)  # 결제금액
    reserve_date_time = Column(
        "RESERVE_DATE_TIME", DateTime, default=datetime.now, nullable=False
    )  # 예약일시

    # Foreign Key 관계 설정 (고객, 좌석, 항공편)
    customer = db.relationship(
        "Customer", foreign_keys=[cno], primaryjoin="Reservation.cno == Customer.cno"
    )
    seat = db.relationship(
        "Seat",
        foreign_keys=[flight_number, departure_date_time, seat_class],
        primaryjoin="and_(Reservation.flight_number == Seat.flight_number, "
        "Reservation.departure_date_time == Seat.departure_date_time, "
        "Reservation.seat_class == Seat.seat_class)",
    )
    airplane = db.relationship(
        "Airplane",
        foreign_keys=[flight_number, departure_date_time],
        primaryjoin="and_(Reservation.flight_number == Airplane.flight_number, "
        "Reservation.departure_date_time == Airplane.departure_date_time)",
    )

    def __repr__(self):
        return (
            f"<Reservation {self.cno} {self.flight_number} {self.departure_date_time}>"
        )

    @classmethod
    def create_reservation(
        cls, cno, flight_number, departure_date_time, seat_class, payment
    ):
        """
        새로운 예약 생성 (좌석 가용성, 중복 예약 체크 포함)
        """
        # 좌석 가용성 확인
        available_seats = Seat.get_available_seats(
            flight_number, departure_date_time, seat_class
        )
        if available_seats <= 0:
            return None, "해당 좌석 등급의 가용 좌석이 없습니다."

        # 중복 예약 확인
        existing_reservation = cls.query.filter_by(
            cno=cno,
            flight_number=flight_number,
            departure_date_time=departure_date_time,
            seat_class=seat_class,
        ).first()

        if existing_reservation:
            return None, "이미 예약된 항공편입니다."

        # 예약 생성
        reservation = cls(
            cno=cno,
            flight_number=flight_number,
            departure_date_time=departure_date_time,
            seat_class=seat_class,
            payment=payment,
        )

        try:
            db.session.add(reservation)
            # 좌석 수 감소
            Seat.update_seat_count(flight_number, departure_date_time, seat_class, -1)
            db.session.commit()
            return reservation, "예약이 성공적으로 완료되었습니다."
        except Exception as e:
            db.session.rollback()
            return None, f"예약 중 오류가 발생했습니다: {str(e)}"

    @classmethod
    def get_customer_reservations(cls, cno):
        """
        고객의 모든 예약 조회 (회원번호 기준)
        """
        return cls.query.filter_by(cno=cno).order_by(cls.departure_date_time).all()
