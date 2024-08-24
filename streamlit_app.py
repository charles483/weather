# -*- coding: utf-8 -*-
"""
Streamlit Weather App
=====================
This file is part of the Streamlit Weather App project which is licensed under the Apache License 2.0.
See the LICENSE file for more details.

Copyright 2024 Charles Churu

This is a basic Streamlit webapp displaying the current temperature, wind speed
and wind direction as well as the temperature and precipitation forecast for 
the week ahead at one of 40,000+ cities and towns around the globe. The weather
forecast is given in terms of the actual timezone of the city of interest.
Additionally, a map with the location of the requested city is displayed.

- The weather data is from http://open-meteo.com
- The list with over 40,000 cities around world stems from 
  https://simplemaps.com/data/world-cities

Enjoy exploring!

"""

import streamlit as st
import pandas as pd
import requests
import json
from plotly.subplots import make_subplots
import plotly.graph_objs as go
from datetime import datetime
from datetime import timezone as tmz
import pytz
from timezonefinder import TimezoneFinder
import folium
from streamlit_folium import folium_static
import plotly.express as px

# Title and description for your app
st.title("How's the weather? :sun_behind_rain_cloud:")

st.subheader("Choose location")

file = "worldcities.csv"
data = pd.read_csv(file)

# Default values
default_country = 'Kenya'
default_city = 'Nyeri'

# Select Country
country_set = set(data["country"])
country = st.selectbox('Select a country', options=country_set, index=list(country_set).index(default_country))

country_data = data[data["country"] == country]

city_set = country_data["city_ascii"].unique()

city = st.selectbox('Select a city', options=city_set, index=list(city_set).index(default_city))

lat = float(country_data[country_data["city_ascii"] == city]["lat"])
lng = float(country_data[country_data["city_ascii"] == city]["lng"])

try:
    response_current = requests.get(f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true')
    response_current.raise_for_status()
    result_current = response_current.json()
    current = result_current["current_weather"]
    temp = current["temperature"]
    speed = current["windspeed"]
    direction = current["winddirection"]

    # Determine wind direction
    ddeg = 11.25
    if direction >= (360 - ddeg) or direction < (0 + ddeg):
        common_dir = "N"
    elif direction >= (337.5 - ddeg) and direction < (337.5 + ddeg):
        common_dir = "N/NW"
    elif direction >= (315 - ddeg) and direction < (315 + ddeg):
        common_dir = "NW"
    elif direction >= (292.5 - ddeg) and direction < (292.5 + ddeg):
        common_dir = "W/NW"
    elif direction >= (270 - ddeg) and direction < (270 + ddeg):
        common_dir = "W"
    elif direction >= (247.5 - ddeg) and direction < (247.5 + ddeg):
        common_dir = "W/SW"
    elif direction >= (225 - ddeg) and direction < (225 + ddeg):
        common_dir = "SW"
    elif direction >= (202.5 - ddeg) and direction < (202.5 + ddeg):
        common_dir = "S/SW"
    elif direction >= (180 - ddeg) and direction < (180 + ddeg):
        common_dir = "S"
    elif direction >= (157.5 - ddeg) and direction < (157.5 + ddeg):
        common_dir = "S/SE"
    elif direction >= (135 - ddeg) and direction < (135 + ddeg):
        common_dir = "SE"
    elif direction >= (112.5 - ddeg) and direction < (112.5 + ddeg):
        common_dir = "E/SE"
    elif direction >= (90 - ddeg) and direction < (90 + ddeg):
        common_dir = "E"
    elif direction >= (67.5 - ddeg) and direction < (67.5 + ddeg):
        common_dir = "E/NE"
    elif direction >= (45 - ddeg) and direction < (45 + ddeg):
        common_dir = "NE"
    elif direction >= (22.5 - ddeg) and direction < (22.5 + ddeg):
        common_dir = "N/NE"

    st.info(f"The current temperature is {temp} °C.\nThe wind speed is {speed} m/s.\nThe wind is coming from {common_dir}.")

    st.subheader("Week ahead")
    st.write('Temperature and rain forecast one week ahead & city location on the map', unsafe_allow_html=True)

    with st.spinner('Loading...'):
        try:
            response_hourly = requests.get(f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&hourly=temperature_2m,precipitation')
            response_hourly.raise_for_status()
            result_hourly = response_hourly.json()
            hourly = result_hourly["hourly"]
            hourly_df = pd.DataFrame.from_dict(hourly)
            hourly_df.rename(columns={'time': 'Week ahead', 'temperature_2m': 'Temperature °C', 'precipitation': 'Precipitation mm'}, inplace=True)

            # Use TimezoneFinder to determine timezone
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lng=lng, lat=lat)
            if timezone_str is None:
                timezone_str = 'UTC'

            timezone_loc = pytz.timezone(timezone_str)
            dt = datetime.now()
            tzoffset = timezone_loc.utcoffset(dt)

            # Create figure with secondary y axis
            fig = make_subplots(specs=[[{"secondary_y": True}]])

            week_ahead = pd.to_datetime(hourly_df['Week ahead'], format="%Y-%m-%dT%H:%M")

            fig.add_trace(go.Scatter(x=week_ahead + tzoffset, y=hourly_df['Temperature °C'], name="Temperature °C"), secondary_y=False)
            fig.add_trace(go.Bar(x=week_ahead + tzoffset, y=hourly_df['Precipitation mm'], name="Precipitation mm"), secondary_y=True)

            time_now = datetime.now(tmz.utc) + tzoffset
            fig.add_vline(x=time_now, line_color="red", opacity=0.4)
            fig.add_annotation(x=time_now, y=max(hourly_df['Temperature °C']) + 5, text=time_now.strftime("%d %b %y, %H:%M"), showarrow=False, yshift=0)

            fig.update_yaxes(range=[min(hourly_df['Temperature °C']) - 10, max(hourly_df['Temperature °C']) + 10], title_text="Temperature °C", secondary_y=False, showgrid=False, zeroline=False)
            fig.update_yaxes(range=[min(hourly_df['Precipitation mm']) - 2, max(hourly_df['Precipitation mm']) + 8], title_text="Precipitation (rain/showers/snow) mm", secondary_y=True, showgrid=False)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=0.7))

            # Map customization
            map_style = st.selectbox("Select map style", ["OpenStreetMap", "TopoMap", "Satellite"])
            map_tiles = {
                "OpenStreetMap": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "TopoMap": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
                "Satellite": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
            }
            attr = {
                "OpenStreetMap": "Map data © OpenStreetMap contributors",
                "TopoMap": "Map tiles by OpenTopoMap, under ODbL.",
                "Satellite": "Map tiles by CartoDB, under CC BY 3.0."
            }.get(map_style, "Map data © OpenStreetMap contributors")

            tiles_url = map_tiles.get(map_style, map_tiles["OpenStreetMap"])

            m = folium.Map(
                location=[lat, lng],
                zoom_start=7,
                tiles=tiles_url,
                attr=attr
            )
            folium.Marker([lat, lng], popup=city + ', ' + country, tooltip=city + ', ' + country).add_to(m)
            folium_static(m)

            st.plotly_chart(fig)
        except requests.RequestException as e:
            st.error(f"Error fetching hourly forecast data: {e}")

    # Historical Weather Data
    st.subheader("Historical Weather")
    date = st.date_input("Select a date", datetime.today())
    if date:
        try:
            response_historical = requests.get(f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&start={date}&end={date}&hourly=temperature_2m,precipitation')
            response_historical.raise_for_status()
            result_historical = response_historical.json()
            historical_df = pd.DataFrame.from_dict(result_historical["hourly"])
            historical_df.rename(columns={'time': 'Time', 'temperature_2m': 'Temperature °C', 'precipitation': 'Precipitation mm'}, inplace=True)
            st.write(historical_df)
        except requests.RequestException as e:
            st.error(f"Error fetching historical weather data: {e}")

    # Compare Weather Between Cities
    st.subheader("Compare Weather Between Cities")
    cities = st.multiselect('Select cities', options=city_set)
    if cities:
        comparison_data = {}
        for city in cities:
            lat_city = float(country_data[country_data["city_ascii"] == city]["lat"])
            lng_city = float(country_data[country_data["city_ascii"] == city]["lng"])
            try:
                response_city = requests.get(f'https://api.open-meteo.com/v1/forecast?latitude={lat_city}&longitude={lng_city}&current_weather=true')
                response_city.raise_for_status()
                comparison_data[city] = response_city.json()["current_weather"]
            except requests.RequestException as e:
                comparison_data[city] = {"error": str(e)}

        # Convert comparison data to DataFrame
        comparison_df = pd.DataFrame(comparison_data).T
        st.write(comparison_df)

        # Plot temperature comparison
        if 'temperature' in comparison_df.columns:
            fig_temp = px.bar(comparison_df, x=comparison_df.index, y='temperature', title='Temperature Comparison Between Cities', labels={'temperature': 'Temperature (°C)'})
            st.plotly_chart(fig_temp)

        # Plot wind speed comparison
        if 'windspeed' in comparison_df.columns:
            fig_speed = px.bar(comparison_df, x=comparison_df.index, y='windspeed', title='Wind Speed Comparison Between Cities', labels={'windspeed': 'Wind Speed (m/s)'})
            st.plotly_chart(fig_speed)

        # Plot precipitation comparison
        if 'precipitation' in comparison_df.columns:
            fig_precip = px.bar(comparison_df, x=comparison_df.index, y='precipitation', title='Precipitation Comparison Between Cities', labels={'precipitation': 'Precipitation (mm)'})
            st.plotly_chart(fig_precip)

    # What to Wear or Do?
    st.subheader("What to Wear or Do?")
    if temp < 10:
        st.write("It's chilly! Wear a warm jacket.")
    elif temp > 25 and speed < 5:
        st.write("It's warm and calm. Perfect day for a walk!")
    else:
        st.write("Weather is moderate, dress comfortably.")

    # Temperature Animation
    st.subheader("Temperature Animation")
    fig_animation = px.line(hourly_df, x=week_ahead + tzoffset, y="Temperature °C", animation_frame="Week ahead", range_y=[-10, 40])
    st.plotly_chart(fig_animation)

    # Local Time and Sun Times
    st.subheader("Local Time and Sun Times")
    try:
        response_sun = requests.get(f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&daily=sunrise,sunset')
        response_sun.raise_for_status()
        sun_times = response_sun.json()
        sunrise = sun_times['daily']['sunrise'][0]
        sunset = sun_times['daily']['sunset'][0]
        st.write(f"Local Time: {datetime.now(pytz.timezone(timezone_str)).strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"Sunrise: {sunrise}, Sunset: {sunset}")
    except requests.RequestException as e:
        st.error(f"Error fetching sun times: {e}")

except requests.RequestException as e:
    st.error(f"Error fetching current weather data: {e}")

st.write('---')
st.write('Data source: [open-meteo.com](http://open-meteo.com)')
st.write('City data source: [simplemaps.com](https://simplemaps.com/data/world-cities)')
