import calendar
import json
import os
import re
from datetime import date, datetime, time, timedelta
from html import escape
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

try:
    import google.generativeai as genai
except ImportError:
    genai = None


st.set_page_config(
    page_title="DayPilot AI",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)


PROFESSION_SUGGESTIONS = [
    "Student",
    "Student Athlete",
    "Doctor",
    "Surgeon",
    "Teacher",
    "Engineer",
    "Professional",
    "Traveler",
    "Other / Custom",
]

MANAGEMENT_AREAS = [
    "School",
    "Work",
    "Sports",
    "Study",
    "Health",
    "Travel",
    "Family",
    "Fitness",
    "Other",
]

SPORT_CATALOG = [
    "Football / Soccer", "Basketball", "Badminton", "Tennis",
    "Formula 1", "Motorsport", "Olympics", "Athletics",
    "Swimming", "Cycling", "Cricket", "Rugby", "Baseball",
    "Ice Hockey", "Field Hockey", "Volleyball", "Handball",
    "Golf", "Boxing", "MMA", "Wrestling", "Gymnastics",
    "Skiing", "Snowboarding", "Table Tennis", "Squash",
    "Netball", "American Football", "Other",
]

TIMEZONES = [
    "Asia/Dubai",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Asia/Riyadh",
    "Asia/Kolkata",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Australia/Sydney",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "UTC",
    "Other / Custom",
]

DEFAULT_COLORS = {
    "Meeting": "#2563EB",
    "Training": "#DC2626",
    "School": "#7C3AED",
    "Study": "#16A34A",
    "Travel": "#EA580C",
    "Medical": "#0891B2",
    "Personal": "#64748B",
    "Sports": "#D97706",
    "Deadline": "#DB2777",
    "Free Time": "#059669",
    "AI Suggested": "#8B5CF6",
    "Other": "#4F46E5",
}

CATEGORY_ICONS = {
    "Meeting": "💼",
    "Training": "🏋️",
    "School": "🎓",
    "Study": "📚",
    "Travel": "✈️",
    "Medical": "🩺",
    "Personal": "✨",
    "Sports": "🏆",
    "Deadline": "⏰",
    "Free Time": "🌿",
    "AI Suggested": "🤖",
    "Other": "📌",
}

THEME_PRESETS = {
    "🌙 Moonlight": {
        "primary": "#202124",
        "secondary": "#6B7280",
        "accent": "#D1D5DB",
        "background": "#ECEFF1",
        "card": "#F8F9FA",
        "text": "#111827",
        "muted": "#6B7280",
        "sidebar": "#17191C",
    },
    "🌲 Forest": {
        "primary": "#214E34",
        "secondary": "#8FAF92",
        "accent": "#2E8B57",
        "background": "#EEF4EC",
        "card": "#FAFCF8",
        "text": "#173124",
        "muted": "#607567",
        "sidebar": "#173A27",
    },
    "🌊 Ocean": {
        "primary": "#4F7C8A",
        "secondary": "#AFCFD8",
        "accent": "#68AEB0",
        "background": "#EDF6F7",
        "card": "#FAFDFD",
        "text": "#17343C",
        "muted": "#607B83",
        "sidebar": "#294F5A",
    },
    "☕ Iced Latte": {
        "primary": "#7A5C43",
        "secondary": "#C9B59D",
        "accent": "#A9825A",
        "background": "#F5EFE7",
        "card": "#FFFDFC",
        "text": "#3C2D22",
        "muted": "#806F62",
        "sidebar": "#4E382A",
    },
    "🌸 Blush Pink": {
        "primary": "#A75D73",
        "secondary": "#F3C6D3",
        "accent": "#D78DA4",
        "background": "#F5F1F3",
        "card": "#FFF9FB",
        "text": "#4A2A35",
        "muted": "#8C6A76",
        "sidebar": "#6E3E50",
    },
}

DEFAULT_THEME_NAME = "🌲 Forest"
DEFAULT_THEME = THEME_PRESETS[DEFAULT_THEME_NAME].copy()

DEFAULT_SETTINGS = {
    "ai_tone": "Adaptive",
    "default_calendar_view": "Week",
    "first_day": "Monday",
    "show_sports": True,
    "show_ai_events": True,
    "save_reflections": True,
    "day_start": 7,
    "day_end": 22,
    "use_gemini": True,
    "gemini_model": "gemini-2.0-flash",
}


# -----------------------------
# SESSION STATE
# -----------------------------
def init_state() -> None:
    defaults = {
        "onboarding_step": 1,
        "profile_done": False,
        "profile": {},
        "events": [],
        "tasks": [],
        "chat_history": [],
        "page": "Dashboard",
        "colors": DEFAULT_COLORS.copy(),
        "theme": DEFAULT_THEME.copy(),
        "theme_name": DEFAULT_THEME_NAME,
        "selected_theme": DEFAULT_THEME_NAME,
        "settings_theme_choice": DEFAULT_THEME_NAME,
        "settings": DEFAULT_SETTINGS.copy(),
        "profession_choice": "Student",
        "custom_profession": "",
        "pending_suggestion": None,
        "assistant_focus_event": None,
        "pending_ai_plans": [],
        "sports_candidates": [],
        "sports_sync_message": "",
        "onboarding_added_count": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value


init_state()


# -----------------------------
# STYLE
# -----------------------------
def apply_css() -> None:
    theme = st.session_state.theme
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {theme['background']}; color: {theme['text']}; }}
        .block-container {{ max-width: 1450px; padding-top: 1.7rem; padding-bottom: 3rem; }}
        section[data-testid="stSidebar"] {{ background: {theme['sidebar']}; }}
        section[data-testid="stSidebar"] * {{ color: white; }}
        .hero {{
            padding: 3rem; border-radius: 28px;
            background: linear-gradient(135deg, {theme['primary']}, {theme.get('accent', theme['sidebar'])});
            color: white; margin: 1rem 0 1.5rem 0;
            box-shadow: 0 18px 50px rgba(15, 23, 42, .18);
        }}
        .hero h1 {{ font-size: 3.4rem; margin: 0 0 .5rem 0; letter-spacing: -.04em; }}
        .hero p {{ font-size: 1.15rem; opacity: .9; max-width: 700px; }}
        .page-title {{ font-size: 2.55rem; font-weight: 850; letter-spacing: -.04em; margin-bottom: .25rem; }}
        .page-subtitle {{ color: {theme['muted']}; font-size: 1.03rem; margin-bottom: 1.4rem; }}
        .metric-card {{
            background: {theme['card']}; border: 1px solid rgba(30,41,59,.08);
            border-radius: 18px; padding: 18px; min-height: 112px;
            box-shadow: 0 8px 24px rgba(15,23,42,.05);
        }}
        .metric-label {{ color: {theme['muted']}; font-size: .88rem; }}
        .metric-value {{ font-size: 2.1rem; font-weight: 850; margin-top: .25rem; }}
        .event-card {{ color: white; border-radius: 12px; padding: 10px 12px; margin: 7px 0; }}
        .event-title {{ font-weight: 800; }}
        .event-meta {{ font-size: .78rem; opacity: .92; margin-top: 3px; }}
        .month-grid {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; }}
        .weekday {{ background: {theme['primary']}; color: white; padding: 9px; border-radius: 8px; text-align: center; font-weight: 800; font-size: .76rem; }}
        .month-cell {{ background: {theme['card']}; min-height: 105px; border: 1px solid rgba(30,41,59,.10); border-radius: 10px; padding: 7px; overflow: hidden; }}
        .today {{ border: 2px solid {theme['primary']}; }}
        .date-number {{ color: {theme['muted']}; font-weight: 800; font-size: .8rem; }}
        .mini-event {{ color: white; padding: 4px 6px; border-radius: 5px; margin-top: 4px; font-size: .66rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .week-grid {{ display: grid; grid-template-columns: 68px repeat(7, minmax(0,1fr)); gap: 5px; margin-bottom: 5px; }}
        .time-label {{ color: {theme['muted']}; font-size: .76rem; font-weight: 700; padding-top: 10px; }}
        .week-cell {{ background: {theme['card']}; min-height: 65px; border: 1px solid rgba(30,41,59,.09); border-radius: 8px; padding: 4px; }}
        .free {{ color: #94A3B8; font-size: .68rem; }}

        .availability-row {{
            display: grid;
            grid-template-columns: 52px 1fr 58px;
            align-items: center;
            gap: 10px;
            margin: 13px 0;
        }}

        .availability-day {{
            font-size: .78rem;
            font-weight: 800;
            color: {theme['muted']};
        }}

        .availability-track {{
            height: 12px;
            border-radius: 999px;
            background: rgba(148, 163, 184, .20);
            overflow: hidden;
        }}

        .availability-fill {{
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(
                90deg,
                {theme['primary']},
                {theme.get('accent', theme['primary'])}
            );
        }}

        .availability-value {{
            text-align: right;
            font-size: .78rem;
            font-weight: 800;
            color: {theme['text']};
        }}

        .week-columns {{
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
            gap: 10px;
            align-items: start;
        }}

        .week-column {{
            background: {theme['card']};
            border: 1px solid rgba(30,41,59,.10);
            border-radius: 14px;
            padding: 12px;
            min-height: 220px;
            box-shadow: 0 6px 18px rgba(15,23,42,.04);
        }}

        .week-column-today {{
            border: 2px solid {theme['primary']};
        }}

        .week-column-header {{
            font-weight: 900;
            font-size: .88rem;
            margin-bottom: 2px;
        }}

        .week-column-date {{
            color: {theme['muted']};
            font-size: .72rem;
            margin-bottom: 10px;
        }}

        .week-event {{
            color: white;
            border-radius: 9px;
            padding: 8px 9px;
            margin-bottom: 8px;
            font-size: .74rem;
            line-height: 1.25;
        }}

        .week-event-name {{
            font-weight: 850;
            margin-bottom: 2px;
        }}

        .week-empty {{
            color: #94A3B8;
            font-size: .74rem;
            padding-top: 8px;
        }}

        @media (max-width: 1100px) {{
            .week-columns {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}

        @media (max-width: 700px) {{
            .week-columns {{
                grid-template-columns: 1fr;
            }}
        }}

        .burnout-track {{
            position: relative;
            height: 28px;
            margin: 34px 3px 18px 3px;
            border-radius: 999px;
            background: linear-gradient(
                90deg,
                #22C55E 0%,
                #22C55E 40%,
                #F59E0B 40%,
                #F59E0B 70%,
                #EF4444 70%,
                #EF4444 100%
            );
        }}

        .burnout-marker {{
            position: absolute;
            top: -10px;
            width: 4px;
            height: 48px;
            border-radius: 4px;
            background: {theme['text']};
            transform: translateX(-2px);
        }}

        .burnout-marker::before {{
            content: "▼";
            position: absolute;
            top: -20px;
            left: -7px;
            color: {theme['text']};
            font-size: 16px;
        }}

        .burnout-zones {{
            display: flex;
            justify-content: space-between;
            font-size: .70rem;
            font-weight: 750;
            color: {theme['muted']};
        }}

        .burnout-score {{
            font-size: 2.1rem;
            font-weight: 900;
            margin-top: .35rem;
        }}

        .burnout-level {{
            display: inline-block;
            margin-top: .25rem;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: .78rem;
            font-weight: 850;
            background: rgba(148,163,184,.16);
        }}

        .theme-preview {{
            background: {theme['card']}; border: 1px solid rgba(30,41,59,.10);
            border-radius: 18px; padding: 16px 18px; margin: .5rem 0 1.25rem 0;
            box-shadow: 0 8px 24px rgba(15,23,42,.06);
        }}
        .theme-preview-title {{ font-weight: 850; font-size: 1rem; margin-bottom: .65rem; }}
        .theme-swatches {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
        .theme-swatch {{ width: 58px; height: 32px; border-radius: 10px; border: 1px solid rgba(0,0,0,.10); }}
        .theme-label {{ color: {theme['muted']}; font-size: .78rem; margin-top: .35rem; }}
        div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 18px; }}
        div.stButton > button {{ background: {theme['primary']}; color: white; border: 0; border-radius: 11px; font-weight: 750; }}
        div.stButton > button:hover {{ filter: brightness(.92); color: white; }}
        @media (max-width: 900px) {{
            .month-grid {{ grid-template-columns: repeat(7, 140px); overflow-x: auto; }}
            .week-grid {{ grid-template-columns: 64px repeat(7, 140px); overflow-x: auto; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_css()


# -----------------------------
# HELPERS
# -----------------------------
def set_theme(theme_name: str) -> None:
    if theme_name in THEME_PRESETS:
        st.session_state.theme_name = theme_name
        st.session_state.theme = THEME_PRESETS[theme_name].copy()


def render_theme_preview(theme_name: str) -> None:
    palette = THEME_PRESETS.get(theme_name, st.session_state.theme)
    swatches = "".join(
        f"<div><div class='theme-swatch' style='background:{color};'></div>"
        f"<div class='theme-label'>{label}</div></div>"
        for label, color in [
            ("Primary", palette["primary"]),
            ("Secondary", palette.get("secondary", palette["muted"])),
            ("Accent", palette.get("accent", palette["card"])),
        ]
    )
    st.markdown(
        f"<div class='theme-preview'><div class='theme-preview-title'>{escape(theme_name)}</div>"
        f"<div class='theme-swatches'>{swatches}</div></div>",
        unsafe_allow_html=True,
    )


def page_header(icon: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='page-title'>{icon} {escape(title)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-subtitle'>{escape(subtitle)}</div>", unsafe_allow_html=True)


def now_local() -> datetime:
    timezone = st.session_state.profile.get("timezone", "UTC")
    try:
        return datetime.now(ZoneInfo(timezone))
    except Exception:
        return datetime.now(ZoneInfo("UTC"))


def event_color(category: str) -> str:
    return st.session_state.colors.get(category, "#4F46E5")


def event_icon(category: str) -> str:
    return CATEGORY_ICONS.get(category, "📌")


def to_minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def from_minutes(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def add_event(
    name: str,
    category: str,
    event_date: str,
    start: str,
    end: str,
    people: str = "",
    needs: str = "",
    notes: str = "",
    result: str = "",
    source: str = "Manual",
    major: bool = True,
) -> bool:
    if not name.strip() or not event_date:
        return False
    duplicate = any(
        e.get("name", "").lower() == name.strip().lower()
        and e.get("date") == event_date
        and e.get("start") == start
        for e in st.session_state.events
    )
    if duplicate:
        return False
    if category not in st.session_state.colors:
        st.session_state.colors[category] = "#4F46E5"
    st.session_state.events.append(
        {
            "name": name.strip(),
            "category": category,
            "date": event_date,
            "start": start,
            "end": end,
            "people": people.strip(),
            "needs": needs.strip(),
            "notes": notes.strip(),
            "result": result.strip(),
            "source": source,
            "major": major,
        }
    )
    return True



def dates_for_pattern(
    start_date: date,
    end_date: date,
    pattern: str,
    selected_days: list[str] | None = None,
) -> list[date]:
    """Return every date included in a recurrence pattern."""
    if end_date < start_date:
        return []

    selected_days = selected_days or []
    day_indexes = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    current = start_date
    results: list[date] = []

    while current <= end_date:
        include = False

        if pattern == "Does not repeat":
            include = current == start_date
        elif pattern == "Daily":
            include = True
        elif pattern == "Weekdays (Monday–Friday)":
            include = current.weekday() < 5
        elif pattern in {"Weekly", "Custom days"}:
            include = current.weekday() in {
                day_indexes[day]
                for day in selected_days
                if day in day_indexes
            }

        if include:
            results.append(current)

        if pattern == "Does not repeat":
            break

        current += timedelta(days=1)

    return results


def add_recurring_events(
    name: str,
    category: str,
    start_date: date,
    end_date: date,
    start_time: time,
    end_time: time,
    pattern: str,
    selected_days: list[str] | None = None,
    people: str = "",
    needs: str = "",
    notes: str = "",
    source: str = "Manual",
    major: bool = True,
) -> tuple[int, int]:
    """Create a series safely and report added and skipped counts."""
    if not name.strip() or end_time <= start_time:
        return 0, 0

    dates = dates_for_pattern(
        start_date,
        end_date,
        pattern,
        selected_days,
    )

    added = 0
    skipped = 0

    for event_day in dates:
        success = add_event(
            name=name,
            category=category,
            event_date=event_day.isoformat(),
            start=start_time.strftime("%H:%M"),
            end=end_time.strftime("%H:%M"),
            people=people,
            needs=needs,
            notes=notes,
            source=source,
            major=major,
        )

        if success:
            added += 1
        else:
            skipped += 1

    return added, skipped


def schedule_block(
    title: str,
    key_prefix: str,
    default_name: str,
    default_category: str,
    default_pattern: str = "Weekly",
    default_days: list[str] | None = None,
) -> dict:
    """Reusable structured schedule input used during onboarding."""
    default_days = default_days or []

    with st.container(border=True):
        st.markdown(f"#### {title}")

        enabled = st.toggle(
            f"Add {title.lower()} to my calendar",
            value=True,
            key=f"{key_prefix}_enabled",
        )

        name = st.text_input(
            "Calendar title",
            value=default_name,
            key=f"{key_prefix}_name",
        )

        pattern_options = [
            "Weekdays (Monday–Friday)",
            "Weekly",
            "Custom days",
            "Does not repeat",
            "Different each week / add manually",
        ]

        pattern = st.selectbox(
            "How often does this happen?",
            pattern_options,
            index=(
                pattern_options.index(default_pattern)
                if default_pattern in pattern_options
                else 1
            ),
            key=f"{key_prefix}_pattern",
        )

        selected_days = st.multiselect(
            "Days",
            DAY_NAMES,
            default=default_days,
            key=f"{key_prefix}_days",
            disabled=pattern not in {"Weekly", "Custom days"},
        )

        columns = st.columns(2)

        start_time = columns[0].time_input(
            "Start time",
            value=time(8, 0),
            key=f"{key_prefix}_start_time",
        )

        end_time = columns[1].time_input(
            "End time",
            value=time(15, 0),
            key=f"{key_prefix}_end_time",
        )

        date_columns = st.columns(2)

        first_date = date_columns[0].date_input(
            "Starts on",
            value=now_local().date(),
            key=f"{key_prefix}_first_date",
        )

        repeat_until = date_columns[1].date_input(
            "Repeat until",
            value=now_local().date() + timedelta(days=30),
            key=f"{key_prefix}_repeat_until",
            disabled=pattern in {
                "Does not repeat",
                "Different each week / add manually",
            },
        )

        if pattern == "Different each week / add manually":
            st.caption(
                "This will not create automatic events. "
                "Add each confirmed date later from Calendar."
            )

    return {
        "enabled": enabled,
        "name": name,
        "category": default_category,
        "pattern": pattern,
        "selected_days": selected_days,
        "start_time": start_time,
        "end_time": end_time,
        "first_date": first_date,
        "repeat_until": (
            first_date
            if pattern == "Does not repeat"
            else repeat_until
        ),
    }


def apply_schedule_block(schedule: dict, source: str) -> tuple[int, int]:
    if not schedule.get("enabled"):
        return 0, 0

    if schedule["pattern"] == "Different each week / add manually":
        return 0, 0

    return add_recurring_events(
        name=schedule["name"],
        category=schedule["category"],
        start_date=schedule["first_date"],
        end_date=schedule["repeat_until"],
        start_time=schedule["start_time"],
        end_time=schedule["end_time"],
        pattern=schedule["pattern"],
        selected_days=schedule["selected_days"],
        source=source,
        major=True,
    )


def parse_api_time(raw: str | None, fallback: str = "12:00") -> str:
    if not raw:
        return fallback

    match = re.search(r"(\d{1,2}):(\d{2})", raw)
    if not match:
        return fallback

    hour = min(max(int(match.group(1)), 0), 23)
    minute = min(max(int(match.group(2)), 0), 59)
    return f"{hour:02d}:{minute:02d}"


def fetch_f1_events() -> list[dict]:
    """Fetch current and next-season F1 race dates from Jolpica."""
    events: list[dict] = []
    today = now_local().date()

    for season in [today.year, today.year + 1]:
        try:
            response = requests.get(
                f"https://api.jolpi.ca/ergast/f1/{season}.json",
                timeout=10,
            )
            response.raise_for_status()
            races = (
                response.json()
                .get("MRData", {})
                .get("RaceTable", {})
                .get("Races", [])
            )
        except Exception:
            continue

        for race in races:
            race_date = race.get("date", "")
            if not race_date:
                continue

            try:
                parsed_date = date.fromisoformat(race_date)
            except ValueError:
                continue

            if parsed_date < today:
                continue

            start = parse_api_time(race.get("time"), "14:00")
            end = from_minutes(min(to_minutes(start) + 120, 1439))

            events.append(
                {
                    "name": race.get("raceName", "Formula 1 Grand Prix"),
                    "category": "Sports",
                    "date": race_date,
                    "start": start,
                    "end": end,
                    "notes": "Live sports event imported from the F1 schedule.",
                    "source": "Live Sports",
                }
            )

    return events


def fetch_team_events(team_name: str) -> list[dict]:
    """Fetch upcoming fixtures for a named team through TheSportsDB."""
    try:
        search_response = requests.get(
            "https://www.thesportsdb.com/api/v1/json/123/searchteams.php",
            params={"t": team_name},
            timeout=10,
        )
        search_response.raise_for_status()
        teams = search_response.json().get("teams") or []
    except Exception:
        return []

    if not teams:
        return []

    team_id = teams[0].get("idTeam")
    if not team_id:
        return []

    try:
        event_response = requests.get(
            "https://www.thesportsdb.com/api/v1/json/123/eventsnext.php",
            params={"id": team_id},
            timeout=10,
        )
        event_response.raise_for_status()
        fixtures = event_response.json().get("events") or []
    except Exception:
        return []

    results: list[dict] = []

    for fixture in fixtures:
        event_date = fixture.get("dateEvent")
        if not event_date:
            continue

        start = parse_api_time(
            fixture.get("strTime")
            or fixture.get("strTimestamp"),
            "18:00",
        )
        end = from_minutes(min(to_minutes(start) + 120, 1439))

        results.append(
            {
                "name": fixture.get("strEvent", f"{team_name} fixture"),
                "category": "Sports",
                "date": event_date,
                "start": start,
                "end": end,
                "notes": (
                    f"Upcoming fixture for {teams[0].get('strTeam', team_name)}."
                ),
                "source": "Live Sports",
            }
        )

    return results


def fetch_named_sports_events(
    query: str,
) -> list[dict]:
    try:
        response = requests.get(
            "https://www.thesportsdb.com/api/v1/json/123/searchevents.php",
            params={"e": query},
            timeout=10,
        )
        response.raise_for_status()
        fixtures = (
            response.json().get("event")
            or response.json().get("events")
            or []
        )
    except Exception:
        return []

    results: list[dict] = []

    for fixture in fixtures:
        event_date = fixture.get("dateEvent")
        if not event_date:
            continue

        try:
            parsed_date = date.fromisoformat(event_date)
        except ValueError:
            continue

        if parsed_date < now_local().date():
            continue

        start_time = parse_api_time(
            fixture.get("strTime")
            or fixture.get("strTimestamp"),
            "18:00",
        )
        end_time = from_minutes(
            min(to_minutes(start_time) + 120, 1439)
        )

        results.append(
            {
                "name": fixture.get("strEvent") or query,
                "category": "Sports",
                "date": event_date,
                "start": start_time,
                "end": end_time,
                "notes": "Imported from a live sports feed.",
                "source": "Live Sports",
            }
        )

    return results


def fetch_sports_candidates(interests: str) -> tuple[list[dict], str]:
    terms = [
        item.strip()
        for item in re.split(r"[,;\n]+", interests)
        if item.strip()
    ]

    candidates: list[dict] = []
    messages: list[str] = []

    for term in terms:
        lowered = term.lower()

        if any(
            value in lowered
            for value in ["f1", "formula 1", "formula one", "ferrari"]
        ):
            found = fetch_f1_events()
        else:
            found = fetch_team_events(term)

            if not found:
                found = fetch_named_sports_events(term)

        candidates.extend(found)

        if found:
            messages.append(
                f"Found {len(found)} upcoming event(s) for {term}."
            )
        else:
            messages.append(
                f"No reliable live dates were found for “{term}”. "
                "You can add it manually."
            )

    unique: dict[tuple[str, str, str], dict] = {}

    for event in candidates:
        key = (
            event["name"].lower(),
            event["date"],
            event["start"],
        )
        unique[key] = event

    ordered = sorted(
        unique.values(),
        key=lambda event: (
            event["date"],
            event["start"],
            event["name"],
        ),
    )

    return ordered[:50], " ".join(messages)

def show_sports_sync() -> None:
    page_header(
        "🏆",
        "Review sports events",
        "Sky found possible fixtures. Nothing is added until you approve it.",
    )

    interests = st.session_state.profile.get("sports_interests", "")

    st.write(
        f"Sports and teams: **{interests or 'None entered'}**"
    )

    col1, col2 = st.columns(2)

    if col1.button(
        "Search upcoming sports events",
        use_container_width=True,
    ):
        with st.spinner("Looking for upcoming fixtures..."):
            candidates, message = fetch_sports_candidates(interests)
            st.session_state.sports_candidates = candidates
            st.session_state.sports_sync_message = message
        st.rerun()

    if col2.button(
        "Skip sports sync",
        use_container_width=True,
    ):
        st.session_state.profile_done = True
        st.session_state.page = "Dashboard"
        st.rerun()

    if st.session_state.sports_sync_message:
        st.info(st.session_state.sports_sync_message)

    candidates = st.session_state.sports_candidates

    if not candidates:
        st.caption(
            "Search first, or skip this step and add sports events manually later."
        )
        return

    st.subheader("Select events to add")

    selected_events: list[dict] = []

    for index, event in enumerate(candidates):
        chosen = st.checkbox(
            (
                f"{event['date']} · {event['start']} · "
                f"{event['name']}"
            ),
            value=index < 8,
            key=f"sports_candidate_{index}",
        )

        if chosen:
            selected_events.append(event)

    if st.button(
        f"Add {len(selected_events)} selected event(s)",
        use_container_width=True,
        disabled=not selected_events,
    ):
        added = 0

        for event in selected_events:
            added += int(
                add_event(
                    name=event["name"],
                    category=event["category"],
                    event_date=event["date"],
                    start=event["start"],
                    end=event["end"],
                    notes=event["notes"],
                    source=event["source"],
                    major=True,
                )
            )

        st.session_state.profile_done = True
        st.session_state.page = "Dashboard"
        st.success(f"Added {added} sports event(s).")
        st.rerun()


def events_on(target: date) -> list[dict]:
    value = target.strftime("%Y-%m-%d")
    events = [e for e in st.session_state.events if e.get("date") == value]
    if not st.session_state.settings["show_sports"]:
        events = [e for e in events if e.get("category") != "Sports"]
    if not st.session_state.settings["show_ai_events"]:
        events = [e for e in events if e.get("source") != "AI Suggested"]
    return sorted(events, key=lambda e: e.get("start", "00:00"))


def upcoming_events(limit: int = 10) -> list[dict]:
    now = now_local()
    today_text = now.strftime("%Y-%m-%d")
    time_text = now.strftime("%H:%M")
    items = [
        e for e in st.session_state.events
        if e.get("date", "") > today_text
        or (e.get("date") == today_text and e.get("end", "00:00") >= time_text)
    ]
    return sorted(items, key=lambda e: (e.get("date", ""), e.get("start", "")))[:limit]


def free_slots(target: date) -> list[tuple[int, int]]:
    cursor = st.session_state.settings["day_start"] * 60
    day_end = st.session_state.settings["day_end"] * 60
    result = []
    for event in events_on(target):
        start = to_minutes(event["start"])
        end = to_minutes(event["end"])
        if start > cursor:
            result.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < day_end:
        result.append((cursor, day_end))
    return result


def free_hours(target: date) -> float:
    return max(sum(end - start for start, end in free_slots(target)) / 60, 0.0)


def event_duration_hours(event: dict) -> float:
    try:
        return max(
            to_minutes(event.get("end", "00:00"))
            - to_minutes(event.get("start", "00:00")),
            0,
        ) / 60
    except Exception:
        return 0.0


def current_week_days(reference: date | None = None) -> list[date]:
    reference = reference or now_local().date()
    start = reference - timedelta(days=reference.weekday())
    return [start + timedelta(days=index) for index in range(7)]


def weekly_workload(reference: date | None = None) -> dict[str, float]:
    days = current_week_days(reference)
    day_values = {day.isoformat() for day in days}

    totals = {
        "Study": 0.0,
        "Sports": 0.0,
        "Work": 0.0,
        "Recovery": 0.0,
        "Free Time": 0.0,
    }

    for event in st.session_state.events:
        if event.get("date") not in day_values:
            continue

        duration = event_duration_hours(event)
        category = event.get("category", "Other").lower()
        name = event.get("name", "").lower()

        if category in {"school", "study", "deadline"}:
            totals["Study"] += duration
        elif category in {"sports", "training"}:
            totals["Sports"] += duration
        elif category in {"meeting", "medical", "travel"} or "work" in category:
            totals["Work"] += duration
        elif category in {"free time", "personal"} and any(
            word in name for word in ["rest", "recovery", "break", "sleep"]
        ):
            totals["Recovery"] += duration

    totals["Free Time"] = sum(free_hours(day) for day in days)

    return {
        key: round(max(value, 0.0), 1)
        for key, value in totals.items()
    }


def burnout_analysis(reference: date | None = None) -> dict:
    totals = weekly_workload(reference)

    active_load = totals["Study"] + totals["Sports"] + totals["Work"]
    free_time = totals["Free Time"]
    recovery = totals["Recovery"]

    workload_score = min(active_load / 45 * 65, 65)
    low_free_penalty = max(0, 12 - free_time) / 12 * 25
    recovery_penalty = max(0, 4 - recovery) / 4 * 10

    score = int(
        round(
            min(
                max(
                    workload_score
                    + low_free_penalty
                    + recovery_penalty,
                    0,
                ),
                100,
            )
        )
    )

    if score <= 40:
        level = "Healthy"
        message = (
            "Your week looks balanced. Keep protecting your free time "
            "and recovery."
        )
    elif score <= 70:
        level = "Busy"
        message = (
            "Your workload is getting heavy. Sky recommends a lighter "
            "evening or a proper recovery break."
        )
    else:
        level = "High risk"
        message = (
            "Your schedule is overloaded. Reduce optional tasks and "
            "protect recovery before adding more work."
        )

    return {
        "score": score,
        "level": level,
        "message": message,
        "totals": totals,
    }


def render_weekly_availability(reference: date) -> None:
    days = current_week_days(reference)
    planning_hours = max(
        st.session_state.settings["day_end"]
        - st.session_state.settings["day_start"],
        1,
    )

    rows = []

    for day in days:
        hours = max(free_hours(day), 0.0)
        percentage = min(hours / planning_hours * 100, 100)
        rows.append(
            f"""
            <div class='availability-row'>
                <div class='availability-day'>{day.strftime('%a')}</div>
                <div class='availability-track'>
                    <div class='availability-fill'
                         style='width:{percentage:.1f}%;'></div>
                </div>
                <div class='availability-value'>{hours:.1f}h</div>
            </div>
            """
        )

    st.markdown("".join(rows), unsafe_allow_html=True)


def render_burnout_meter(score: int) -> None:
    safe_score = min(max(score, 0), 100)

    st.markdown(
        f"""
        <div class='burnout-track'>
            <div class='burnout-marker'
                 style='left:{safe_score}%;'></div>
        </div>
        <div class='burnout-zones'>
            <span>Healthy 0–40</span>
            <span>Busy 41–70</span>
            <span>High risk 71–100</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_event(event: dict, detailed: bool = False) -> None:
    name = escape(str(event.get("name", "Event")))
    category = escape(str(event.get("category", "Other")))
    details = []
    if detailed and event.get("people"):
        details.append(f"With: {escape(event['people'])}")
    if detailed and event.get("needs"):
        details.append(f"Bring: {escape(event['needs'])}")
    if detailed and event.get("notes"):
        details.append(f"Notes: {escape(event['notes'])}")
    if detailed and event.get("result"):
        details.append(f"Reflection: {escape(event['result'])}")
    extra = "<br>" + "<br>".join(details) if details else ""
    st.markdown(
        f"""
        <div class='event-card' style='background:{event_color(event.get('category','Other'))};'>
            <div class='event-title'>{event_icon(event.get('category','Other'))} {name}</div>
            <div class='event-meta'>{escape(event.get('date',''))} · {escape(event.get('start',''))}–{escape(event.get('end',''))} · {category}{extra}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# ROUTINE PARSER (OFFLINE)
# -----------------------------
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def parse_time(raw: str) -> str | None:
    raw = raw.lower().replace(".", "").strip()
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", raw)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    marker = match.group(3)
    if marker == "pm" and hour != 12:
        hour += 12
    if marker == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def infer_category(name: str) -> str:
    value = name.lower()
    mappings = [
        (["school", "class", "lesson"], "School"),
        (["study", "revision", "homework"], "Study"),
        (["surgery", "clinic", "patient", "hospital", "ward"], "Medical"),
        (["training", "practice", "gym"], "Training"),
        (["match", "basketball", "football", "tennis", "race", "f1", "sport"], "Sports"),
        (["test", "exam", "deadline", "assignment"], "Deadline"),
        (["meeting", "call", "interview"], "Meeting"),
        (["flight", "hotel", "travel"], "Travel"),
    ]
    for words, category in mappings:
        if any(word in value for word in words):
            return category
    return "Other"


def expand_days(text: str) -> list[str]:
    lower = text.lower()
    range_match = re.search(
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+to\s+"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        lower,
    )
    if range_match:
        start = DAY_NAMES.index(range_match.group(1).title())
        end = DAY_NAMES.index(range_match.group(2).title())
        return DAY_NAMES[start:end + 1] if start <= end else []
    return [day for day in DAY_NAMES if day.lower() in lower]


def next_dates(day_name: str, weeks: int = 6) -> list[date]:
    today = now_local().date()
    offset = (DAY_NAMES.index(day_name) - today.weekday()) % 7
    first = today + timedelta(days=offset)
    return [first + timedelta(days=7 * i) for i in range(weeks)]


def clean_event_name(sentence: str, day_match_start: int) -> str:
    name = sentence[:day_match_start].strip(" ,.-")
    name = re.sub(r"^(i have|i do|my|the)\s+", "", name, flags=re.IGNORECASE)
    return name.title() if name else "Routine Event"


def parse_routine(text: str) -> int:
    count = 0
    sentences = [s.strip() for s in re.split(r"[\n.;]+", text) if s.strip()]
    day_pattern = re.compile(
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        r"(?:\s+to\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday))?"
        r"(?:\s*(?:,|and)\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday))*",
        re.IGNORECASE,
    )
    time_pattern = re.compile(
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:to|-)\s*"
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
        re.IGNORECASE,
    )
    month_pattern = re.compile(
        r"(.+?)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})"
        r"(?:\s+at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?"
        r"(?:\s*(?:to|-)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?))?",
        re.IGNORECASE,
    )
    for sentence in sentences:
        specific = month_pattern.search(sentence)
        if specific:
            name, month_name, day_number, start_raw, end_raw = specific.groups()
            year = now_local().year
            try:
                target = datetime.strptime(f"{month_name} {day_number} {year}", "%B %d %Y").date()
                if target < now_local().date():
                    target = target.replace(year=year + 1)
            except ValueError:
                continue
            start = parse_time(start_raw or "09:00") or "09:00"
            end = parse_time(end_raw or "") or from_minutes(min(to_minutes(start) + 60, 1439))
            count += int(add_event(name.strip().title(), infer_category(name), target.isoformat(), start, end, source="Profile Routine"))
            continue
        day_match = day_pattern.search(sentence)
        time_match = time_pattern.search(sentence)
        if not day_match or not time_match:
            continue
        days = expand_days(day_match.group(0))
        start = parse_time(time_match.group(1))
        end = parse_time(time_match.group(2))
        if not days or not start or not end:
            continue
        name = clean_event_name(sentence, day_match.start())
        for day_name in days:
            for target in next_dates(day_name):
                count += int(add_event(name, infer_category(name), target.isoformat(), start, end, source="Profile Routine", major=infer_category(name) in {"Sports", "Medical", "Deadline", "Meeting"}))
    return count


# -----------------------------
# OPTIONAL GEMINI + OFFLINE ASSISTANT
# -----------------------------
def gemini_available() -> bool:
    key = os.getenv("GOOGLE_API_KEY")
    try:
        key = key or st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        pass
    return bool(genai and key and st.session_state.settings["use_gemini"])


def ask_gemini(prompt: str) -> str | None:
    if not gemini_available():
        return None
    try:
        key = os.getenv("GOOGLE_API_KEY")
        try:
            key = key or st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            pass
        genai.configure(api_key=key)
        model = genai.GenerativeModel(st.session_state.settings["gemini_model"])
        return model.generate_content(prompt).text
    except Exception:
        return None


def question_date(question: str) -> date:
    lower = question.lower()
    today = now_local().date()
    if "tomorrow" in lower:
        return today + timedelta(days=1)
    if "today" in lower:
        return today
    for day in DAY_NAMES:
        if day.lower() in lower:
            return today + timedelta(days=(DAY_NAMES.index(day) - today.weekday()) % 7)
    return today


def matching_events(question: str, future_only: bool = False) -> list[dict]:
    stop = {"when", "is", "my", "next", "what", "the", "a", "an", "do", "i", "have", "with"}
    words = {w for w in re.findall(r"[a-z0-9]+", question.lower()) if w not in stop}
    events = upcoming_events(100) if future_only else st.session_state.events
    scored = []
    for event in events:
        text = " ".join([event.get("name", ""), event.get("category", ""), event.get("people", "")]).lower()
        score = sum(1 for word in words if word in text)
        if score:
            scored.append((score, event))
    return [event for _, event in sorted(scored, key=lambda x: (-x[0], x[1].get("date", ""), x[1].get("start", "")))]


def event_datetime(event: dict) -> datetime:
    return datetime.strptime(
        f"{event.get('date')} {event.get('start', '00:00')}",
        "%Y-%m-%d %H:%M",
    )


def event_end_datetime(event: dict) -> datetime:
    return datetime.strptime(
        f"{event.get('date')} {event.get('end', '00:00')}",
        "%Y-%m-%d %H:%M",
    )


def is_deadline_event(event: dict) -> bool:
    searchable = f"{event.get('name', '')} {event.get('category', '')}".lower()
    return event.get("category") == "Deadline" or any(
        word in searchable
        for word in ["test", "exam", "deadline", "assessment", "quiz"]
    )


def resolve_focus_event(question: str) -> dict | None:
    """Find the event being discussed and remember it for follow-up questions."""
    lower = question.lower()
    matches = matching_events(question, future_only=True)

    study_words = [
        "study", "revise", "revision", "prepare", "exam", "test", "quiz"
    ]

    if any(word in lower for word in study_words):
        deadline_matches = [event for event in matches if is_deadline_event(event)]
        if deadline_matches:
            focus = deadline_matches[0]
            st.session_state.assistant_focus_event = focus
            return focus

        future_deadlines = [
            event for event in upcoming_events(100) if is_deadline_event(event)
        ]
        if future_deadlines:
            focus = future_deadlines[0]
            st.session_state.assistant_focus_event = focus
            return focus

    if matches:
        focus = matches[0]
        st.session_state.assistant_focus_event = focus
        return focus

    pronouns = ["it", "that", "this", "the test", "the exam", "for it"]
    if any(phrase in lower for phrase in pronouns):
        return st.session_state.get("assistant_focus_event")

    return st.session_state.get("assistant_focus_event")


def unfiltered_events_on(target: date) -> list[dict]:
    value = target.isoformat()
    return sorted(
        [event for event in st.session_state.events if event.get("date") == value],
        key=lambda event: event.get("start", "00:00"),
    )


def safe_free_slots(target: date) -> list[tuple[int, int]]:
    """Calculate real free time using every event, even hidden display categories."""
    cursor = st.session_state.settings["day_start"] * 60
    day_end = st.session_state.settings["day_end"] * 60
    slots: list[tuple[int, int]] = []

    for event in unfiltered_events_on(target):
        start = max(to_minutes(event["start"]), cursor)
        end = min(to_minutes(event["end"]), day_end)

        if end <= cursor:
            continue
        if start > cursor:
            slots.append((cursor, start))
        cursor = max(cursor, end)

    if cursor < day_end:
        slots.append((cursor, day_end))

    return slots


def nearby_context(target_event: dict, days_before: int = 3) -> list[dict]:
    target_date = datetime.strptime(target_event["date"], "%Y-%m-%d").date()
    start_date = target_date - timedelta(days=days_before)

    return sorted(
        [
            event
            for event in st.session_state.events
            if start_date.isoformat() <= event.get("date", "") <= target_event["date"]
            and event is not target_event
        ],
        key=lambda event: (event.get("date", ""), event.get("start", "")),
    )


def create_preparation_plan(target_event: dict) -> list[dict]:
    """Build recovery-aware sessions before an exam, deadline, or important event."""
    target_date = datetime.strptime(target_event["date"], "%Y-%m-%d").date()
    today = now_local().date()
    first_day = max(today, target_date - timedelta(days=5))
    candidates: list[dict] = []

    current = first_day
    while current < target_date:
        day_events = unfiltered_events_on(current)
        sport_events = [
            event
            for event in day_events
            if event.get("category") in {"Sports", "Training"}
        ]

        for slot_start, slot_end in safe_free_slots(current):
            if slot_end - slot_start < 45:
                continue

            suggested_start = slot_start
            recovery_note = ""

            # If a free slot begins after sport, protect at least 30 minutes of recovery.
            preceding_sports = [
                event
                for event in sport_events
                if to_minutes(event["end"]) <= slot_start
            ]
            if preceding_sports:
                last_sport = max(preceding_sports, key=lambda event: event["end"])
                suggested_start = max(
                    suggested_start,
                    to_minutes(last_sport["end"]) + 30,
                )
                recovery_note = (
                    f"This starts 30 minutes after {last_sport['name']} "
                    "so you have time to recover, eat, and reset."
                )

            # Prefer focused sessions, not huge blocks.
            available = slot_end - suggested_start
            if available < 30:
                continue

            duration = 60 if available >= 60 else 45 if available >= 45 else 30
            suggested_end = suggested_start + duration

            # Avoid suggesting very late study unless there is no better option.
            late_penalty = 2 if suggested_start >= 20 * 60 else 0
            day_distance = (target_date - current).days
            priority = day_distance + late_penalty

            candidates.append(
                {
                    "title": f"Prepare for {target_event['name']}",
                    "category": "Study",
                    "date": current.isoformat(),
                    "start": from_minutes(suggested_start),
                    "end": from_minutes(suggested_end),
                    "notes": (
                        f"Focused preparation for {target_event['name']}. "
                        + recovery_note
                    ).strip(),
                    "reason": recovery_note or "This fits inside a genuine free block.",
                    "priority": priority,
                }
            )

        current += timedelta(days=1)

    candidates.sort(key=lambda item: (item["priority"], item["date"], item["start"]))

    # Use a maximum of three sessions and avoid putting all of them on one day.
    selected: list[dict] = []
    used_dates: set[str] = set()

    for candidate in candidates:
        if candidate["date"] not in used_dates or len(selected) == 0:
            selected.append(candidate)
            used_dates.add(candidate["date"])
        if len(selected) == 3:
            break

    if not selected:
        return []

    for item in selected:
        item.pop("priority", None)
    return selected


def describe_context(target_event: dict) -> str:
    nearby = nearby_context(target_event, days_before=3)
    if not nearby:
        return "I did not find another major event immediately before it."

    lines = []
    for event in nearby[-4:]:
        lines.append(
            f"• {event['name']} on {event['date']} from {event['start']} to {event['end']}"
        )
    return "Nearby commitments:\n" + "\n".join(lines)


def planning_answer(question: str, focus: dict) -> str:
    plans = create_preparation_plan(focus)
    st.session_state.pending_ai_plans = plans

    context = describe_context(focus)
    if not plans:
        return (
            f"**{focus['name']}** is on **{focus['date']}** from "
            f"**{focus['start']} to {focus['end']}**.\n\n"
            f"{context}\n\n"
            "I could not find a safe preparation block before it inside your planning hours. "
            "You may need to shorten, move, or remove another event."
        )

    plan_lines = [
        f"• **{plan['date']}**, {plan['start']}–{plan['end']}: {plan['reason']}"
        for plan in plans
    ]

    return (
        f"**{focus['name']}** is on **{focus['date']}** from "
        f"**{focus['start']} to {focus['end']}**.\n\n"
        f"{context}\n\n"
        "I recommend these preparation sessions:\n\n"
        + "\n".join(plan_lines)
        + "\n\nYou can review and add any of them to your calendar below."
    )


def local_answer(question: str) -> str:
    lower = question.lower()
    target = question_date(question)
    day_events = unfiltered_events_on(target)
    matches = matching_events(question, future_only=True)
    focus = resolve_focus_event(question)

    if not st.session_state.events:
        return "Your calendar is empty. Add an event or rebuild your schedule from Settings."

    planning_words = [
        "study", "revise", "revision", "prepare", "plan", "practice",
        "when can i", "help me", "make time", "fit in"
    ]
    if focus and any(word in lower for word in planning_words):
        return planning_answer(question, focus)

    if "next" in lower and matches:
        event = matches[0]
        st.session_state.assistant_focus_event = event
        return (
            f"Your next **{event['name']}** is on **{event['date']}** "
            f"from **{event['start']} to {event['end']}**."
        )

    if any(word in lower for word in ["free", "available"]):
        slots = safe_free_slots(target)
        if not slots:
            return f"You have no free time on **{target.strftime('%A, %d %B')}** within your planning hours."
        lines = [
            f"• {from_minutes(start)}–{from_minutes(end)} ({(end-start)/60:.1f} hours)"
            for start, end in slots
        ]
        return (
            f"Your free time on **{target.strftime('%A, %d %B')}** is:\n\n"
            + "\n".join(lines)
        )

    if any(word in lower for word in ["between", "gap"]):
        if len(day_events) < 2:
            return "There are not enough events that day to calculate a gap."
        lines = []
        for first, second in zip(day_events, day_events[1:]):
            gap = to_minutes(second["start"]) - to_minutes(first["end"])
            if gap >= 0:
                lines.append(f"• {gap} minutes between {first['name']} and {second['name']}")
        return "\n".join(lines) if lines else "Your events overlap."

    if any(word in lower for word in ["who", "with"]):
        if focus and focus.get("people"):
            return f"**{focus['name']}** is with **{focus['people']}**."
        return "I could not find a person attached to that event."

    if any(word in lower for word in ["need", "bring"]):
        if focus and focus.get("needs"):
            return f"For **{focus['name']}**, you need **{focus['needs']}**."
        return "I could not find a preparation note for that event."

    if matches:
        event = matches[0]
        st.session_state.assistant_focus_event = event
        return (
            f"**{event['name']}** is on **{event['date']}** "
            f"from **{event['start']} to {event['end']}**."
        )

    if any(word in lower for word in ["schedule", "tomorrow", "today", "have"]):
        if not day_events:
            return f"You have no events on **{target.strftime('%A, %d %B')}**."
        return (
            f"Your schedule for **{target.strftime('%A, %d %B')}**:\n\n"
            + "\n".join(
                f"• {event['start']}–{event['end']}: {event['name']}"
                for event in day_events
            )
        )

    analysis = burnout_analysis(target)
    next_items = upcoming_events(5)

    next_lines = (
        "\n".join(
            f"• {item['date']} {item['start']} — {item['name']}"
            for item in next_items
        )
        if next_items
        else "• No upcoming events found."
    )

    return (
        f"Your burnout score is **{analysis['score']}/100 "
        f"({analysis['level']})**. {analysis['message']}\n\n"
        f"Your next events are:\n{next_lines}\n\n"
        "Ask me to plan your week, find study time, protect recovery "
        "after training, compare commitments, or suggest an event."
    )


def assistant_answer(question: str) -> str:
    local = local_answer(question)
    tone = st.session_state.settings["ai_tone"]
    recent_history = st.session_state.chat_history[-6:]
    focus = st.session_state.get("assistant_focus_event")
    plans = st.session_state.get("pending_ai_plans", [])

    prompt = f"""
You are Sky, a proactive and intelligent calendar coach. Tone: {tone}.

Your responsibilities:
- understand the user's actual planning goal, not only the literal question;
- connect school, exams, deadlines, sports, work, travel, sleep, breaks, and recovery;
- remember follow-up references such as 'it', 'that', 'the match', and 'the test';
- compare nearby commitments and explain how one affects another;
- recommend one to three realistic actions inside confirmed free time;
- protect recovery after sport and avoid unnecessary late-night work;
- notice conflicts, overload, missing breaks, and long active streaks;
- give a useful weekly plan when the request is broad;
- never silently add an event;
- only offer events that the user can review and approve;
- never invent dates, fixtures, people, events, or times;
- clearly say when live sports information is unavailable.

Profile: {json.dumps(st.session_state.profile)}
Events: {json.dumps(st.session_state.events)}
Recent conversation: {json.dumps(recent_history)}
Current focus event: {json.dumps(focus)}
Approved plan candidates: {json.dumps(plans)}
Question: {question}
Verified local analysis: {local}

Answer naturally and explain why the suggested timing works. Keep it concise.
"""
    return ask_gemini(prompt) or local


# -----------------------------
# AI PLANNING SUGGESTIONS
# -----------------------------
def build_suggestion() -> dict | None:
    deadlines = [e for e in upcoming_events(30) if e.get("category") == "Deadline"]
    if not deadlines:
        return None
    deadline = deadlines[0]
    deadline_date = datetime.strptime(deadline["date"], "%Y-%m-%d").date()
    candidate_days = [deadline_date - timedelta(days=i) for i in range(1, 4)]
    for candidate in candidate_days:
        slots = free_slots(candidate)
        for start, end in slots:
            if end - start >= 105:
                rest_start = start
                study_start = start + 60
                study_end = study_start + 45
                return {
                    "title": f"Prepare for {deadline['name']}",
                    "date": candidate.isoformat(),
                    "start": from_minutes(study_start),
                    "end": from_minutes(study_end),
                    "reason": f"You have {deadline['name']} on {deadline['date']}. This fits after a 1-hour rest inside a free block.",
                    "notes": "Rest for one hour first, then complete a focused 45-minute review. Review key notes during travel if safe and practical.",
                }
    return None

    st.divider()
    st.subheader("Add any sport manually")

    with st.form("manual_sports_event"):
        event_name = st.text_input(
            "Event name",
            placeholder="Badminton tournament",
        )
        sport_type = st.selectbox(
            "Sport",
            SPORT_CATALOG,
        )
        event_date = st.date_input(
            "Date",
            now_local().date(),
        )
        start_time = st.time_input(
            "Start",
            time(12, 0),
        )
        end_time = st.time_input(
            "End",
            time(14, 0),
        )
        notes = st.text_area("Notes")
        submitted = st.form_submit_button(
            "Add sports event",
            use_container_width=True,
        )

    if submitted:
        if not event_name.strip():
            st.warning("Enter an event name.")
        elif end_time <= start_time:
            st.error("End time must be after start time.")
        else:
            created = add_event(
                event_name,
                "Sports",
                event_date.isoformat(),
                start_time.strftime("%H:%M"),
                end_time.strftime("%H:%M"),
                notes=f"{sport_type}. {notes}".strip(),
                source="Manual Sports",
                major=True,
            )

            if created:
                st.success("Sports event added.")
            else:
                st.warning("That event already exists.")


# -----------------------------
# ONBOARDING
# -----------------------------
def show_welcome() -> None:
    st.markdown(
        """
        <div class='hero'>
            <h1>Welcome to DayPilot AI</h1>
            <p>Your personal planner for school, work, sports, health, travel, and everything in between. Build a schedule that adapts to your life and helps you make better use of your free time.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Choose your theme")
    selected_theme = st.selectbox(
        "Theme",
        list(THEME_PRESETS.keys()),
        index=list(THEME_PRESETS.keys()).index(st.session_state.get("selected_theme", DEFAULT_THEME_NAME)),
        key="welcome_theme_picker",
        label_visibility="collapsed",
    )

    if selected_theme != st.session_state.get("selected_theme"):
        st.session_state.selected_theme = selected_theme
        set_theme(selected_theme)
        st.rerun()

    render_theme_preview(selected_theme)

    c1, c2, c3 = st.columns(3)
    c1.info("📅 Smart calendar\n\nTurn routines into useful weekly and monthly plans.")
    c2.info("🤖 Helpful assistant\n\nAsk about free time, events, preparation, and priorities.")
    c3.info("🎨 Your style\n\nChange themes later and keep every event color fully custom.")

    if st.button("Get Started →", use_container_width=True):
        set_theme(selected_theme)
        st.session_state.onboarding_step = 2
        st.rerun()


def show_profession() -> None:
    page_header("👋", "What best describes you?", "Choose a suggestion or enter your own profession.")
    choice = st.selectbox("Profession suggestion", PROFESSION_SUGGESTIONS, index=PROFESSION_SUGGESTIONS.index(st.session_state.profession_choice))
    custom = ""
    if choice == "Other / Custom":
        custom = st.text_input("Type your profession", value=st.session_state.custom_profession, placeholder="Pilot, lawyer, coach, designer...")
    profession = custom.strip() if choice == "Other / Custom" else choice
    if st.button("Continue →", use_container_width=True):
        if not profession:
            st.warning("Please enter your profession.")
        else:
            st.session_state.profession_choice = choice
            st.session_state.custom_profession = custom
            st.session_state.profile["profession"] = profession
            st.session_state.onboarding_step = 3
            st.rerun()


def show_profile_questions() -> None:
    profession = st.session_state.profile.get("profession", "Student")
    role = profession.lower()

    page_header(
        "✨",
        "Personalize DayPilot",
        (
            f"Build reliable recurring schedules for your role: "
            f"{profession}."
        ),
    )

    st.caption(
        "Recurring schedules are created from structured choices, "
        "so Monday–Friday school and weekly training appear correctly."
    )

    name = st.text_input("Name")
    goal = st.text_input(
        "Main goal",
        placeholder="Balance school, training, recovery, and free time...",
    )

    areas = st.multiselect(
        "What should DayPilot help manage?",
        MANAGEMENT_AREAS,
        default=(
            ["School", "Study", "Sports"]
            if "athlete" in role
            else ["School", "Study"]
            if "student" in role
            else ["Work"]
        ),
    )

    schedules: list[dict] = []

    if "student" in role:
        schedules.append(
            schedule_block(
                title="School timetable",
                key_prefix="school",
                default_name="School",
                default_category="School",
                default_pattern="Weekdays (Monday–Friday)",
                default_days=[
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                ],
            )
        )

    if "athlete" in role or "Sports" in areas:
        schedules.append(
            schedule_block(
                title="Training",
                key_prefix="training",
                default_name="Training",
                default_category="Training",
                default_pattern="Weekly",
                default_days=["Tuesday", "Thursday"],
            )
        )

        schedules.append(
            schedule_block(
                title="Matches or competitions",
                key_prefix="matches",
                default_name="Match",
                default_category="Sports",
                default_pattern="Different each week / add manually",
                default_days=[],
            )
        )

        schedules.append(
            schedule_block(
                title="Recovery",
                key_prefix="recovery",
                default_name="Recovery session",
                default_category="Free Time",
                default_pattern="Weekly",
                default_days=["Wednesday"],
            )
        )

    elif "surgeon" in role:
        schedules.extend(
            [
                schedule_block(
                    "Clinic hours",
                    "clinic",
                    "Clinic",
                    "Medical",
                    "Weekly",
                    ["Tuesday"],
                ),
                schedule_block(
                    "Ward rounds",
                    "ward_rounds",
                    "Ward rounds",
                    "Medical",
                    "Weekly",
                    ["Monday", "Wednesday", "Friday"],
                ),
                schedule_block(
                    "Surgery schedule",
                    "surgery",
                    "Surgery",
                    "Medical",
                    "Different each week / add manually",
                    [],
                ),
                schedule_block(
                    "On-call shifts",
                    "on_call",
                    "On-call",
                    "Medical",
                    "Different each week / add manually",
                    [],
                ),
            ]
        )

    elif "doctor" in role:
        schedules.extend(
            [
                schedule_block(
                    "Clinic hours",
                    "clinic",
                    "Clinic",
                    "Medical",
                    "Weekly",
                    ["Monday", "Tuesday", "Wednesday"],
                ),
                schedule_block(
                    "Ward rounds",
                    "ward_rounds",
                    "Ward rounds",
                    "Medical",
                    "Weekly",
                    ["Friday"],
                ),
                schedule_block(
                    "On-call shifts",
                    "on_call",
                    "On-call",
                    "Medical",
                    "Different each week / add manually",
                    [],
                ),
            ]
        )

    elif "teacher" in role:
        schedules.append(
            schedule_block(
                "Teaching timetable",
                "teaching",
                "Teaching",
                "School",
                "Weekdays (Monday–Friday)",
                [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                ],
            )
        )

    elif not any(
        word in role
        for word in ["student", "doctor", "surgeon", "teacher"]
    ):
        schedules.append(
            schedule_block(
                "Work schedule",
                "work",
                "Work",
                "Meeting",
                "Weekdays (Monday–Friday)",
                [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                ],
            )
        )

    st.subheader("Deadlines and one-time events")

    upcoming = st.text_area(
        "Exams, appointments, matches, or deadlines",
        placeholder=(
            "Biology test July 18 at 9am to 10am. "
            "Dentist July 20 at 4pm to 5pm."
        ),
    )

    sports_enabled = "Sports" in areas or "athlete" in role

    sports_interests = ""

    if sports_enabled:
        st.subheader("Sports you follow")

        selected_sports = st.multiselect(
            "Sports you follow",
            SPORT_CATALOG,
            default=["Basketball"],
        )

        sports_interests = st.text_area(
            "Teams, leagues, athletes, or tournaments",
            placeholder=(
                "FIFA World Cup, Olympics, Arsenal, Lakers, "
                "Wimbledon, badminton"
            ),
            help=(
                "Use exact names where possible. "
                "You review every event before it is added."
            ),
        )

    timezone_choice = st.selectbox(
        "Timezone",
        TIMEZONES,
        index=TIMEZONES.index("Asia/Dubai"),
    )

    custom_timezone = (
        st.text_input(
            "Custom timezone",
            placeholder="Europe/Zurich",
        )
        if timezone_choice == "Other / Custom"
        else ""
    )

    if st.button(
        "Build My DayPilot",
        use_container_width=True,
    ):
        timezone = (
            custom_timezone.strip()
            if timezone_choice == "Other / Custom"
            else timezone_choice
        )

        try:
            ZoneInfo(timezone)
        except Exception:
            st.error(
                "Invalid timezone. Try Asia/Dubai or Europe/London."
            )
            return

        for schedule in schedules:
            if (
                schedule["enabled"]
                and schedule["end_time"] <= schedule["start_time"]
            ):
                st.error(
                    f"{schedule['name']}: end time must be after start time."
                )
                return

            if (
                schedule["enabled"]
                and schedule["pattern"] in {"Weekly", "Custom days"}
                and not schedule["selected_days"]
            ):
                st.error(
                    f"{schedule['name']}: choose at least one day."
                )
                return

        st.session_state.profile.update(
            {
                "name": name,
                "goal": goal,
                "management_areas": areas,
                "sports_interests": sports_interests,
                "selected_sports": selected_sports if sports_enabled else [],
                "upcoming": upcoming,
                "timezone": timezone,
            }
        )

        added = 0
        skipped = 0

        for schedule in schedules:
            created, ignored = apply_schedule_block(
                schedule,
                source="Onboarding recurrence",
            )
            added += created
            skipped += ignored

        added += parse_routine(upcoming)
        st.session_state.onboarding_added_count = added

        if sports_enabled and sports_interests.strip():
            st.session_state.onboarding_step = 4
            st.session_state.sports_candidates = []
            st.session_state.sports_sync_message = ""
        else:
            st.session_state.profile_done = True
            st.session_state.page = "Dashboard"

        st.success(
            f"Added {added} calendar event(s). "
            f"Skipped {skipped} duplicate event(s)."
        )
        st.rerun()


# -----------------------------
# SIDEBAR
# -----------------------------
def sidebar() -> None:
    if not st.session_state.profile_done:
        st.sidebar.markdown("## 📅 DayPilot AI")
        st.sidebar.caption("Complete onboarding to unlock all features.")
        return
    st.sidebar.markdown("## 📅 DayPilot AI")
    for label, icon in [("Dashboard", "🏠"), ("Calendar", "📅"), ("Assistant", "💬")]:
        if st.sidebar.button(f"{icon} {label}", use_container_width=True):
            st.session_state.page = label
            st.rerun()
    st.sidebar.divider()
    if st.sidebar.button("⚙️ Settings", use_container_width=True):
        st.session_state.page = "Settings"
        st.rerun()
    st.sidebar.divider()
    st.sidebar.caption(f"{st.session_state.profile.get('profession', '')}")
    st.sidebar.caption(f"Timezone: {st.session_state.profile.get('timezone', 'UTC')}")
    st.sidebar.info("Gemini available" if gemini_available() else "Offline assistant active")


sidebar()


# -----------------------------
# MAIN FLOW
# -----------------------------
if not st.session_state.profile_done:
    if st.session_state.onboarding_step == 1:
        show_welcome()
    elif st.session_state.onboarding_step == 2:
        show_profession()
    elif st.session_state.onboarding_step == 3:
        show_profile_questions()
    else:
        show_sports_sync()

elif st.session_state.page == "Dashboard":
    today = now_local().date()
    today_events = events_on(today)
    upcoming = upcoming_events(6)
    burnout = burnout_analysis(today)
    workload = burnout["totals"]

    page_header(
        "🏠",
        f"Welcome back, {st.session_state.profile.get('name', 'there')}",
        (
            f"{today.strftime('%A, %d %B %Y')} · "
            f"{st.session_state.profile.get('timezone', 'UTC')}"
        ),
    )

    metrics = [
        ("Events Today", len(today_events)),
        ("Free Today", f"{free_hours(today):.1f} h"),
        (
            "Active Load",
            f"{workload['Study'] + workload['Sports'] + workload['Work']:.1f} h",
        ),
        ("Burnout Level", burnout["level"]),
    ]

    cols = st.columns(4)
    for col, (label, value) in zip(cols, metrics):
        col.markdown(
            (
                "<div class='metric-card'>"
                f"<div class='metric-label'>{escape(str(label))}</div>"
                f"<div class='metric-value'>{escape(str(value))}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    st.write("")

    left, right = st.columns([1.55, 1], gap="large")

    with left:
        with st.container(border=True):
            st.subheader("Today’s Schedule")

            if today_events:
                for event in today_events:
                    render_event(event, detailed=True)
            else:
                st.info("No events today.")

    with right:
        with st.container(border=True):
            st.subheader("Upcoming Events")

            if upcoming:
                for event in upcoming:
                    render_event(event)
            else:
                st.info("No upcoming events.")

    st.write("")

    availability_col, burnout_col = st.columns(2, gap="large")

    with availability_col:
        with st.container(border=True):
            st.subheader("Weekly Availability")
            st.caption(
                "A simple view of how many genuinely free hours "
                "you have each day."
            )
            render_weekly_availability(today)
            st.caption(
                f"Total free time this week: "
                f"{workload['Free Time']:.1f} hours"
            )

    with burnout_col:
        with st.container(border=True):
            st.subheader("Burnout Monitor")
            st.caption(
                "Based on study, sport, work, free time, and recovery."
            )
            st.markdown(
                (
                    f"<div class='burnout-score'>{burnout['score']} / 100</div>"
                    f"<div class='burnout-level'>{burnout['level']}</div>"
                ),
                unsafe_allow_html=True,
            )
            render_burnout_meter(burnout["score"])
            st.info(burnout["message"])
            st.caption(
                "This is a planning signal, not a medical diagnosis."
            )

    with st.container(border=True):
        st.subheader("Sky’s Planning Insight")

        suggestion = build_suggestion()

        if suggestion:
            st.write(suggestion["reason"])
            st.caption(suggestion["notes"])

            if st.button(
                "Review Suggestion",
                use_container_width=True,
            ):
                st.session_state.pending_suggestion = suggestion
                st.rerun()
        else:
            st.info(
                "Add a deadline or exam and Sky will look for "
                "a safe study slot."
            )

    if st.session_state.pending_suggestion:
        s = st.session_state.pending_suggestion

        with st.container(border=True):
            st.subheader("Edit AI Suggestion")

            title = st.text_input(
                "Title",
                s["title"],
                key="suggest_title",
            )

            s_date = st.date_input(
                "Date",
                datetime.strptime(s["date"], "%Y-%m-%d").date(),
                key="suggest_date",
            )

            c1, c2 = st.columns(2)

            s_start = c1.time_input(
                "Start",
                datetime.strptime(s["start"], "%H:%M").time(),
                key="suggest_start",
            )

            s_end = c2.time_input(
                "End",
                datetime.strptime(s["end"], "%H:%M").time(),
                key="suggest_end",
            )

            notes = st.text_area(
                "Notes",
                s["notes"],
                key="suggest_notes",
            )

            b1, b2 = st.columns(2)

            if b1.button(
                "Add to Calendar",
                use_container_width=True,
            ):
                add_event(
                    title,
                    "AI Suggested",
                    s_date.isoformat(),
                    s_start.strftime("%H:%M"),
                    s_end.strftime("%H:%M"),
                    notes=notes,
                    source="AI Suggested",
                )

                st.session_state.pending_suggestion = None
                st.success("AI suggestion added.")
                st.rerun()

            if b2.button(
                "Cancel",
                use_container_width=True,
            ):
                st.session_state.pending_suggestion = None
                st.rerun()

    if st.session_state.settings["save_reflections"]:
        st.subheader("Notes and Reflections")

        for index, event in enumerate(today_events):
            with st.expander(
                f"{event_icon(event['category'])} "
                f"{event['start']} — {event['name']}"
            ):
                notes = st.text_area(
                    "Notes or homework",
                    event.get("notes", ""),
                    key=f"note_{index}",
                )

                result = st.text_input(
                    "Result or reflection",
                    event.get("result", ""),
                    key=f"result_{index}",
                )

                if st.button(
                    "Save",
                    key=f"save_{index}",
                ):
                    event["notes"] = notes
                    event["result"] = result
                    st.success("Saved.")

elif st.session_state.page == "Calendar":
    page_header("📅", "Calendar", "Switch between a detailed weekly plan and a compact monthly overview.")
    view = st.segmented_control("Calendar view", ["Week", "Month"], default=st.session_state.settings["default_calendar_view"])
    with st.expander("➕ Add Event", expanded=False):
        with st.form("add_event"):
            c1, c2 = st.columns(2)

            name = c1.text_input("Event name")
            category = c1.text_input("Category", "Personal")
            event_date = c1.date_input(
                "Starts on",
                now_local().date(),
            )
            start = c1.time_input("Start", time(9, 0))
            end = c1.time_input("End", time(10, 0))

            color = c2.color_picker(
                "Color",
                st.session_state.colors.get(
                    category,
                    "#4F46E5",
                ),
            )
            people = c2.text_input("Who is involved?")
            needs = c2.text_input("What do you need?")
            notes = c2.text_area("Notes")
            major = c2.checkbox("Show in Month View", True)

            st.markdown("#### Repeat")

            repeat_pattern = st.selectbox(
                "How often?",
                [
                    "Does not repeat",
                    "Daily",
                    "Weekdays (Monday–Friday)",
                    "Weekly",
                    "Custom days",
                ],
            )

            repeat_days = st.multiselect(
                "Repeat on",
                DAY_NAMES,
                default=[DAY_NAMES[event_date.weekday()]],
            )

            repeat_until = st.date_input(
                "Repeat until",
                event_date + timedelta(days=30),
            )

            submit = st.form_submit_button(
                "Add Event",
                use_container_width=True,
            )

        if submit:
            clean_category = category.strip() or "Other"

            if not name.strip():
                st.warning("Enter an event name.")
            elif end <= start:
                st.error("End time must be after start time.")
            elif (
                repeat_pattern in {"Weekly", "Custom days"}
                and not repeat_days
            ):
                st.error("Choose at least one repeat day.")
            elif repeat_until < event_date:
                st.error("Repeat-until date cannot be before the start date.")
            else:
                st.session_state.colors[clean_category] = color

                final_end_date = (
                    event_date
                    if repeat_pattern == "Does not repeat"
                    else repeat_until
                )

                added, skipped = add_recurring_events(
                    name=name,
                    category=clean_category,
                    start_date=event_date,
                    end_date=final_end_date,
                    start_time=start,
                    end_time=end,
                    pattern=repeat_pattern,
                    selected_days=repeat_days,
                    people=people,
                    needs=needs,
                    notes=notes,
                    source="Manual recurrence",
                    major=major,
                )

                st.success(
                    f"Added {added} event(s). "
                    f"Skipped {skipped} duplicate(s)."
                )
                st.rerun()

    if view == "Week":
        picked = st.date_input(
            "Choose a week",
            now_local().date(),
            key="week_pick",
        )

        start_week = picked - timedelta(days=picked.weekday())
        days = [start_week + timedelta(days=i) for i in range(7)]
        today_value = now_local().date()

        html = "<div class='week-columns'>"

        for day_value in days:
            column_class = (
                "week-column week-column-today"
                if day_value == today_value
                else "week-column"
            )

            html += (
                f"<div class='{column_class}'>"
                f"<div class='week-column-header'>{day_value.strftime('%A')}</div>"
                f"<div class='week-column-date'>{day_value.strftime('%d %B')}</div>"
            )

            day_events = events_on(day_value)

            if not day_events:
                html += "<div class='week-empty'>No events</div>"
            else:
                for event in day_events:
                    html += (
                        f"<div class='week-event' "
                        f"style='background:{event_color(event.get('category', 'Other'))};'>"
                        f"<div class='week-event-name'>{escape(event.get('name', 'Event'))}</div>"
                        f"<div>{escape(event.get('start', ''))}–{escape(event.get('end', ''))}</div>"
                        f"</div>"
                    )

            html += "</div>"

        html += "</div>"

        st.markdown(
            html,
            unsafe_allow_html=True,
        )

    else:
        c1, c2 = st.columns(2)
        current = now_local().date()
        month_name = c1.selectbox("Month", list(calendar.month_name)[1:], index=current.month - 1)
        year = c2.number_input("Year", 2024, 2040, current.year)
        month_number = list(calendar.month_name).index(month_name)
        firstweekday = 0 if st.session_state.settings["first_day"] == "Monday" else 6
        weeks = calendar.Calendar(firstweekday=firstweekday).monthdayscalendar(year, month_number)
        labels = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"] if firstweekday == 0 else ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        html = "<div class='month-grid'>" + "".join(f"<div class='weekday'>{x}</div>" for x in labels)
        for week in weeks:
            for day_num in week:
                if day_num == 0:
                    html += "<div class='month-cell'></div>"
                    continue
                d = date(year, month_number, day_num)
                cls = "month-cell today" if d == current else "month-cell"
                html += f"<div class='{cls}'><div class='date-number'>{day_num}</div>"
                majors = [e for e in events_on(d) if e.get("major", True)]
                for e in majors[:3]:
                    html += f"<div class='mini-event' style='background:{event_color(e['category'])}'>{e['start']} {escape(e['name'])}</div>"
                if len(majors) > 3:
                    html += f"<div class='date-number'>+{len(majors)-3} more</div>"
                html += "</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    with st.expander("Manage Events"):
        if not st.session_state.events:
            st.info("No events yet.")
        else:
            options = [f"{i+1}. {e['date']} · {e['start']} · {e['name']}" for i, e in enumerate(st.session_state.events)]
            selected = st.selectbox("Event", options)
            index = options.index(selected)
            event = st.session_state.events[index]
            render_event(event, detailed=True)
            new_notes = st.text_area("Update notes", event.get("notes", ""), key="manage_notes")
            new_result = st.text_input("Update reflection", event.get("result", ""), key="manage_result")
            c1, c2 = st.columns(2)
            if c1.button("Save Changes", use_container_width=True):
                event["notes"] = new_notes
                event["result"] = new_result
                st.success("Updated.")
                st.rerun()
            if c2.button("Delete Event", use_container_width=True):
                st.session_state.events.pop(index)
                st.rerun()

elif st.session_state.page == "Assistant":
    page_header(
        "💬",
        "Sky Planning Assistant",
        "Ask Sky to connect exams, sports, recovery, deadlines, and free time into a realistic plan.",
    )

    if not gemini_available():
        st.info(
            "Offline planning is active. Sky can still analyse your calendar and create safe suggestions."
        )

    suggestions = [
        "When can I study for my next test?",
        "Plan around my next sports event",
        "Where can I fit a recovery break?",
        "What should I prepare for this week?",
    ]
    cols = st.columns(4)
    for col, suggestion in zip(cols, suggestions):
        if col.button(suggestion, use_container_width=True):
            st.session_state.pending_question = suggestion

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if st.session_state.pending_ai_plans:
        with st.container(border=True):
            st.subheader("📅 Sky's suggested calendar events")
            st.caption(
                "Sky will never add these automatically. Review each suggestion first."
            )

            plans_to_remove = []
            for index, plan in enumerate(st.session_state.pending_ai_plans):
                with st.expander(
                    f"{plan['date']} · {plan['start']}–{plan['end']} · {plan['title']}",
                    expanded=True,
                ):
                    title = st.text_input(
                        "Title",
                        plan["title"],
                        key=f"ai_plan_title_{index}",
                    )
                    plan_date = st.date_input(
                        "Date",
                        datetime.strptime(plan["date"], "%Y-%m-%d").date(),
                        key=f"ai_plan_date_{index}",
                    )
                    c1, c2 = st.columns(2)
                    plan_start = c1.time_input(
                        "Start",
                        datetime.strptime(plan["start"], "%H:%M").time(),
                        key=f"ai_plan_start_{index}",
                    )
                    plan_end = c2.time_input(
                        "End",
                        datetime.strptime(plan["end"], "%H:%M").time(),
                        key=f"ai_plan_end_{index}",
                    )
                    notes = st.text_area(
                        "Notes",
                        plan.get("notes", ""),
                        key=f"ai_plan_notes_{index}",
                    )
                    st.caption(plan.get("reason", ""))

                    b1, b2 = st.columns(2)
                    if b1.button(
                        "Add to Calendar",
                        key=f"add_ai_plan_{index}",
                        use_container_width=True,
                    ):
                        added = add_event(
                            title,
                            plan.get("category", "Study"),
                            plan_date.isoformat(),
                            plan_start.strftime("%H:%M"),
                            plan_end.strftime("%H:%M"),
                            notes=notes,
                            source="AI Suggested",
                        )
                        if added:
                            plans_to_remove.append(index)
                            st.success("Suggested event added to your calendar.")
                        else:
                            st.error("That event already exists or could not be added.")

                    if b2.button(
                        "Dismiss",
                        key=f"dismiss_ai_plan_{index}",
                        use_container_width=True,
                    ):
                        plans_to_remove.append(index)

            if plans_to_remove:
                st.session_state.pending_ai_plans = [
                    plan
                    for index, plan in enumerate(st.session_state.pending_ai_plans)
                    if index not in plans_to_remove
                ]
                st.rerun()

    typed = st.chat_input("Ask Sky to plan around your timetable...")
    question = typed or st.session_state.pop("pending_question", None)

    if question:
        st.session_state.chat_history.append(
            {"role": "user", "content": question}
        )
        answer = assistant_answer(question)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer}
        )
        st.rerun()

elif st.session_state.page == "Settings":
    page_header("⚙️", "Settings", "Edit your profile, appearance, calendar preferences, and assistant style.")
    profile_tab, appearance_tab, calendar_tab, assistant_tab = st.tabs(["Profile", "Appearance", "Calendar", "Assistant"])

    with profile_tab:
        profile = st.session_state.profile
        profession_choice = st.selectbox("Profession suggestion", PROFESSION_SUGGESTIONS, index=PROFESSION_SUGGESTIONS.index(profile.get("profession")) if profile.get("profession") in PROFESSION_SUGGESTIONS else PROFESSION_SUGGESTIONS.index("Other / Custom"))
        custom_profession = st.text_input("Custom profession", profile.get("profession", "")) if profession_choice == "Other / Custom" else ""
        name = st.text_input("Name", profile.get("name", ""))
        goal = st.text_input("Main goal", profile.get("goal", ""))
        areas = st.multiselect("Management areas", MANAGEMENT_AREAS, default=profile.get("management_areas", []))
        sports_interests = st.text_input("Sports interests", profile.get("sports_interests", ""))
        sports_schedule = st.text_area("Sports schedule", profile.get("sports_schedule", ""))
        timezone_current = profile.get("timezone", "Asia/Dubai")
        timezone_index = TIMEZONES.index(timezone_current) if timezone_current in TIMEZONES else TIMEZONES.index("Other / Custom")
        timezone_choice = st.selectbox("Timezone", TIMEZONES, index=timezone_index)
        custom_timezone = st.text_input("Custom timezone", timezone_current if timezone_current not in TIMEZONES else "") if timezone_choice == "Other / Custom" else ""
        if st.button("Save Profile", use_container_width=True):
            profession = custom_profession.strip() if profession_choice == "Other / Custom" else profession_choice
            timezone = custom_timezone.strip() if timezone_choice == "Other / Custom" else timezone_choice
            try:
                ZoneInfo(timezone)
                st.session_state.profile.update({"profession": profession, "name": name, "goal": goal, "management_areas": areas, "sports_interests": sports_interests, "sports_schedule": sports_schedule, "timezone": timezone})
                st.success("Profile saved.")
                st.rerun()
            except Exception:
                st.error("Invalid timezone.")
        if st.button("Rebuild Sports Schedule", use_container_width=True):
            added = parse_routine(sports_schedule)
            st.success(f"Added {added} events.")

        st.subheader("Live sports calendar")

        live_interests = st.text_area(
            "Teams or championships to sync",
            profile.get("sports_interests", ""),
            key="settings_live_sports",
            placeholder="F1, Ferrari, Arsenal, Portugal",
        )

        if st.button(
            "Find upcoming sports events",
            use_container_width=True,
        ):
            with st.spinner("Looking for fixtures..."):
                candidates, message = fetch_sports_candidates(
                    live_interests
                )

            st.session_state.sports_candidates = candidates
            st.session_state.sports_sync_message = message
            st.session_state.profile["sports_interests"] = live_interests
            st.info(message)

        if st.session_state.sports_candidates:
            st.caption(
                "Open onboarding sports review by clicking below. "
                "Nothing is added without approval."
            )

            if st.button(
                "Review found sports events",
                use_container_width=True,
            ):
                st.session_state.profile_done = False
                st.session_state.onboarding_step = 4
                st.rerun()

    with appearance_tab:
        st.subheader("App Theme")
        theme_names = list(THEME_PRESETS.keys())
        current_name = st.session_state.get("theme_name", DEFAULT_THEME_NAME)
        selected_preset = st.selectbox(
            "Choose a theme",
            theme_names,
            index=theme_names.index(current_name) if current_name in theme_names else 0,
            key="appearance_theme_picker",
        )

        if selected_preset != st.session_state.get("settings_theme_choice"):
            st.session_state.settings_theme_choice = selected_preset
            set_theme(selected_preset)
            st.rerun()

        render_theme_preview(selected_preset)
        base = st.session_state.theme

        with st.expander("Advanced theme colors"):
            primary = st.color_picker("Primary", base["primary"])
            secondary = st.color_picker("Secondary", base.get("secondary", base["muted"]))
            accent = st.color_picker("Accent", base.get("accent", base["card"]))
            background = st.color_picker("Background", base["background"])
            card = st.color_picker("Cards", base["card"])
            text_color = st.color_picker("Text", base["text"])
            muted = st.color_picker("Secondary text", base["muted"])
            sidebar_color = st.color_picker("Sidebar", base["sidebar"])

        st.subheader("Custom Event Colors")
        st.caption("These stay separate from the app theme, so every calendar category can have its own color.")
        updated = {}
        columns = st.columns(2)
        for i, category in enumerate(st.session_state.colors):
            with columns[i % 2]:
                updated[category] = st.color_picker(
                    f"{event_icon(category)} {category}",
                    st.session_state.colors[category],
                    key=f"color_{category}",
                )

        if st.button("Save Appearance", use_container_width=True):
            st.session_state.theme = {
                "primary": primary,
                "secondary": secondary,
                "accent": accent,
                "background": background,
                "card": card,
                "text": text_color,
                "muted": muted,
                "sidebar": sidebar_color,
            }
            preset_values = THEME_PRESETS[selected_preset]
            if st.session_state.theme == preset_values:
                st.session_state.theme_name = selected_preset
            else:
                st.session_state.theme_name = selected_preset
            st.session_state.selected_theme = st.session_state.theme_name
            st.session_state.settings_theme_choice = st.session_state.theme_name
            st.session_state.colors.update(updated)
            st.success("Appearance saved.")
            st.rerun()

    with calendar_tab:
        default_view = st.radio("Default calendar view", ["Week", "Month"], index=0 if st.session_state.settings["default_calendar_view"] == "Week" else 1, horizontal=True)
        first_day = st.radio("First day of week", ["Monday", "Sunday"], index=0 if st.session_state.settings["first_day"] == "Monday" else 1, horizontal=True)
        show_sports = st.toggle("Show sports events", st.session_state.settings["show_sports"])
        show_ai = st.toggle("Show AI suggested events", st.session_state.settings["show_ai_events"])
        save_reflections = st.toggle("Save notes and reflections", st.session_state.settings["save_reflections"])
        day_start = st.slider("Planning day starts", 0, 12, st.session_state.settings["day_start"])
        day_end = st.slider("Planning day ends", 13, 24, st.session_state.settings["day_end"])
        if st.button("Save Calendar Settings", use_container_width=True):
            st.session_state.settings.update({"default_calendar_view": default_view, "first_day": first_day, "show_sports": show_sports, "show_ai_events": show_ai, "save_reflections": save_reflections, "day_start": day_start, "day_end": day_end})
            st.success("Calendar settings saved.")
            st.rerun()

    with assistant_tab:
        tone = st.selectbox("AI personality", ["Adaptive", "Professional", "Friendly", "Coach", "Motivational", "Strict", "Funny"], index=["Adaptive", "Professional", "Friendly", "Coach", "Motivational", "Strict", "Funny"].index(st.session_state.settings["ai_tone"]))
        use_gemini = st.toggle("Use Gemini when available", st.session_state.settings["use_gemini"])
        model_name = st.text_input("Gemini model", st.session_state.settings["gemini_model"])
        if st.button("Save Assistant Settings", use_container_width=True):
            st.session_state.settings.update({"ai_tone": tone, "use_gemini": use_gemini, "gemini_model": model_name.strip()})
            st.success("Assistant settings saved.")
            st.rerun()
        st.caption("Gemini uses GOOGLE_API_KEY from .streamlit/secrets.toml or your environment. The offline assistant remains available if Gemini fails.")