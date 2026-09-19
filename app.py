# ============================================================
# 🇵🇰 PAKISTAN WEATHER INTELLIGENCE — INDUSTRY STYLE STREAMLIT APP
# Fast multi-city architecture + live forecast + historical analytics
# + rainfall intelligence + insights + statistical outlook + PDF.
#
# Install:
#   pip install streamlit pandas numpy requests plotly reportlab
#
# Run:
#   streamlit run app.py
# ============================================================

import concurrent.futures
from datetime import date, timedelta
from io import BytesIO

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

# ============================================================
# APP CONFIG
# ============================================================
st.set_page_config(
    page_title="Pakistan Weather Intelligence",
    page_icon="🇵🇰",
    layout="wide",
    initial_sidebar_state="expanded",
)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HIST_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT = 20
CACHE_TTL_FORECAST = 300
CACHE_TTL_HISTORY = 86400

# ============================================================
# PREMIUM UI
# ============================================================
st.markdown("""
<style>
:root {
    --card: rgba(127,127,127,.07);
    --border: rgba(127,127,127,.20);
}
.main .block-container {
    max-width: 1550px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}
.hero {
    padding: 30px 32px;
    border-radius: 22px;
    margin-bottom: 18px;
    background: linear-gradient(135deg,#07111f 0%,#123d5a 55%,#0f766e 100%);
    color: white;
    box-shadow: 0 12px 35px rgba(0,0,0,.12);
}
.hero h1 {margin:0;font-size:2.45rem;letter-spacing:-.7px;}
.hero p {margin:8px 0 0;color:#dbeafe;font-size:1.02rem;}
.section-title {
    font-size: 1.35rem;
    font-weight: 750;
    margin-top: 18px;
    margin-bottom: 8px;
}
.insight {
    padding: 15px 17px;
    border-radius: 15px;
    border: 1px solid var(--border);
    background: var(--card);
    margin-bottom: 10px;
}
.insight b {font-size: .98rem;}
.insight span {color:#64748b;}
.source-note {
    color:#64748b;
    font-size:.78rem;
    line-height:1.45;
}
div[data-testid="stMetric"] {
    border: 1px solid var(--border);
    border-radius: 15px;
    padding: 14px 15px;
    background: var(--card);
}
[data-testid="stSidebar"] {
    border-right: 1px solid var(--border);
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CITY MASTER — 100+ LOCATIONS
# User selects only a city name; coordinates stay internal.
# ============================================================
CITIES = {
    # Federal / ICT
    "Islamabad": (33.6844, 73.0479),
    "Rawalpindi": (33.5651, 73.0169),

    # Sindh
    "Karachi": (24.8607, 67.0011),
    "Hyderabad": (25.3960, 68.3578),
    "Sukkur": (27.7052, 68.8574),
    "Larkana": (27.5581, 68.2028),
    "Nawabshah": (26.2442, 68.4100),
    "Mirpur Khas": (25.5276, 69.0111),
    "Thatta": (24.7475, 67.9235),
    "Jacobabad": (28.2819, 68.4376),
    "Shikarpur": (27.9556, 68.6382),
    "Dadu": (26.7303, 67.7769),
    "Badin": (24.6560, 68.8380),
    "Tando Adam": (25.7631, 68.6610),
    "Tando Allahyar": (25.4600, 68.7190),
    "Umerkot": (25.3633, 69.7360),
    "Khairpur": (27.5295, 68.7592),
    "Ghotki": (28.0060, 69.3161),
    "Matiari": (25.5970, 68.4460),

    # Punjab
    "Lahore": (31.5497, 74.3436),
    "Faisalabad": (31.4504, 73.1350),
    "Gujranwala": (32.1877, 74.1945),
    "Sialkot": (32.4945, 74.5229),
    "Sargodha": (32.0836, 72.6711),
    "Bahawalpur": (29.3956, 71.6836),
    "Multan": (30.1575, 71.5249),
    "Rahim Yar Khan": (28.4212, 70.2989),
    "Sahiwal": (30.6682, 73.1114),
    "Jhang": (31.2781, 72.3118),
    "Sheikhupura": (31.7131, 73.9783),
    "Gujrat": (32.5742, 74.0754),
    "Kasur": (31.1157, 74.4467),
    "Okara": (30.8103, 73.4516),
    "Dera Ghazi Khan": (30.0561, 70.6348),
    "Muridke": (31.8020, 74.2550),
    "Wazirabad": (32.4440, 74.1200),
    "Hafizabad": (32.0709, 73.6880),
    "Mandi Bahauddin": (32.5861, 73.4918),
    "Chiniot": (31.7200, 72.9789),
    "Toba Tek Singh": (30.9713, 72.4827),
    "Khanewal": (30.3017, 71.9321),
    "Lodhran": (29.5339, 71.6336),
    "Vehari": (30.0419, 72.3528),
    "Pakpattan": (30.3431, 73.3866),
    "Muzaffargarh": (30.0726, 71.1938),
    "Layyah": (30.9690, 70.9428),
    "Bhakkar": (31.6330, 71.0657),
    "Mianwali": (32.5853, 71.5436),
    "Attock": (33.7667, 72.3667),
    "Jhelum": (32.9345, 73.7310),
    "Chakwal": (32.9333, 72.8667),
    "Nankana Sahib": (31.4500, 73.7069),
    "Narowal": (32.1000, 74.8833),
    "Taxila": (33.7463, 72.8397),
    "Kharian": (32.8110, 73.8650),
    "Arifwala": (30.2916, 73.0650),
    "Burewala": (30.1667, 72.6500),
    "Kot Addu": (30.4691, 70.9660),

    # Khyber Pakhtunkhwa
    "Peshawar": (34.0151, 71.5249),
    "Mardan": (34.1989, 72.0401),
    "Abbottabad": (34.1463, 73.2117),
    "Mingora": (34.7795, 72.3627),
    "Saidu Sharif": (34.7466, 72.3556),
    "Swat": (35.2227, 72.4258),
    "Bannu": (32.9853, 70.6040),
    "Dera Ismail Khan": (31.8327, 70.9024),
    "Kohat": (33.5819, 71.4493),
    "Chitral": (35.8518, 71.7864),
    "Mansehra": (34.3300, 73.2000),
    "Haripur": (33.9942, 72.9340),
    "Nowshera": (34.0159, 72.0110),
    "Charsadda": (34.1482, 71.7406),
    "Karak": (33.1167, 71.0833),
    "Tank": (32.2167, 70.3833),
    "Dir": (35.1989, 71.8744),
    "Bajaur": (34.7900, 71.5200),
    "Parachinar": (33.8997, 70.1000),

    # Balochistan
    "Quetta": (30.1798, 66.9750),
    "Turbat": (26.0023, 63.0485),
    "Gwadar": (25.1264, 62.3225),
    "Khuzdar": (27.8000, 66.6167),
    "Zhob": (31.3417, 69.4486),
    "Chaman": (30.9177, 66.4597),
    "Sibi": (29.5430, 67.8773),
    "Loralai": (30.3705, 68.5979),
    "Kalat": (29.0266, 66.5936),
    "Nushki": (29.5522, 66.0213),
    "Pishin": (30.5818, 66.9927),
    "Dalbandin": (28.8885, 64.4062),
    "Pasni": (25.2631, 63.4710),
    "Ormara": (25.2100, 64.6350),

    # Azad Kashmir
    "Muzaffarabad": (34.3700, 73.4711),
    "Mirpur": (33.1481, 73.7510),
    "Kotli": (33.5184, 73.9022),
    "Rawalakot": (33.8578, 73.7604),
    "Bagh": (33.9811, 73.7740),

    # Gilgit-Baltistan
    "Gilgit": (35.9208, 74.3080),
    "Skardu": (35.2971, 75.6333),
    "Hunza": (36.3167, 74.6500),
    "Khaplu": (35.1620, 76.3330),
    "Chilas": (35.4145, 74.1021),
    "Astore": (35.3667, 74.8667),
    "Ghanche": (35.3000, 76.3333),

    # Northern tourist/weather locations
    "Murree": (33.9073, 73.3903),
    "Naran": (34.9086, 73.6510),
    "Kaghan": (34.7797, 73.5376),
}

CITY_LIST = sorted(CITIES)

# ============================================================
# HTTP SESSION + API HELPERS
# ============================================================
@st.cache_resource
def http_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Pakistan-Weather-Intelligence/2.0 Streamlit"
    })
    return s

SESSION = http_session()

FORECAST_HOURLY = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m",
    "apparent_temperature", "precipitation_probability",
    "precipitation", "rain", "showers", "weather_code",
    "cloud_cover", "pressure_msl", "surface_pressure",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
    "visibility", "uv_index", "is_day"
]

FORECAST_DAILY = [
    "weather_code", "temperature_2m_max", "temperature_2m_min",
    "temperature_2m_mean", "apparent_temperature_max",
    "apparent_temperature_min", "sunrise", "sunset",
    "daylight_duration", "sunshine_duration", "precipitation_sum",
    "rain_sum", "showers_sum", "precipitation_hours",
    "precipitation_probability_max", "wind_speed_10m_max",
    "wind_gusts_10m_max", "wind_direction_10m_dominant",
    "uv_index_max", "et0_fao_evapotranspiration"
]

HISTORY_DAILY = [
    "weather_code", "temperature_2m_max", "temperature_2m_min",
    "temperature_2m_mean", "apparent_temperature_max",
    "apparent_temperature_min", "precipitation_sum", "rain_sum",
    "showers_sum", "precipitation_hours", "wind_speed_10m_max",
    "wind_gusts_10m_max", "wind_direction_10m_dominant",
    "sunshine_duration", "et0_fao_evapotranspiration"
]


@st.cache_data(ttl=CACHE_TTL_FORECAST, show_spinner=False)
def get_forecast_multi(cities):
    """One API request for many cities — much faster than N separate calls."""
    lats = ",".join(str(CITIES[c][0]) for c in cities)
    lons = ",".join(str(CITIES[c][1]) for c in cities)

    params = {
        "latitude": lats,
        "longitude": lons,
        "timezone": "auto",
        "forecast_days": 16,
        "current": ",".join([
            "temperature_2m", "relative_humidity_2m",
            "apparent_temperature", "precipitation",
            "rain", "showers", "weather_code", "cloud_cover",
            "pressure_msl", "wind_speed_10m", "wind_direction_10m",
            "wind_gusts_10m", "visibility", "uv_index"
        ]),
        "hourly": ",".join(FORECAST_HOURLY),
        "daily": ",".join(FORECAST_DAILY),
    }

    r = SESSION.get(FORECAST_URL, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else [data]


@st.cache_data(ttl=CACHE_TTL_FORECAST, show_spinner=False)
def get_single_forecast(city):
    return get_forecast_multi((city,))[0]


@st.cache_data(ttl=CACHE_TTL_HISTORY, show_spinner=False)
def get_history(city, start_date, end_date):
    lat, lon = CITIES[city]
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto",
        "daily": ",".join(HISTORY_DAILY),
    }
    r = SESSION.get(HIST_URL, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=CACHE_TTL_HISTORY, show_spinner=False)
def get_city_history_total(city, start_date, end_date):
    """Small response for rankings: only precipitation + temperature."""
    lat, lon = CITIES[city]
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto",
        "daily": "precipitation_sum,temperature_2m_mean",
    }
    r = SESSION.get(HIST_URL, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json().get("daily", {})
    rain = np.asarray(d.get("precipitation_sum", []), dtype=float)
    temp = np.asarray(d.get("temperature_2m_mean", []), dtype=float)
    return {
        "City": city,
        "Rain (mm)": float(np.nansum(rain)),
        "Avg Temp (°C)": float(np.nanmean(temp)) if len(temp) else np.nan,
        "Wet Days": int(np.nansum(rain >= 1)),
    }


# ============================================================
# DATAFRAME HELPERS
# ============================================================
def hourly_df(payload):
    d = payload.get("hourly", {})
    df = pd.DataFrame(d)
    if "time" in df:
        df["time"] = pd.to_datetime(df["time"])
    return df


def daily_df(payload):
    d = payload.get("daily", {})
    df = pd.DataFrame(d)
    if "time" in df:
        df["time"] = pd.to_datetime(df["time"])
    return df


def weather_label(code):
    mapping = {
        0: "Clear", 1: "Mainly clear", 2: "Partly cloudy",
        3: "Overcast", 45: "Fog", 48: "Rime fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
        61: "Light rain", 63: "Rain", 65: "Heavy rain",
        66: "Freezing rain", 67: "Heavy freezing rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow",
        77: "Snow grains", 80: "Rain showers", 81: "Rain showers",
        82: "Heavy rain showers", 85: "Snow showers",
        86: "Heavy snow showers", 95: "Thunderstorm",
        96: "Thunderstorm + hail", 99: "Thunderstorm + hail",
    }
    try:
        return mapping.get(int(code), "Unknown")
    except Exception:
        return "Unknown"


def nsum(series):
    return float(np.nansum(np.asarray(series, dtype=float)))


def nmean(series):
    a = np.asarray(series, dtype=float)
    return float(np.nanmean(a)) if len(a) and not np.all(np.isnan(a)) else np.nan


def fmt_num(x, digits=1):
    try:
        if pd.isna(x):
            return "—"
        return f"{float(x):,.{digits}f}"
    except Exception:
        return "—"


# ============================================================
# INSIGHT ENGINE
# ============================================================
def generate_insights(city, cur, fday, hist):
    insights = []

    temp = cur.get("temperature_2m")
    humidity = cur.get("relative_humidity_2m")
    rain_now = cur.get("precipitation")
    wind = cur.get("wind_speed_10m")
    pressure = cur.get("pressure_msl")

    if temp is not None:
        insights.append(
            f"<b>Current thermal state:</b> {city} is at "
            f"<b>{fmt_num(temp)} °C</b>, with a humidity level of "
            f"<b>{fmt_num(humidity,0)}%</b>."
        )

    if len(fday):
        max_idx = fday["temperature_2m_max"].idxmax()
        min_idx = fday["temperature_2m_min"].idxmin()
        max_row = fday.loc[max_idx]
        min_row = fday.loc[min_idx]
        insights.append(
            f"<b>Forecast range:</b> the warmest forecast maximum is "
            f"<b>{fmt_num(max_row['temperature_2m_max'])} °C</b> on "
            f"<b>{max_row['time'].strftime('%d %b')}</b>, while the lowest "
            f"forecast minimum is <b>{fmt_num(min_row['temperature_2m_min'])} °C</b>."
        )

        rain_total = nsum(fday["precipitation_sum"])
        wet_days = int(nsum(fday["precipitation_sum"] >= 1))
        rain_prob = float(fday["precipitation_probability_max"].max())
        insights.append(
            f"<b>Rain signal:</b> the 16-day forecast contains about "
            f"<b>{rain_total:.1f} mm</b> of total precipitation across "
            f"<b>{wet_days}</b> wet day(s); the highest daily rain probability "
            f"is <b>{rain_prob:.0f}%</b>."
        )

    if len(hist):
        hist_rain = nsum(hist["precipitation_sum"])
        hist_temp = nmean(hist["temperature_2m_mean"])
        heavy = int(nsum(hist["precipitation_sum"] >= 25))
        insights.append(
            f"<b>Historical baseline:</b> over the selected historical window, "
            f"the city accumulated approximately <b>{hist_rain:,.1f} mm</b> "
            f"of precipitation with a mean temperature of <b>{hist_temp:.1f} °C</b>."
        )
        insights.append(
            f"<b>Rainfall intensity:</b> {heavy} historical day(s) recorded "
            f"at least 25 mm of daily precipitation in the selected period."
        )

    if humidity is not None and temp is not None:
        if humidity >= 80:
            msg = "high atmospheric moisture may make conditions feel more humid."
        elif humidity <= 30:
            msg = "relatively dry air is currently present."
        else:
            msg = "humidity is in a moderate range."
        insights.append(f"<b>Moisture signal:</b> {msg}")

    if wind is not None and wind >= 35:
        insights.append(
            f"<b>Wind watch:</b> current wind speed is around {wind:.1f} km/h; "
            "monitor gusts in the detailed forecast."
        )

    if pressure is not None:
        insights.append(
            f"<b>Pressure context:</b> mean-sea-level pressure is approximately "
            f"<b>{pressure:.0f} hPa</b>."
        )

    return insights


# ============================================================
# STATISTICAL PROJECTION
# ============================================================
def seasonal_projection(hist, days=30):
    """
    Transparent climatological baseline.
    Uses historical day-of-year averages + smoothing.
    It is explicitly NOT an operational weather forecast.
    """
    if len(hist) < 60:
        return pd.DataFrame()

    x = hist.copy()
    x = x.dropna(subset=["temperature_2m_mean", "precipitation_sum"])
    if len(x) < 60:
        return pd.DataFrame()

    x["doy"] = x["time"].dt.dayofyear

    # Smooth day-of-year climatology.
    temp_clim = x.groupby("doy")["temperature_2m_mean"].mean().rolling(
        15, center=True, min_periods=3
    ).mean()

    rain_clim = x.groupby("doy")["precipitation_sum"].mean().rolling(
        15, center=True, min_periods=3
    ).mean()

    start = x["time"].max().normalize() + pd.Timedelta(days=1)
    dates = pd.date_range(start, periods=days)

    out = pd.DataFrame({"date": dates})
    out["doy"] = out["date"].dt.dayofyear
    out["Projected Temp (°C)"] = out["doy"].map(temp_clim)
    out["Projected Rain (mm)"] = out["doy"].map(rain_clim).fillna(0)
    out["Projected Temp (°C)"] = (
        out["Projected Temp (°C)"].interpolate().bfill().ffill()
    )
    return out


# ============================================================
# PDF REPORT
# ============================================================
def make_pdf(city, cur, hist, fday, projection, insights):
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        rightMargin=28,
        leftMargin=28,
        topMargin=25,
        bottomMargin=25,
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=23, leading=26, spaceAfter=8
    )
    h2 = ParagraphStyle(
        "ReportH2", parent=styles["Heading2"],
        fontSize=14, leading=17, spaceBefore=10, spaceAfter=6
    )
    body = ParagraphStyle(
        "ReportBody", parent=styles["BodyText"],
        fontSize=8.5, leading=11
    )

    story = []
    story.append(Paragraph(
        f"Pakistan Weather Intelligence Report — {city}", title
    ))
    story.append(Paragraph(
        f"Generated on {date.today().isoformat()} • Live forecast + historical analytics",
        body
    ))
    story.append(Spacer(1, 8))

    # KPI table
    kpi = [
        ["Temperature", "Feels Like", "Humidity", "Wind", "Pressure", "Rain Now"],
        [
            f"{cur.get('temperature_2m','—')} °C",
            f"{cur.get('apparent_temperature','—')} °C",
            f"{cur.get('relative_humidity_2m','—')} %",
            f"{cur.get('wind_speed_10m','—')} km/h",
            f"{cur.get('pressure_msl','—')} hPa",
            f"{cur.get('precipitation','—')} mm",
        ],
    ]

    t = Table(kpi, colWidths=[1.25*inch]*6)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#edf7f7")),
        ("GRID", (0,0), (-1,-1), .4, colors.grey),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(t)

    story.append(Paragraph("Automated Insights", h2))
    for item in insights[:8]:
        story.append(Paragraph("• " + item.replace("<b>","").replace("</b>",""), body))
        story.append(Spacer(1, 3))

    story.append(Paragraph("Historical Summary", h2))
    if len(hist):
        hist_table = [
            ["Period", "Mean Temp", "Max Temp", "Min Temp", "Rain", "Wet Days", "Heavy Rain Days"],
            [
                f"{hist['time'].min().date()} → {hist['time'].max().date()}",
                f"{nmean(hist['temperature_2m_mean']):.1f} °C",
                f"{np.nanmax(hist['temperature_2m_max']):.1f} °C",
                f"{np.nanmin(hist['temperature_2m_min']):.1f} °C",
                f"{nsum(hist['precipitation_sum']):,.1f} mm",
                str(int(nsum(hist['precipitation_sum'] >= 1))),
                str(int(nsum(hist['precipitation_sum'] >= 25))),
            ]
        ]
        ht = Table(hist_table, colWidths=[
            1.65*inch,1.0*inch,1.0*inch,1.0*inch,
            1.0*inch,.9*inch,1.15*inch
        ])
        ht.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#123d5a")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("GRID",(0,0),(-1,-1),.4,colors.grey),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("FONTSIZE",(0,0),(-1,-1),8),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(ht)

    story.append(Paragraph("16-Day Forecast", h2))
    if len(fday):
        rows = [["Date","Max °C","Min °C","Rain mm","Rain Prob.","Max Wind","UV"]]
        for _, r in fday.head(16).iterrows():
            rows.append([
                r["time"].strftime("%d %b"),
                f"{r.get('temperature_2m_max',np.nan):.1f}",
                f"{r.get('temperature_2m_min',np.nan):.1f}",
                f"{r.get('precipitation_sum',np.nan):.1f}",
                f"{r.get('precipitation_probability_max',np.nan):.0f}%",
                f"{r.get('wind_speed_10m_max',np.nan):.1f}",
                f"{r.get('uv_index_max',np.nan):.1f}",
            ])
        ft = Table(rows, colWidths=[1.0*inch,.8*inch,.8*inch,.8*inch,
                                    .9*inch,1.0*inch,.7*inch])
        ft.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f766e")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("GRID",(0,0),(-1,-1),.35,colors.grey),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("FONTSIZE",(0,0),(-1,-1),7.5),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        story.append(ft)

    story.append(PageBreak())
    story.append(Paragraph("Projection & Methodology", title))
    story.append(Paragraph(
        "The 30-day outlook is a statistical seasonal baseline derived from the "
        "selected city's historical daily weather record. It maps historical "
        "day-of-year patterns to future calendar dates and applies smoothing. "
        "It is not a replacement for operational numerical weather prediction "
        "and should not be interpreted as a guaranteed forecast.",
        body
    ))
    story.append(Spacer(1, 8))

    if len(projection):
        p = projection.copy()
        p["Month"] = p["date"].dt.strftime("%d %b")
        rows = [["Date","Projected Temp °C","Projected Rain mm"]]
        for _, r in p.iterrows():
            rows.append([
                r["Month"],
                f"{r['Projected Temp (°C)']:.1f}",
                f"{r['Projected Rain (mm)']:.2f}",
            ])
        pt = Table(rows, colWidths=[1.1*inch,1.4*inch,1.4*inch])
        pt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#334155")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("GRID",(0,0),(-1,-1),.3,colors.grey),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("FONTSIZE",(0,0),(-1,-1),7),
        ]))
        story.append(pt)

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Data source: Open-Meteo forecast and historical weather APIs. "
        "Historical values are model/reanalysis-derived and can differ from "
        "individual weather-station observations. For safety-critical weather "
        "decisions, consult official meteorological warnings.",
        body
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ============================================================
# HERO
# ============================================================
st.markdown("""
<div class="hero">
    <h1>🇵🇰 Pakistan Weather Intelligence</h1>
    <p>Live conditions • 16-day forecast • historical climate analytics • rainfall intelligence • statistical outlooks • 100+ cities</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("🎛 Control Center")

selected_city = st.sidebar.selectbox(
    "📍 City",
    CITY_LIST,
    index=CITY_LIST.index("Karachi")
)

history_days = st.sidebar.select_slider(
    "📚 Historical window",
    options=[30, 90, 180, 365, 730, 1095],
    value=365,
    format_func=lambda x: f"{x} days"
)

dashboard_view = st.sidebar.radio(
    "📊 Analysis module",
    [
        "Executive Overview",
        "Forecast",
        "Historical Trends",
        "Rainfall Intelligence",
        "Atmosphere & Wind",
        "All-City Comparison",
    ],
)

if st.sidebar.button("🔄 Force Refresh", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Performance architecture**  \n"
    "• Multi-city forecast batching  \n"
    "• Request caching  \n"
    "• Small historical ranking payloads  \n"
    "• Parallel historical ranking requests"
)

# ============================================================
# SELECTED CITY DATA
# ============================================================
try:
    with st.spinner(f"Loading live weather intelligence for {selected_city}..."):
        forecast_payload = get_single_forecast(selected_city)
        history_payload = get_history(
            selected_city,
            (date.today() - timedelta(days=history_days)).isoformat(),
            date.today().isoformat()
        )
except Exception as e:
    st.error("Weather data could not be loaded. Check your internet connection or refresh the dashboard.")
    st.exception(e)
    st.stop()

cur = forecast_payload.get("current", {})
fday = daily_df(forecast_payload)
fhour = hourly_df(forecast_payload)
hist = daily_df(history_payload)

# ============================================================
# CURRENT KPI BAR
# ============================================================
st.markdown(
    f'<div class="section-title">🌤 Live Conditions — {selected_city}</div>',
    unsafe_allow_html=True
)

k = st.columns(7)
k[0].metric("🌡 Temperature", f"{cur.get('temperature_2m','—')} °C")
k[1].metric("🥵 Feels Like", f"{cur.get('apparent_temperature','—')} °C")
k[2].metric("💧 Humidity", f"{cur.get('relative_humidity_2m','—')} %")
k[3].metric("🌧 Rain", f"{cur.get('precipitation','—')} mm")
k[4].metric("💨 Wind", f"{cur.get('wind_speed_10m','—')} km/h")
k[5].metric("🎈 Pressure", f"{cur.get('pressure_msl','—')} hPa")
k[6].metric("☀️ UV", f"{cur.get('uv_index','—')}")

# ============================================================
# AUTOMATED INSIGHTS
# ============================================================
insights = generate_insights(selected_city, cur, fday, hist)

st.markdown('<div class="section-title">💡 Decision Insights</div>', unsafe_allow_html=True)
for insight in insights[:6]:
    st.markdown(f'<div class="insight">{insight}</div>', unsafe_allow_html=True)

# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================
if dashboard_view == "Executive Overview":

    st.markdown('<div class="section-title">📊 Executive Weather Overview</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=fday["time"], y=fday["temperature_2m_max"],
            mode="lines+markers", name="Max temperature"
        ))
        fig.add_trace(go.Scatter(
            x=fday["time"], y=fday["temperature_2m_min"],
            mode="lines+markers", name="Min temperature"
        ))
        fig.update_layout(
            title="16-Day Temperature Corridor",
            template="plotly_white",
            hovermode="x unified",
            height=430,
            margin=dict(l=20,r=20,t=55,b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.bar(
            fday, x="time", y="precipitation_sum",
            title="16-Day Precipitation Forecast",
            labels={"time":"Date","precipitation_sum":"Precipitation (mm)"},
            template="plotly_white"
        )
        fig.update_layout(height=430, margin=dict(l=20,r=20,t=55,b=20))
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        subset = fhour.head(120)
        fig = px.line(
            subset, x="time",
            y=["temperature_2m","apparent_temperature"],
            title="Hourly Temperature & Feels-Like",
            labels={"value":"°C","time":"Time","variable":"Series"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        subset = fhour.head(120)
        fig = px.line(
            subset, x="time",
            y=["relative_humidity_2m","cloud_cover"],
            title="Humidity & Cloud Cover",
            labels={"value":"%","time":"Time","variable":"Series"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Forecast summary table
    st.markdown("### 📅 Forecast Summary")
    summary = fday[[
        "time","temperature_2m_max","temperature_2m_min",
        "precipitation_sum","precipitation_probability_max",
        "wind_speed_10m_max","wind_gusts_10m_max","uv_index_max"
    ]].copy()

    summary.columns = [
        "Date","Max °C","Min °C","Rain mm","Rain Prob %",
        "Max Wind km/h","Max Gust km/h","Max UV"
    ]
    st.dataframe(summary, use_container_width=True, hide_index=True)

# ============================================================
# FORECAST
# ============================================================
elif dashboard_view == "Forecast":

    st.markdown("### 🔮 Operational Forecast")
    st.info(
        "Operational forecast = model-based weather forecast. "
        "The separate 30-day section below is a statistical historical projection."
    )

    tabs = st.tabs(["Temperature", "Rain", "Wind", "Atmosphere", "Solar"])

    with tabs[0]:
        fig = px.line(
            fday, x="time",
            y=["temperature_2m_max","temperature_2m_min"],
            markers=True,
            title="16-Day Temperature Forecast",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        c1,c2 = st.columns(2)
        with c1:
            fig = px.bar(
                fday, x="time", y="precipitation_sum",
                title="Daily Precipitation",
                labels={"precipitation_sum":"mm","time":"Date"},
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.line(
                fhour.head(192), x="time",
                y="precipitation_probability",
                title="Hourly Precipitation Probability",
                labels={"precipitation_probability":"Probability (%)"},
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        c1,c2 = st.columns(2)
        with c1:
            fig = px.line(
                fhour.head(192), x="time",
                y=["wind_speed_10m","wind_gusts_10m"],
                title="Wind Speed & Gusts",
                labels={"value":"km/h","time":"Time","variable":"Series"},
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.line(
                fhour.head(192), x="time",
                y="wind_direction_10m",
                title="Wind Direction",
                labels={"wind_direction_10m":"Degrees","time":"Time"},
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        c1,c2 = st.columns(2)
        with c1:
            fig = px.line(
                fhour.head(192), x="time",
                y=["pressure_msl","surface_pressure"],
                title="Pressure Trend",
                labels={"value":"hPa","time":"Time","variable":"Series"},
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.line(
                fhour.head(192), x="time",
                y="visibility",
                title="Visibility Forecast",
                labels={"visibility":"metres","time":"Time"},
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        fig = px.bar(
            fday, x="time",
            y=["uv_index_max","et0_fao_evapotranspiration"],
            barmode="group",
            title="UV Index & Reference Evapotranspiration",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# HISTORICAL
# ============================================================
elif dashboard_view == "Historical Trends":

    st.markdown("### 📜 Historical Climate Analytics")

    h = hist.copy()
    h["month"] = h["time"].dt.to_period("M").astype(str)

    monthly = h.groupby("month", as_index=False).agg(
        mean_temp=("temperature_2m_mean","mean"),
        max_temp=("temperature_2m_max","max"),
        min_temp=("temperature_2m_min","min"),
        rain=("precipitation_sum","sum"),
        wind=("wind_speed_10m_max","mean"),
        sunshine=("sunshine_duration","sum")
    )

    c1,c2 = st.columns(2)
    with c1:
        fig = px.line(
            monthly, x="month",
            y=["mean_temp","max_temp","min_temp"],
            markers=True,
            title="Monthly Temperature Regime",
            labels={"value":"°C","month":"Month","variable":"Series"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.bar(
            monthly, x="month", y="rain",
            title="Monthly Rainfall",
            labels={"rain":"Rain (mm)","month":"Month"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    c3,c4 = st.columns(2)
    with c3:
        fig = px.area(
            monthly, x="month", y="rain",
            title="Rainfall Accumulation",
            labels={"rain":"Rain (mm)","month":"Month"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        fig = px.line(
            monthly, x="month", y="wind",
            title="Monthly Maximum-Wind Average",
            labels={"wind":"km/h","month":"Month"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🌡 Historical Extremes")
    e = st.columns(5)
    e[0].metric("Mean Temp", f"{nmean(h['temperature_2m_mean']):.1f} °C")
    e[1].metric("Record Max", f"{np.nanmax(h['temperature_2m_max']):.1f} °C")
    e[2].metric("Record Min", f"{np.nanmin(h['temperature_2m_min']):.1f} °C")
    e[3].metric("Total Rain", f"{nsum(h['precipitation_sum']):,.1f} mm")
    e[4].metric("Wet Days", str(int(nsum(h["precipitation_sum"] >= 1))))

    # Distribution
    fig = px.histogram(
        h, x="temperature_2m_mean", nbins=30,
        title="Distribution of Historical Daily Mean Temperature",
        labels={"temperature_2m_mean":"Daily Mean Temperature (°C)"},
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# RAINFALL INTELLIGENCE
# ============================================================
elif dashboard_view == "Rainfall Intelligence":

    st.markdown("### 🌧 Rainfall Intelligence")

    h = hist.copy()
    h["month_num"] = h["time"].dt.month
    h["year"] = h["time"].dt.year
    h["month_name"] = h["time"].dt.strftime("%b")

    monsoon = h[h["month_num"].isin([6,7,8,9])]

    r1,r2,r3,r4 = st.columns(4)
    r1.metric("Period Rain", f"{nsum(h['precipitation_sum']):,.1f} mm")
    r2.metric("Monsoon Rain", f"{nsum(monsoon['precipitation_sum']):,.1f} mm")
    r3.metric("Heavy Days ≥25mm", str(int(nsum(h["precipitation_sum"] >= 25))))
    r4.metric("Extreme Days ≥50mm", str(int(nsum(h["precipitation_sum"] >= 50))))

    monthly = h.groupby(
        h["time"].dt.to_period("M").astype(str), as_index=False
    )["precipitation_sum"].sum()
    monthly.columns = ["month","rain"]

    c1,c2 = st.columns(2)
    with c1:
        fig = px.bar(
            monthly, x="month", y="rain",
            title="Historical Monthly Rainfall",
            labels={"rain":"Rain (mm)","month":"Month"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.histogram(
            h, x="precipitation_sum", nbins=35,
            title="Daily Rainfall Distribution",
            labels={"precipitation_sum":"Daily precipitation (mm)"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- Top 10 all-Pakistan ----------------
    st.markdown("### 🇵🇰 Top 10 Cities by Rainfall — Previous Calendar Year")
    st.caption(
        "This ranking is calculated from the same historical API source for "
        "the registered city grid points. It is not a ranking of individual weather stations."
    )

    previous_year = date.today().year - 1
    start = date(previous_year,1,1).isoformat()
    end = date(previous_year,12,31).isoformat()

    city_tuple = tuple(CITY_LIST)

    @st.cache_data(ttl=CACHE_TTL_HISTORY, show_spinner=False)
    def ranked_city_history(cities, start_date, end_date):
        results = []
        # Parallel I/O dramatically reduces waiting time.
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            futures = {
                ex.submit(get_city_history_total, city, start_date, end_date): city
                for city in cities
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    pass
        return pd.DataFrame(results)

    with st.spinner(f"Fast-fetching rainfall history for {len(CITY_LIST)} cities..."):
        rank_df = ranked_city_history(city_tuple, start, end)

    if len(rank_df):
        top10 = rank_df.sort_values("Rain (mm)", ascending=False).head(10).copy()

        c1,c2 = st.columns(2)
        with c1:
            fig = px.bar(
                top10.sort_values("Rain (mm)"),
                x="Rain (mm)", y="City",
                orientation="h",
                title=f"Top 10 Rainiest Cities — {previous_year}",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = px.pie(
                top10, names="City", values="Rain (mm)",
                hole=.52,
                title=f"Rainfall Share of Top 10 — {previous_year}",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(top10, use_container_width=True, hide_index=True)

    # Monsoon
    st.markdown("### ☔ Monsoon Profile")
    monsoon_monthly = monsoon.groupby(
        monsoon["time"].dt.strftime("%b"), as_index=False
    )["precipitation_sum"].sum()
    monsoon_monthly.columns = ["month","rain"]

    fig = px.bar(
        monsoon_monthly, x="month", y="rain",
        title="Selected City — Monsoon Rainfall",
        labels={"rain":"Rain (mm)","month":"Month"},
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# ATMOSPHERE & WIND
# ============================================================
elif dashboard_view == "Atmosphere & Wind":

    st.markdown("### 🌬 Atmosphere, Pressure & Wind")

    c1,c2 = st.columns(2)

    with c1:
        fig = px.line(
            fhour.head(192), x="time",
            y=["wind_speed_10m","wind_gusts_10m"],
            title="Wind & Gust Timeline",
            labels={"value":"km/h","time":"Time","variable":"Series"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.line(
            fhour.head(192), x="time",
            y=["pressure_msl","surface_pressure"],
            title="Atmospheric Pressure",
            labels={"value":"hPa","time":"Time","variable":"Series"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    c3,c4 = st.columns(2)
    with c3:
        fig = px.scatter(
            fhour.head(192),
            x="temperature_2m",
            y="relative_humidity_2m",
            size="wind_speed_10m",
            title="Temperature vs Humidity",
            labels={
                "temperature_2m":"Temperature (°C)",
                "relative_humidity_2m":"Humidity (%)"
            },
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        fig = px.scatter(
            fhour.head(192),
            x="pressure_msl",
            y="wind_speed_10m",
            size="precipitation",
            title="Pressure vs Wind",
            labels={
                "pressure_msl":"Pressure (hPa)",
                "wind_speed_10m":"Wind (km/h)"
            },
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🧭 Current Wind Vector")
    direction = float(cur.get("wind_direction_10m", 0) or 0)
    speed = float(cur.get("wind_speed_10m", 0) or 0)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=direction,
        title={"text":f"Wind Direction • {speed:.1f} km/h"},
        gauge={
            "axis":{"range":[0,360]},
            "steps":[
                {"range":[0,90]},
                {"range":[90,180]},
                {"range":[180,270]},
                {"range":[270,360]}
            ]
        }
    ))
    fig.update_layout(height=350, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# ALL-CITY COMPARISON — ONE BATCH REQUEST
# ============================================================
elif dashboard_view == "All-City Comparison":

    st.markdown("### 🇵🇰 Pakistan City Weather Matrix")
    st.caption(
        f"Live model-grid comparison across {len(CITY_LIST)} registered locations. "
        "The API supports multiple coordinates in one request, which keeps this view fast."
    )

    try:
        batch = get_forecast_multi(tuple(CITY_LIST))
        rows = []

        for city, payload in zip(CITY_LIST, batch):
            c = payload.get("current", {})
            rows.append({
                "City": city,
                "Temp °C": c.get("temperature_2m"),
                "Feels °C": c.get("apparent_temperature"),
                "Humidity %": c.get("relative_humidity_2m"),
                "Rain mm": c.get("precipitation"),
                "Wind km/h": c.get("wind_speed_10m"),
                "Gust km/h": c.get("wind_gusts_10m"),
                "Pressure hPa": c.get("pressure_msl"),
                "Cloud %": c.get("cloud_cover"),
                "UV": c.get("uv_index"),
                "Condition": weather_label(c.get("weather_code"))
            })

        all_df = pd.DataFrame(rows)

        sort_metric = st.selectbox(
            "Sort by",
            ["Temp °C","Humidity %","Rain mm","Wind km/h","Gust km/h","Pressure hPa","Cloud %","UV"]
        )

        all_df = all_df.sort_values(sort_metric, ascending=False)

        st.dataframe(
            all_df,
            use_container_width=True,
            hide_index=True
        )

        c1,c2 = st.columns(2)
        with c1:
            fig = px.bar(
                all_df.head(15),
                x="City", y="Temp °C",
                title="Hottest 15 Locations",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = px.bar(
                all_df.head(15),
                x="City", y="Humidity %",
                title="Highest Humidity — 15 Locations",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"All-city comparison failed: {e}")

# ============================================================
# 30-DAY HISTORICAL SEASONAL PROJECTION
# ============================================================
st.markdown("---")
st.markdown("### 🧠 30-Day Historical Seasonal Projection")
st.caption(
    "Transparent baseline: historical day-of-year climatology with smoothing. "
    "This is an analytical projection, not a guaranteed weather forecast."
)

projection = seasonal_projection(hist, 30)

if len(projection):
    p1,p2 = st.columns(2)

    with p1:
        fig = px.line(
            projection, x="date", y="Projected Temp (°C)",
            markers=True,
            title="Projected Temperature Pattern",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with p2:
        fig = px.bar(
            projection, x="date", y="Projected Rain (mm)",
            title="Projected Rainfall Pattern",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    q1,q2,q3 = st.columns(3)
    q1.metric(
        "30-Day Projected Rain",
        f"{projection['Projected Rain (mm)'].sum():.1f} mm"
    )
    q2.metric(
        "Projected Mean Temp",
        f"{projection['Projected Temp (°C)'].mean():.1f} °C"
    )
    q3.metric(
        "Projected Wet Days",
        str(int(nsum(projection["Projected Rain (mm)"] >= 1)))
    )
else:
    st.warning("Not enough historical records were returned for a 30-day seasonal projection.")

# ============================================================
# PDF REPORT
# ============================================================
st.markdown("---")
st.markdown("### 📄 Executive PDF Report")

pdf_bytes = make_pdf(
    selected_city,
    cur,
    hist,
    fday,
    projection,
    insights
)

d1,d2 = st.columns([1,3])

with d1:
    st.download_button(
        "📥 Download Enhanced PDF",
        data=pdf_bytes,
        file_name=f"{selected_city.replace(' ','_')}_Weather_Intelligence_Report.pdf",
        mime="application/pdf",
        use_container_width=True
    )

with d2:
    st.markdown(
        '<div class="insight"><b>Report contents:</b> live KPI snapshot, automated insights, '
        'historical climate summary, 16-day forecast, statistical projection and methodology notes.</div>',
        unsafe_allow_html=True
    )

# ============================================================
# DATA SOURCE / METHODOLOGY
# ============================================================
st.markdown("---")
st.markdown(
    '<div class="source-note">'
    '<b>Data & methodology:</b> Forecast and historical weather values are retrieved from Open-Meteo. '
    'The forecast service supports up to 16 forecast days and extensive hourly/daily variables. '
    'Historical weather data are model/reanalysis-based and can differ from individual station observations. '
    'The 30-day projection is a transparent climatological baseline, not an operational numerical forecast. '
    'For safety-critical weather warnings, use official meteorological authorities.'
    '</div>',
    unsafe_allow_html=True
)
