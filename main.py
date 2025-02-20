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
from typing import Tuple, Dict, List, Any

# Constants for timezones and strings
LOCAL_TZ = pytz.timezone('Europe/Berlin')
UTC_TZ = pytz.timezone('UTC')

LIGHT_WARNING = '🚨 Do not forget to bring lights! 🚨\n\n'
WEATHER_DISCLAIMER = "⛈️ Watch the forecast ⛈️\nIf the weather forecast gets worse, we cancel the ride.\n\n"
RACE_DISCLAIMER = "⚠️ No regular ride ⚠️\nThis is not a regular ride. Participation in the race is at your own risk, ZüRides will not take any responsibility, we just ride to the start and back to Zürich together. If you are unsure or have any questions, please get in touch with the organizers.\n\n"
SUBMISSION_FORM_LINK = 'https://docs.google.com/forms/d/e/1FAIpQLScgY8tIqtNKiD6sRei6LXCvFQL3HSFO481xiV9mzF5-85USiw/viewform'
RIDE_LEVELS = ['☕️', '🦵', '🔥']
RANDOM_RIDE_TITELS = [
    "Velodyssey", "Spokes & Scenery", "The Winding Way", "Tarmac Tales",
    "Ride the Horizon", "Two Wheels, One Path", "Echoes of the Road", "The Long Arc",
    "Serpentine Symphony", "Chasing the Curve", "Ribbons of Asphalt", "Wanderlust on Wheels",
    "The Hidden Route", "Through Valleys & Vistas", "Saddle Stories", "Where the Road Unfolds",
    "The Turning Point", "Rolling Through Time", "Lost in the Ride", "Shadows & Switchbacks"
]

# Dictionaries for months and weekdays
MONTHS = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
    7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

WEEKDAYS = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
]

# Predefined meeting points with coordinates
MEETING_POINTS = {
    'Fork & Bottle parking lot': (47.35262, 8.52454),
    'Frohburg-/Letzistrasse': (47.39252, 8.55045), 
    'Thiwa\'s Cafe, Triemli': (47.36783, 8.49466), 
    'OIL! petrol station, Fronwaldstrasse': (47.41510, 8.51845),
    'Graveyard Witikon': (47.36144, 8.60253),
    'Train station Tiefenbrunnen': (47.35007, 8.56122)
}

organizers_list = list(st.secrets['organizers'].keys())


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
    _dist_to_mp = [haversine(mp, point, unit=Unit.METERS) for _, mp in MEETING_POINTS.items()]
    _closest_index = np.argmin(_dist_to_mp)
    return list(MEETING_POINTS.keys())[_closest_index] 


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
            tzinfo=UTC_TZ #pytz.timezone('UTC')
        ).astimezone(
            LOCAL_TZ #pytz.timezone('CET')
        )
    else:
        print('Bad request! Using default sunset time 8:00 PM')
        _sunset_datetime = datetime.datetime(
            date.year, date.month, date.day, 
            20, 00, tzinfo=pytz.timezone('CET')
            )

    return _sunset_datetime


st.title(f'Post creator for [ZüRides]({SUBMISSION_FORM_LINK})')
st.header('Input')
with st.form('Input'):
    cb_col1, cb_col2, cb_col3 = st.columns(3)
    with cb_col1:
        add_weather_disclaimer = st.checkbox('Weather disclaimer ⛈️')
    with cb_col2:
        add_race_disclaimer = st.checkbox('Race disclaimer 🚴💨')
    with cb_col3:
        is_mtb_ride = st.checkbox('Gravel/XC ride 🚵')

    default_datetime = datetime.datetime.now() + datetime.timedelta(days=1)
    default_date = default_datetime.astimezone(LOCAL_TZ).date()
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        d = st.date_input(
            "What date does the ride take place?", default_date
        )
    month_num = d.month
    month_name = MONTHS[month_num]
    day = d.day
    weekday_name = WEEKDAYS[d.weekday()]
    with r_col2:
        meeting_time = st.time_input(
            'What time do we start?', 
            datetime.time(10, 00) if weekday_name in ['Saturday', 'Sunday'] else datetime.time(18, 00))
    meeting_time_str = meeting_time.strftime('%H:%M')

    organizers = st.multiselect(
        'Who organizes the ride',
        organizers_list
        )
    organizers = [f"{i} ({st.secrets['organizers'][i]})" for i in organizers]
    organizers_str = ', '.join(sorted(organizers)) if organizers else '⚠️_unsupervised group ride_⚠️'

    ride_level = st.radio('Choose your ride level:',RIDE_LEVELS, index=1, horizontal=True)
    # TODO Replace the following line with an estimate function
    ride_speed = st.slider('What is the expected average speed in km/h?', min_value=20, max_value=32, value= 26)
    st.caption("For Gravel/XC rides, the 10km/h will be substracted from the selected speed")


    link_input = st.text_input('Paste URL of public Strava route:')
    s = re.search(r"^https?://[\w\d]+\.?strava.com/routes/(\d+)", link_input.strip())

    submitted = st.form_submit_button("Create post")

if submitted:
    # Load gpx file from Strava
    gpx = get_route(s.group(1))

    route_title = gpx.name.strip()
    if not re.search('[a-zA-Z]{3,}', route_title):
        route_title = np.random.choice(RANDOM_RIDE_TITELS)

    if is_mtb_ride:
        route_title += " - Gravel/CX ride"
        ride_speed = ride_speed -10
    
    
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

    dist_to_mp = [haversine(mp, points[0], unit=Unit.METERS) for _, mp in MEETING_POINTS.items()]
    closest_index = np.argmin(dist_to_mp)
    meeting_point = list(MEETING_POINTS.keys())[closest_index]
    
    text = f'*— {weekday_name}, {month_name} {day} —*\n\nSign up here:  registration.zürides.ch\nSelect the ride you prefer, make sure you received the confirmation email, and please use the link in that email if you want to remove or change your registration.\n\n'
    return_time = \
        LOCAL_TZ.localize(
            datetime.datetime(d.year, d.month, d.day, meeting_time.hour, meeting_time.minute)
        ) + \
        datetime.timedelta(hours=route_distance/ride_speed * 1.2 + 0.3)
    sunset_time = get_sunset_time(d) # datetime.datetime(d.year, d.month, d.day, 20, 00)
    if  return_time > sunset_time: text += LIGHT_WARNING
    text += f'*{route_title}*\n'
    text += f'{organizers_str}\n'
    text += f'*Route*: {route_distance}km, {route_elevation_gain}m, strava.com/routes/{s.group(1)}\n' # gpx.link
    if is_mtb_ride: ride_level = '⛰️'
    text += f'*Ride level*: {ride_level}, ~{ride_speed}km/h\n'
    text += f'*Meeting time & place*: {meeting_time_str} at {meeting_point}\n'
    if type(gpx.description) == str: 
        text += f'{gpx.description.strip()}\n\n'
    else:
        text += '\n'
    if add_race_disclaimer: text += RACE_DISCLAIMER
    if add_weather_disclaimer: text += WEATHER_DISCLAIMER
    if is_mtb_ride:
        text += 'Thanks & see you on the dirt! 🫎'
    else:
        text += 'Thanks & see you on the road 👋'

    st.header('Output for copy\'n\'paste to WhatsApp')
    st.code(text, language=None)

    text_short = f'{route_title} @ {meeting_point}'
    st.header(f'Output for copy\'n\'paste to [submission form]({SUBMISSION_FORM_LINK})')
    st.code(text_short, language=None)
