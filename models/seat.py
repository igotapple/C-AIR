from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from models.customer import db


class Seat(db.Model):
    __tablename__ = "SEAT"

    # 좌석 등급 매핑 (한글/영문 모두 지원)
    SEAT_CLASS_MAPPING = {
        "Business": ["비즈니스", "비즈니스석", "Business", "business"],
        "Economy": ["이코노미", "이코노미석", "Economy", "economy"],
    }

    # 좌석 정보 컬럼 정의
    flight_number = Column("FLIGHT_NUMBER", String(20), primary_key=True)  # 운항편명
    departure_date_time = Column(
        "DEPARTURE_DATE_TIME", DateTime, primary_key=True
    )  # 출발일시
    seat_class = Column("SEAT_CLASS", String(20), primary_key=True)  # 좌석등급
    number_of_seats = Column("NUMBER_OF_SEATS", Integer, nullable=False)  # 잔여좌석수
    price = Column("PRICE", Integer, nullable=False)  # 가격

    # Foreign Key 관계 설정 (Airplane과 연결)
    airplane = db.relationship(
        "Airplane",
        foreign_keys=[flight_number, departure_date_time],
        primaryjoin="and_(Seat.flight_number == Airplane.flight_number, "
        "Seat.departure_date_time == Airplane.departure_date_time)",
    )

    def __repr__(self):
        return f"<Seat {self.flight_number} {self.seat_class}>"

    @classmethod
    def _get_seat_class(cls, seat_class_input):
        """
        좌석 등급 입력값을 받아서 DB 좌석등급으로 변환 (한글/영문 모두 지원)
        """
        for db_class, names in cls.SEAT_CLASS_MAPPING.items():
            if any(
                name.lower() in seat_class_input.lower()
                or seat_class_input.lower() in name.lower()
                for name in names
            ):
                return db_class
        return seat_class_input  # 매핑되지 않으면 원래 입력값 반환

    @classmethod
    def get_available_seats(cls, flight_number, departure_date_time, seat_class):
        """
        특정 항공편/좌석등급의 가용 좌석 수 조회
        """
        # 좌석 등급 매핑 적용
        mapped_seat_class = cls._get_seat_class(seat_class)

        seat = cls.query.filter_by(
            flight_number=flight_number,
            departure_date_time=departure_date_time,
            seat_class=mapped_seat_class,
        ).first()

        return seat.number_of_seats if seat else 0

    @classmethod
    def update_seat_count(
        cls, flight_number, departure_date_time, seat_class, count_change
    ):
        """
        좌석 수 업데이트 (예약 시 감소, 취소 시 증가)
        """
        # 좌석 등급 매핑 적용
        mapped_seat_class = cls._get_seat_class(seat_class)

        seat = cls.query.filter_by(
            flight_number=flight_number,
            departure_date_time=departure_date_time,
            seat_class=mapped_seat_class,
        ).first()

        if seat:
            seat.number_of_seats += count_change
            if seat.number_of_seats < 0:
                seat.number_of_seats = 0
            db.session.commit()
            return True
        return False
