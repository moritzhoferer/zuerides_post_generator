"""
# My first app
Here's our first attempt at using data to create a table:
"""

import streamlit as st
import numpy as np
import gpxpy
import gpxpy.gpx
import datetime

months = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
}

weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
            'Friday', 'Saturday', 'Sunday']


st.title('Post creator for ZüRides 🚴')
st.header('Input')

organizers = st.multiselect(
    'Who organizes the ride',
    ['Alex', 'Andrew', 'Beat', 'Boris', 'Dominic', 'Iris', 'Julius', 'Katja', 'Manu', 'Maria', 'Max', 'Moritz', 'Nino', 'Sofia']
    )
organizers_str = ','.join(organizers)
d = st.date_input(
    "What date does the ride take place?",
    datetime.date.today() + datetime.timedelta(days=1))
month = d.month
month_str = months[month]
day = d.day
weekday = weekdays[d.weekday()]
meeting_time = st.time_input('What time do we start?', datetime.time(18,00))
meeting_time_str = meeting_time.strftime('%H:%M')

uploaded_files = st.file_uploader("Choose a gpx file", accept_multiple_files=False)
if uploaded_files is not None:
    gpx = gpxpy.parse(uploaded_files)

    route_title = gpx.name
    route_distance = int(np.ceil(gpx.length_3d()/1000))
    if gpx.has_elevations:
        elevations = [point.elevation for track in gpx.tracks for segment in track.segments for point in segment.points]
        diffs = np.diff(elevations)
        route_elevation_gain = int(np.ceil(np.sum(diffs[diffs > 0])))
    else:
        route_elevation_gain = None
    
    route_description = gpx.description
    route_link = gpx.link

meeting_point = st.selectbox(
    'Where do we meet?',
    ['Fork & Bottle parking lot', 'Frohburg-/Letzistrasse', 
     'Thiwa\'s Cafe, Triemli', 'OIL! petrol station, Fronwaldstrasse'])


ride_level = '🦵'
ride_speed = 26

if uploaded_files is not None:
    text = \
        f'*— {weekday}, {month_str} {day} —*\n\nSign up here:  https://registration.zürides.ch/\nSelect the ride you prefer, make sure you received the confirmation email, and please use the link in that email if you want to remove or change your registration.\n\n🚨 Do not forget to bring lights! 🚨\n\n' + \
        f'*{route_title}*\n' + \
        f'{organizers_str}\n' + \
        f'*Route*: {route_distance}km, {route_elevation_gain}m, {route_link}\n' + \
        f'*Ride level*: {ride_level}, ~{ride_speed}km/h\n' + \
        f'*Meeting time & place*: {meeting_time_str} at {meeting_point}\n' + \
        f'{route_description}\n\nThanks & see you on the road. '
    st.header('Output for copy\'n\'paste to WhatsApp')
    st.code(text, language=None)

