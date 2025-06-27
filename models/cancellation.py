from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from models.customer import db
from datetime import datetime


class Cancellation(db.Model):
    __tablename__ = "CANCELLATION"

    cno = Column("CNO", String(20), primary_key=True)
    flight_number = Column("FLIGHT_NUMBER", String(20), primary_key=True)
    departure_date_time = Column("DEPARTURE_DATE_TIME", DateTime, primary_key=True)
    seat_class = Column("SEAT_CLASS", String(20), primary_key=True)
    refund = Column("REFUND", Integer, nullable=False)
    cancel_date_time = Column(
        "CANCEL_DATE_TIME", DateTime, default=datetime.now, nullable=False
    )

    # Foreign Key 관계 설정
    customer = db.relationship(
        "Customer", foreign_keys=[cno], primaryjoin="Cancellation.cno == Customer.cno"
    )
    airplane = db.relationship(
        "Airplane",
        foreign_keys=[flight_number, departure_date_time],
        primaryjoin="and_(Cancellation.flight_number == Airplane.flight_number, "
        "Cancellation.departure_date_time == Airplane.departure_date_time)",
    )

    def __repr__(self):
        return (
            f"<Cancellation {self.cno} {self.flight_number} {self.departure_date_time}>"
        )

    @classmethod
    def _calculate_refund_amount(cls, original_payment, days_before_departure):
        """
        환불 금액 계산 (고정 위약금 정책)
        """
        # 위약금 정책: 15일 이전 150,000원, 14일~4일 180,000원, 3일 이내 250,000원, 당일 전액
        if days_before_departure >= 15:
            penalty = 150000  # 150,000원
        elif days_before_departure >= 4:
            penalty = 180000  # 180,000원
        elif days_before_departure >= 1:
            penalty = 250000  # 250,000원
        else:
            penalty = original_payment  # 당일 취소시 전액 위약금

        refund_amount = max(
            0, original_payment - penalty
        )  # 환불 금액이 음수가 되지 않도록
        return refund_amount

    @classmethod
    def cancel_reservation_with_fee(
        cls, cno, flight_number, departure_date_time, seat_class, original_payment
    ):
        """
        수수료를 적용한 예약 취소
        """
        from models.reservation import Reservation
        from models.seat import Seat

        # 예약 존재 확인
        reservation = Reservation.query.filter_by(
            cno=cno,
            flight_number=flight_number,
            departure_date_time=departure_date_time,
            seat_class=seat_class,
        ).first()

        if not reservation:
            return None, "해당 예약을 찾을 수 없습니다."

        # 출발일까지 남은 일수 계산
        days_before_departure = (departure_date_time - datetime.now()).days

        # 환불 금액 계산
        refund_amount = cls._calculate_refund_amount(
            original_payment, days_before_departure
        )

        try:
            # 취소 기록 생성
            cancellation = cls(
                cno=cno,
                flight_number=flight_number,
                departure_date_time=departure_date_time,
                seat_class=seat_class,
                refund=refund_amount,
            )

            db.session.add(cancellation)

            # 예약 삭제
            db.session.delete(reservation)

            # 좌석 수 증가
            Seat.update_seat_count(flight_number, departure_date_time, seat_class, 1)

            db.session.commit()

            return (
                cancellation,
                f"예약이 성공적으로 취소되었습니다. 환불 금액: {refund_amount:,}원",
            )

        except Exception as e:
            db.session.rollback()
            return None, f"취소 중 오류가 발생했습니다: {str(e)}"

    @classmethod
    def get_customer_cancellations(cls, cno):
        """
        고객의 모든 취소 내역 조회
        """
        return cls.query.filter_by(cno=cno).order_by(cls.cancel_date_time.desc()).all()

    @classmethod
    def get_cancellation_details(
        cls, cno, flight_number, departure_date_time, seat_class
    ):
        """
        특정 취소 내역 상세 조회
        """
        return cls.query.filter_by(
            cno=cno,
            flight_number=flight_number,
            departure_date_time=departure_date_time,
            seat_class=seat_class,
        ).first()

    @classmethod
    def get_cancellation_statistics(cls):
        """
        취소 통계 조회 (관리자용)
        """
        total_cancellations = cls.query.count()
        total_refund = db.session.query(db.func.sum(cls.refund)).scalar() or 0

        return {
            "total_cancellations": total_cancellations,
            "total_refund": total_refund,
        }
