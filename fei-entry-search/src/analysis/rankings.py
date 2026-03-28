from dataclasses import dataclass

import pandas as pd
from sqlalchemy import func

from src.db.database import get_session
from src.db.models import CompetitionClass, Show, Venue


@dataclass
class ShowOpportunity:
    venue_name: str
    venue_id: int
    state: str | None
    country: str
    star_level: int | None
    week_number: int
    avg_entries: float
    min_entries: int
    max_entries: int
    years_of_data: int
    trend: float  # negative = fewer entries over time (good), positive = growing
    last_year_entries: float | None


def get_avg_entries_by_venue_week(
    star_level: int | None = None,
    country: str | None = None,
    state: str | None = None,
    ranking_only: bool = True,
    db_path: str | None = None,
) -> list[ShowOpportunity]:
    """Get average entry counts per venue + week, sorted lowest first."""
    session = get_session(db_path)

    try:
        query = (
            session.query(
                Venue.name.label("venue_name"),
                Venue.id.label("venue_id"),
                Venue.state,
                Venue.country,
                Show.star_level,
                Show.week_number,
                func.avg(CompetitionClass.entry_count).label("avg_entries"),
                func.min(CompetitionClass.entry_count).label("min_entries"),
                func.max(CompetitionClass.entry_count).label("max_entries"),
                func.count(func.distinct(Show.year)).label("years_of_data"),
            )
            .join(Show, Show.venue_id == Venue.id)
            .join(CompetitionClass, CompetitionClass.show_id == Show.id)
            .filter(CompetitionClass.entry_count.isnot(None))
        )

        if ranking_only:
            query = query.filter(CompetitionClass.is_ranking_class == True)

        if star_level is not None:
            query = query.filter(Show.star_level == star_level)

        if country:
            query = query.filter(Venue.country == country)

        if state:
            query = query.filter(Venue.state == state)

        query = query.group_by(Venue.id, Show.week_number, Show.star_level)
        query = query.order_by(func.avg(CompetitionClass.entry_count).asc())

        results = query.all()

        opportunities = []
        for row in results:
            trend = _calculate_trend(session, row.venue_id, row.week_number, ranking_only)
            last_year = _get_last_year_avg(session, row.venue_id, row.week_number, ranking_only)

            opportunities.append(ShowOpportunity(
                venue_name=row.venue_name,
                venue_id=row.venue_id,
                state=row.state,
                country=row.country,
                star_level=row.star_level,
                week_number=row.week_number,
                avg_entries=round(row.avg_entries, 1),
                min_entries=row.min_entries,
                max_entries=row.max_entries,
                years_of_data=row.years_of_data,
                trend=trend,
                last_year_entries=last_year,
            ))

        return opportunities
    finally:
        session.close()


def _calculate_trend(
    session, venue_id: int, week_number: int, ranking_only: bool
) -> float:
    """Calculate year-over-year trend. Negative = decreasing entries (opportunity)."""
    query = (
        session.query(
            Show.year,
            func.avg(CompetitionClass.entry_count).label("avg_entries"),
        )
        .join(CompetitionClass, CompetitionClass.show_id == Show.id)
        .filter(
            Show.venue_id == venue_id,
            Show.week_number == week_number,
            CompetitionClass.entry_count.isnot(None),
        )
    )

    if ranking_only:
        query = query.filter(CompetitionClass.is_ranking_class == True)

    query = query.group_by(Show.year).order_by(Show.year)
    rows = query.all()

    if len(rows) < 2:
        return 0.0

    # Simple linear trend: (last - first) / num_years
    first_avg = rows[0].avg_entries
    last_avg = rows[-1].avg_entries
    num_years = rows[-1].year - rows[0].year

    if num_years == 0 or first_avg == 0:
        return 0.0

    return round((last_avg - first_avg) / num_years, 1)


def _get_last_year_avg(
    session, venue_id: int, week_number: int, ranking_only: bool
) -> float | None:
    """Get average entries from the most recent year."""
    subq = (
        session.query(func.max(Show.year))
        .filter(Show.venue_id == venue_id, Show.week_number == week_number)
        .scalar()
    )
    if not subq:
        return None

    query = (
        session.query(func.avg(CompetitionClass.entry_count))
        .join(Show, CompetitionClass.show_id == Show.id)
        .filter(
            Show.venue_id == venue_id,
            Show.week_number == week_number,
            Show.year == subq,
            CompetitionClass.entry_count.isnot(None),
        )
    )

    if ranking_only:
        query = query.filter(CompetitionClass.is_ranking_class == True)

    result = query.scalar()
    return round(result, 1) if result else None


def get_entry_trends(venue_id: int, db_path: str | None = None) -> pd.DataFrame:
    """Get year-over-year entry data for a specific venue."""
    session = get_session(db_path)

    try:
        rows = (
            session.query(
                Show.year,
                Show.week_number,
                Show.star_level,
                Show.name,
                CompetitionClass.name.label("class_name"),
                CompetitionClass.entry_count,
                CompetitionClass.starter_count,
                CompetitionClass.is_ranking_class,
            )
            .join(CompetitionClass, CompetitionClass.show_id == Show.id)
            .filter(Show.venue_id == venue_id)
            .order_by(Show.year, Show.week_number)
            .all()
        )

        return pd.DataFrame(rows, columns=[
            "year", "week_number", "star_level", "show_name",
            "class_name", "entry_count", "starter_count", "is_ranking_class",
        ])
    finally:
        session.close()


def get_calendar_heatmap_data(
    year: int | None = None,
    ranking_only: bool = True,
    db_path: str | None = None,
) -> dict[int, list[dict]]:
    """Get weekly entry data formatted for calendar heatmap display.

    Returns a dict mapping week_number -> list of show summaries.
    """
    session = get_session(db_path)

    try:
        query = (
            session.query(
                Show.week_number,
                Venue.name.label("venue_name"),
                Venue.id.label("venue_id"),
                Show.star_level,
                func.avg(CompetitionClass.entry_count).label("avg_entries"),
                func.count(CompetitionClass.id).label("num_classes"),
            )
            .join(Show, Show.venue_id == Venue.id)
            .join(CompetitionClass, CompetitionClass.show_id == Show.id)
            .filter(CompetitionClass.entry_count.isnot(None))
        )

        if ranking_only:
            query = query.filter(CompetitionClass.is_ranking_class == True)

        if year:
            query = query.filter(Show.year == year)

        query = query.group_by(Show.week_number, Venue.id, Show.star_level)
        rows = query.all()

        heatmap: dict[int, list[dict]] = {}
        for row in rows:
            week = row.week_number
            if week not in heatmap:
                heatmap[week] = []
            heatmap[week].append({
                "venue_name": row.venue_name,
                "venue_id": row.venue_id,
                "star_level": row.star_level,
                "avg_entries": round(row.avg_entries, 1),
                "num_classes": row.num_classes,
            })

        return heatmap
    finally:
        session.close()


def rank_shows_by_opportunity(
    star_level: int | None = None,
    week_start: int | None = None,
    week_end: int | None = None,
    country: str | None = None,
    state: str | None = None,
    ranking_only: bool = True,
    limit: int = 50,
    db_path: str | None = None,
) -> list[ShowOpportunity]:
    """Main ranking function: find shows with lowest competition."""
    results = get_avg_entries_by_venue_week(
        star_level=star_level,
        country=country,
        state=state,
        ranking_only=ranking_only,
        db_path=db_path,
    )

    if week_start is not None:
        results = [r for r in results if r.week_number >= week_start]
    if week_end is not None:
        results = [r for r in results if r.week_number <= week_end]

    return results[:limit]
