from flask import Blueprint, render_template, request

from src.analysis.rankings import (
    get_calendar_heatmap_data,
    get_entry_trends,
    rank_shows_by_opportunity,
)

bp = Blueprint("main", __name__)

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]


@bp.route("/")
def dashboard():
    star_level = request.args.get("star_level", type=int)
    country = request.args.get("country") or None
    state = request.args.get("state") or None
    week_start = request.args.get("week_start", type=int)
    week_end = request.args.get("week_end", type=int)
    ranking_only = request.args.get("ranking_only", "true") == "true"

    shows = rank_shows_by_opportunity(
        star_level=star_level,
        week_start=week_start,
        week_end=week_end,
        country=country,
        state=state,
        ranking_only=ranking_only,
        limit=100,
    )

    return render_template(
        "dashboard.html",
        shows=shows,
        star_level=star_level,
        country=country,
        state=state,
        week_start=week_start,
        week_end=week_end,
        ranking_only=ranking_only,
        states=US_STATES,
    )


@bp.route("/calendar")
def calendar():
    year = request.args.get("year", type=int)
    ranking_only = request.args.get("ranking_only", "true") == "true"

    heatmap = get_calendar_heatmap_data(year=year, ranking_only=ranking_only)

    return render_template(
        "calendar.html",
        heatmap=heatmap,
        year=year,
        ranking_only=ranking_only,
    )


@bp.route("/show/<int:venue_id>")
def show_detail(venue_id: int):
    df = get_entry_trends(venue_id)

    # Summarize by year for the overview
    yearly_summary = []
    if not df.empty:
        for year in sorted(df["year"].unique()):
            year_data = df[df["year"] == year]
            ranking_data = year_data[year_data["is_ranking_class"] == True]
            yearly_summary.append({
                "year": year,
                "total_classes": len(year_data),
                "ranking_classes": len(ranking_data),
                "avg_entries": round(ranking_data["entry_count"].mean(), 1) if not ranking_data.empty else None,
                "min_entries": ranking_data["entry_count"].min() if not ranking_data.empty else None,
                "max_entries": ranking_data["entry_count"].max() if not ranking_data.empty else None,
            })

    # Class-level detail
    classes = df.to_dict("records") if not df.empty else []

    venue_name = df.iloc[0]["show_name"] if not df.empty else f"Venue #{venue_id}"

    return render_template(
        "show_detail.html",
        venue_id=venue_id,
        venue_name=venue_name,
        yearly_summary=yearly_summary,
        classes=classes,
    )
