import streamlit as st
import os
import json
import re
import requests
import pandas as pd
import us
import zoneinfo
import time
# import datetime
from datetime import datetime, timedelta
from dateutil import tz
from timezonefinder import TimezoneFinder


def get_timezone(lat, lng):
    tf = TimezoneFinder()
    tz = tf.timezone_at(lat=lat, lng=lng)
    return tz

# from streamlit.components.v1 import html
#
#
# # Define javascript
# my_js = """
# <!DOCTYPE html>
# <html>
# <body>
#
# <button onclick="getLocation()">Try It</button>
#
# <p id="demo"></p>
#
# <script>
# const x = document.getElementById("demo");
# const gps = new Array(position.coords.latitude, position.coords.longitude);
#
# function getLocation() {
#   if (navigator.geolocation) {
#     navigator.geolocation.getCurrentPosition(showPosition);
#     return gps;
#   } else {
#     x.innerHTML = "Geolocation is not supported by this browser.";
#   }
# }
#
# function showPosition(position) {
#   x.innerHTML = "Latitude: " + position.coords.latitude +
#   "<br>Longitude: " + position.coords.longitude;
# }
# </script>
#
# </body>
# </html>
# """


@st.cache_data(ttl=60*60*12)
def get_merry_sky(lat, lon):
    m_weather = requests.get(f"https://api.merrysky.net/weather?q={lat},{lon}&source=pirateweather")
    m_json = m_weather.json()
    merry_sky_hourly = m_json.get("hourly").get("data")
    return merry_sky_hourly


def get_info(hour_w, lat, lon):
    now = datetime.now()
    rounded_value = now.replace(second=0, microsecond=0, minute=0, hour=hour_w)
    m_hourly = get_merry_sky(lat, lon)
    adj_now = rounded_value.timestamp()
    # time = datetime.fromtimestamp(adj_now).strftime('%Y-%m-%d %H:%M:%S')
    time = datetime.fromtimestamp(adj_now)
    for i in m_hourly:
        if i["time"] == adj_now:
            temp_C = i["temperature"]
            temp_F = (temp_C * 9/5) + 32
            feels_likeC = i["apparentTemperature"]
            feels_likeF = (feels_likeC * 9 / 5) + 32
            precip = i["precipProbability"] * 100
            dewpoint_C = i["dewPoint"]
            dewpoint_F = (dewpoint_C * 1.8) + 32
            rel_hum = i["humidity"] * 100
            wind_speed = i["windSpeed"] * 2.23694
            wind_gust = i["windGust"] * 2.23694
            windBearing = i["windBearing"]
            wind_dir = degToCompass(windBearing)
            cloudiness = i["summary"]
            cloud_cover = i["cloudCover"] * 100
            vis = i["visibility"] * 0.621371
            precip_amount = round(i["precipAccumulation"]/25.4, 1)
            precip_type = i["precipType"]

    print_out2 = f'''
{cloudiness}, {temp_F:.1f}F/{temp_C:.1f}C
Feel: {feels_likeF:.1f}F/{feels_likeC:.1f}C 
Wind: {wind_dir}, {wind_speed:.1f} - {wind_gust:.1f}mph
Clouds: {cloud_cover}%
Precip: {precip:.1f}%{'' if precip_amount < 0.1 else f", {precip_amount}in of {precip_type}"}
Rel Humidity: {rel_hum:.1f}%
Dewpoint: {dewpoint_F:.1f}F ({dewpoint_C:.1f}C)
Visibility: {vis:.01f}mi
Last update: {time.astimezone(tz.gettz(get_timezone(lat, lon))).strftime('%Y-%m-%d %H:%M:%S')}'''

    st.code(print_out2, language='None')


def degToCompass(num):
    val = int((num/22.5)+.5)
    arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return arr[(val % 16)]


def get_filename(filename):
    file_dir = os.path.dirname(__file__)
    return os.path.join(file_dir, 'resources', filename)


def load_csv(filename):
    csv = pd.read_csv(get_filename(filename))
    return csv.sort_values(by=csv.columns[0])


@st.cache_data
def state_dropdown_options():
    state_options = load_csv('state_abbr.csv')
    return state_options


@st.cache_data
def load_eBird_hotspots(state):
    with open(f'resources/{state}_hotspots.json', encoding="utf-8") as f:
        eBird_hotspots = json.load(f)
    return eBird_hotspots


def eBird_hotspots_options(col, hotspots):
    loc_name = [d.get(col) for d in hotspots]
    return loc_name


def location_value(col, hotspots, x, y):
    col_value = [d.get(col) for d in hotspots if d.get(x) == y]
    return col_value[0]


def eBird_hotspot_dropdown(data, weather_time):
    st.selectbox("Ebird Hotspot:", eBird_hotspots_options('locName', data), index=None,
             key="filter_hotspot")  # use to reference locName from hotspots
    if st.session_state.filter_hotspot:
        lat_input = location_value('lat', data, 'locName', st.session_state.filter_hotspot)
        lon_input = location_value('lng', data, 'locName', st.session_state.filter_hotspot)
        # st.write(lat_input, lon_input)

        get_info(weather_time.hour, lat_input, lon_input)


def main():
    st.title("eBird Weather")
    weather_time = datetime.today()

    state_col1, state_col2 = st.columns([1, 1.5])
    state_col1.radio("State", ["VA", "NY", "Other State"], horizontal=True, label_visibility="collapsed", key="radio_state")
    if st.session_state.radio_state != "Other State":
        hotspot_data = load_eBird_hotspots(st.session_state.radio_state)
        time_zone = 'America/New_York'
        st.write(time_zone)

    if st.session_state.radio_state == "Other State":
        state_col2.selectbox("State:", state_dropdown_options(), index=None, label_visibility="collapsed", key="filter_state")
        if st.session_state.filter_state:
            hotspot_data = load_eBird_hotspots(st.session_state.filter_state)
            time_zone = us.states.lookup(st.session_state.filter_state).capital_tz
            st.write(time_zone)

    time_col1, time_col2 = st.columns([1, 1.5])
    time_col1.radio("Time", ["Current", "Other Time"], horizontal=True, label_visibility="collapsed",
              key="radio_time")
    st.write(time.time())
    st.write(datetime.now())
    st.write(datetime.now(zoneinfo.ZoneInfo(time_zone)))
    # st.write(datetime.timestamp(time.time()))
    # st.write(time.astimezone(tz.gettz(get_timezone(lat, lon))).strftime('%Y-%m-%d %H:%M:%S'))
    if st.session_state.radio_time == "Other Time":
        weather_time = time_col2.time_input('Input time', datetime.now(), label_visibility="collapsed", step=3600)


    eBird_hotspot_dropdown(hotspot_data, weather_time)












        # start = time.time()
        # st.write('First! Time', int((time.time() - start) * 10) / 10.0, 'SECONDS')


# Run main
if __name__ == "__main__":
    st.set_page_config(page_icon='💨', initial_sidebar_state='expanded')
    main()

37.092726, -76.273583
