from sqlalchemy import Column, String, DateTime
from models.customer import db
from models.seat import Seat
from sqlalchemy import func, and_, text
from datetime import datetime


class Airplane(db.Model):
    __tablename__ = "AIRPLANE"

    # 공항 코드와 공항명 매핑 (검색 시 한글/영문 모두 지원)
    AIRPORT_MAPPING = {
        "ICN": ["인천", "인천공항", "ICN"],
        "JFK": ["뉴욕", "JFK", "JFK공항"],
    }

    # 항공편 정보 컬럼 정의
    airline = Column("AIRLINE", String(100), nullable=False)  # 항공사명
    flight_number = Column("FLIGHT_NUMBER", String(20), primary_key=True)  # 운항편명
    departure_date_time = Column(
        "DEPARTURE_DATE_TIME", DateTime, primary_key=True
    )  # 출발일시
    departure_airport = Column(
        "DEPARTURE_AIRPORT", String(100), nullable=False
    )  # 출발공항
    arrival_date_time = Column(
        "ARRIVAL_DATE_TIME", DateTime, nullable=False
    )  # 도착일시
    arrival_airport = Column("ARRIVAL_AIRPORT", String(100), nullable=False)  # 도착공항

    def __repr__(self):
        return f"<Airplane {self.flight_number} {self.departure_date_time}>"

    @classmethod
    def _get_airport_codes(cls, airport_name):
        """
        공항명이나 코드를 받아서 해당하는 공항 코드 리스트 반환 (검색 편의)
        """
        airport_codes = []
        for code, names in cls.AIRPORT_MAPPING.items():
            if any(
                name.lower() in airport_name.lower()
                or airport_name.lower() in name.lower()
                for name in names
            ):
                airport_codes.append(code)
        return airport_codes

    @classmethod
    def search_flights(
        cls, departure_date, departure_airport, arrival_airport, seat_class
    ):
        """
        항공편 검색 메서드 (날짜, 출발/도착공항, 좌석등급)
        """
        search_date = datetime.strptime(departure_date, "%Y-%m-%d").date()

        # 공항 코드들 가져오기 (한글/영문 모두 지원)
        departure_codes = cls._get_airport_codes(departure_airport)
        arrival_codes = cls._get_airport_codes(arrival_airport)

        # 공항 코드가 없으면 원래 입력값 그대로 사용
        if not departure_codes:
            departure_codes = [departure_airport]
        if not arrival_codes:
            arrival_codes = [arrival_airport]

        # 좌석 등급 매핑 적용 (한글/영문 입력 모두 지원)
        mapped_seat_class = Seat._get_seat_class(seat_class)

        # 항공편 + 좌석 정보 조인 후 조건 검색
        query = (
            db.session.query(
                cls.airline,
                cls.flight_number,
                cls.departure_date_time,
                cls.departure_airport,
                cls.arrival_date_time,
                cls.arrival_airport,
                Seat.seat_class,
                Seat.number_of_seats,
                Seat.price,
            )
            .join(
                Seat,
                and_(
                    cls.flight_number == Seat.flight_number,
                    cls.departure_date_time == Seat.departure_date_time,
                ),
            )
            .filter(
                and_(
                    func.trunc(cls.departure_date_time) == search_date,
                    cls.departure_airport.in_(departure_codes),
                    cls.arrival_airport.in_(arrival_codes),
                    Seat.seat_class == mapped_seat_class,
                    Seat.number_of_seats > 0,
                )
            )
            .order_by(Seat.price.asc())
        )

        return query.all()
