from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 3166 alpha-3
    state: Mapped[str | None] = mapped_column(String(50))
    city: Mapped[str | None] = mapped_column(String(100))
    showgrounds_slug: Mapped[str | None] = mapped_column(String(100), unique=True)
    fei_venue_id: Mapped[str | None] = mapped_column(String(50), unique=True)

    shows: Mapped[list["Show"]] = relationship(back_populates="venue", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Venue {self.name} ({self.country})>"


class Show(Base):
    __tablename__ = "shows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)  # ISO week 1-53
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    star_level: Mapped[int | None] = mapped_column(Integer)  # 1-5 for CSI
    fei_event_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    showgrounds_show_id: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # "fei" or "showgrounds"
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    venue: Mapped["Venue"] = relationship(back_populates="shows")
    classes: Mapped[list["CompetitionClass"]] = relationship(
        back_populates="show", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Show {self.name} ({self.start_date})>"


class CompetitionClass(Base):
    __tablename__ = "competition_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    class_number: Mapped[str | None] = mapped_column(String(20))
    fei_class_type: Mapped[str | None] = mapped_column(String(50))  # Grand Prix, Ranking, Speed, etc.
    height_cm: Mapped[int | None] = mapped_column(Integer)  # table height in cm
    is_ranking_class: Mapped[bool] = mapped_column(Boolean, default=False)
    entry_count: Mapped[int | None] = mapped_column(Integer)
    starter_count: Mapped[int | None] = mapped_column(Integer)
    prize_money: Mapped[float | None] = mapped_column(Float)

    show: Mapped["Show"] = relationship(back_populates="classes")

    def __repr__(self) -> str:
        return f"<CompetitionClass {self.name} entries={self.entry_count}>"
