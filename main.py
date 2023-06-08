#! /usr/bin/python3

import streamlit as st
import re
import requests
import numpy as np
import gpxpy
import gpxpy.gpx
from haversine import haversine, Unit
import datetime
import pytz

local_tz = pytz.timezone('Europe/Berlin')
utc_tz = pytz.timezone('UTC')

months = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
}

weekdays = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
    'Friday', 'Saturday', 'Sunday'
]

meeting_points = {
    'Fork & Bottle parking lot': (47.35262, 8.52454),
    'Frohburg-/Letzistrasse': (47.39252, 8.55045), 
    'Thiwa\'s Cafe, Triemli': (47.36783, 8.49466), 
    'OIL! petrol station, Fronwaldstrasse': (47.41510, 8.51845),
    'Graveyard Witikon': (47.36144, 8.60253),
    'Train station Tiefenbrunnen': (47.35007, 8.56122)
}

organizers_list = list(st.secrets['organizers'].keys())

light_warning = '🚨 Do not forget to bring lights! 🚨\n\n'
weather_disclaimer = "⛈️ Watch the forecast ⛈️\nIf the weather forecast gets worse, we cancel the ride.\n\n"
race_disclaimer = "⚠️ No regular ride ⚠️\nThis is not a regular ride. Participation in the race is at your own risk, ZüRides will not take any responsibility, we just ride to the start and back to Zürich together. If you are unsure or have any questions, please get in touch with the organizers.\n\n"
submission_form_link = 'https://docs.google.com/forms/d/e/1FAIpQLScgY8tIqtNKiD6sRei6LXCvFQL3HSFO481xiV9mzF5-85USiw/viewform'


def get_route(route_id: str) -> gpxpy.gpx.GPX:
    _r = requests.get(st.secrets['get_route_url'] + route_id)
    if _r.status_code == 200:
        return gpxpy.parse(_r.text)
    else:
        raise _r.raise_for_status()
    

def get_distance(start: dict, end: dict) -> any:
    return haversine(
        (start['lat'], start['lon']),
        (end['lat'], end['lon']),
        unit=Unit.METERS
    )


def get_closest_meeting_point(point: dict) -> str:
    _dist_to_mp = [haversine(mp, point, unit=Unit.METERS) for _, mp in meeting_points.items()]
    _closest_index = np.argmin(_dist_to_mp)
    return list(meeting_points.keys())[_closest_index] 


def preprocess_route(gpx: gpxpy.gpx.GPX) -> list:
    return []


def get_sunset_time(date: datetime.date, loc= {'lat': 47.3769, 'lon': 8.5417}) -> datetime.datetime:
    # Default location: Zurich
    # API: https://sunrisesunset.io/api/
    _date_str = date.strftime("%Y-%m-%d")
    _sunset_request = requests.get(f'https://api.sunrisesunset.io/json?timezone=UTC&lat={loc["lat"]}&lng={loc["lon"]}&date={_date_str}')

    if _sunset_request.status_code == 200:
        _sunset_json = _sunset_request.json()
        _sunset_time_str = _sunset_json['results']['sunset']
        _sunset_datetime = datetime.datetime.strptime(
            f'{_date_str} {_sunset_time_str}', '%Y-%m-%d %I:%M:%S %p'
        ).replace(
            tzinfo=utc_tz #pytz.timezone('UTC')
        ).astimezone(
            local_tz #pytz.timezone('CET')
        )
    else:
        print('Bad request! Using default sunset time 8:00 PM')
        _sunset_datetime = datetime.datetime(
            date.year, date.month, date.day, 
            20, 00, tzinfo=pytz.timezone('CET')
            )

    return _sunset_datetime


st.title(f'Post creator for [ZüRides]({submission_form_link})')
st.header('Input')
with st.form('Input'):
    default_datetime = datetime.datetime.now() + datetime.timedelta(days=1)
    default_date = default_datetime.astimezone(local_tz).date()

    d = st.date_input(
        "What date does the ride take place?", default_date
    )
    month = d.month
    month_str = months[month]
    day = d.day
    weekday = weekdays[d.weekday()]

    meeting_time = st.time_input(
        'What time do we start?', 
        datetime.time(10, 00) if weekday in ['Saturday', 'Sunday'] else datetime.time(18, 00))
    meeting_time_str = meeting_time.strftime('%H:%M')

    organizers = st.multiselect(
        'Who organizes the ride',
        organizers_list
        )
    organizers = [f"{i} ({st.secrets['organizers'][i]})" for i in organizers]
    organizers_str = ', '.join(sorted(organizers))

    ride_level = st.radio('Choose your ride level:',['☕️', '🦵','🔥'], index=1, horizontal=True)
    # TODO Replace the following line with an estimate function
    ride_speed = st.slider('What is the expected average speed in km/h?', min_value=20, max_value=32, value= 26)

    cb_col1, cb_col2 = st.columns(2)
    with cb_col1:
        add_weather_disclaimer = st.checkbox('Weather disclaimer ⛈️')
    with cb_col2:
        add_race_disclaimer = st.checkbox('Race disclaimer 🚴💨')

    link_input = st.text_input('Paste URL of public Strava route:')
    s = re.search(r"^https?://[\w\d]+\.?strava.com/routes/(\d+)", link_input.strip())

    submitted = st.form_submit_button("Create post")

if submitted:
    # Load gpx file from Strava
    gpx = get_route(s.group(1))

    route_title = gpx.name.strip()
    route_distance = int(np.ceil(gpx.length_3d()/1000))
    points = [
        (point.latitude, point.longitude) 
        for track in gpx.tracks for segment in track.segments for point in segment.points
    ]
    if gpx.has_elevations:
        elevations = [point.elevation for track in gpx.tracks for segment in track.segments for point in segment.points]
        diffs = np.diff(elevations)
        route_elevation_gain = int(np.ceil(np.sum(diffs[diffs > 0])))
    else:
        route_elevation_gain = 'n/a '

    dist_to_mp = [haversine(mp, points[0], unit=Unit.METERS) for _, mp in meeting_points.items()]
    closest_index = np.argmin(dist_to_mp)
    meeting_point = list(meeting_points.keys())[closest_index]
    
    text = f'*— {weekday}, {month_str} {day} —*\n\nSign up here:  https://registration.zürides.ch/\nSelect the ride you prefer, make sure you received the confirmation email, and please use the link in that email if you want to remove or change your registration.\n\n'
    return_time = \
        local_tz.localize(
            datetime.datetime(d.year, d.month, d.day, meeting_time.hour, meeting_time.minute)
        ) + \
        datetime.timedelta(hours=route_distance/ride_speed * 1.2 + 0.3)
    sunset_time = get_sunset_time(d) # datetime.datetime(d.year, d.month, d.day, 20, 00)
    if  return_time > sunset_time: text += light_warning
    text += f'*{route_title}*\n'
    text += f'{organizers_str}\n'
    text += f'*Route*: {route_distance}km, {route_elevation_gain}m, {gpx.link}\n'
    text += f'*Ride level*: {ride_level}, ~{ride_speed}km/h\n'
    text += f'*Meeting time & place*: {meeting_time_str} at {meeting_point}\n'
    if type(gpx.description) == str: 
        text += f'{gpx.description.strip()}\n\n'
    else:
        text += '\n'
    if add_race_disclaimer: text += race_disclaimer
    if add_weather_disclaimer: text += weather_disclaimer
    text += 'Thanks & see you on the road 👋'

    st.header('Output for copy\'n\'paste to WhatsApp')
    st.code(text, language=None)

    text_short = f'{route_title} @ {meeting_point}'
    st.header('Output for copy\'n\'paste to submission form')
    st.code(text_short, language=None)

