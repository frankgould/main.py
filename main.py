#!/usr/bin/python3
# -*- coding: utf-8 -*-
#app name: main.py
#operation: RPi/Android Automated SlideShow Display App.

from __future__ import print_function
import os
from kivy.utils import platform
#print ('++++++++++++++++++++++++ platform == ' + platform)
if platform == 'android':
    os.environ['KIVY_HOME'] = "/sdcard/.slideshow/"
    os.environ["KIVY_WINDOW"] = "sdl2"
    os.environ["KIVY_GL_BACKEND"] = "sdl2"
    os.environ["KIVY_AUDIO"] = "sdl2"
    from android.permissions import request_permissions, Permission
#    android_permissions = False
    def callback(permission,results):
        if all([res for res in results]): 
#            android_permissions = True
            print ('++++++++++++++++++++++++ permissions accepted')
        else:
            print ('++++++++++++++++++++++++ permissions denied')
    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE], callback)

import sys, time, random, subprocess, gc, ssl, smtplib, configparser, json, codecs, html
from platform import system
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition
from kivy.animation import Animation
from moretransitions import PixelTransition, RippleTransition, BlurTransition, RVBTransition, RotateTransition
from kivy.properties import StringProperty
from kivy.clock import Clock, ClockEvent, ClockBase
from kivy.uix.image import Image as Image_source
from kivy.logger import Logger
from datetime import datetime, timedelta
from kivy.event import *
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.graphics import *
from kivy.uix.widget import Widget
from array import *
from decimal import *
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from shutil import copy2, copytree, copyfile
from kivy.uix.image import AsyncImage

from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window

import requests, pickle, httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from oauth2client.client import GoogleCredentials
from google.auth.transport.requests import Request
from astral import Astral
import ss_utils
import calendar

from pygame import mixer
mixer.init()

import atexit
def shutdown():
    logger.critical('Shutdown occurred, turning screen back on.')
    wake_screen()
atexit.register(shutdown)

#NOTE: 01.06 contained changes to NEXT ending by removing redundant 'if frame_sleeping' that will never happen and changing elif.
__version__ = "23.05.27"
dev_version = "23.05.27"

## setup logging: use .kivy/config.ini for configuration
logger=Logger
slideshow_started_datetime = str(datetime.now())[0:19]
logger.info('Log Started: Slideshow Version ' + dev_version + ', Platform: ' + str(platform) + ' @ ' + slideshow_started_datetime)

if platform == 'android': 
	logger.info('Android Permissions Affirmed: ' + str(android_permissions))
	from android.storage import primary_external_storage_path
	ss_path = primary_external_storage_path() + '/.slideshow/'
else: 
	ss_path = os.path.dirname(os.path.realpath(sys.argv[0])) + '/'
ss_data_path = ss_path + 'data/'

# Caption and digitalclock fonts and Color Lookup Table
file_lines=[]
color_lut={}

temp_text=open(ss_data_path + 'ss_color_lut.dat','r')
temp_check=temp_text.readlines()
for file_row in temp_check:
    file_row=file_row.strip().split(',')
    file_lines.append(file_row)
for file_line in file_lines:
    color_lut[str(file_line[0])]=[float(file_line[1]),float(file_line[2]),float(file_line[3]),str(file_line[4])]

# Build transition tables used in Next routine

#       Transition Type Enumerated:
#            FadeTransition = 1
#            BlurTransition = 2
#            PixelTransition = 3
#            RippleTransition = 4
#            RotateTransition = 5
#            SlideTransition = 6
#            Toggle Rotate Top/Bottom = 91 (uses transitions_rotatetb list below)
#            Toggle Rotate Left/Right = 92 (uses transitions_slide list below)
#            Toggle Slide Top/Bottom = 93 (uses transitions_slidetb list below)
#            Toggle Slide Left/Right = 94 (uses transitions_slidelr list below)
#            Random Rotate = 95 (uses transitions_rotate list below)
#            Random Slide = 96 (uses transitions_slide list below)
#            Random Fade = 97 (uses transitions_fade list below)
#            Random Swipe = 98 (uses transitions_swipe list below)
#            Random All = 99 (uses transitions_all list below)

#       List below requires Type,Duration,Direction between commas and single quote.
#       This list is used by NEXT routine below to fix an object problem when using  
#       screen manager transition, that crashes Android APK on Frame when using objects.
        
def build_array(filename,array_var):
    file_lines=[]
    temp_text = open(ss_data_path + 'transitions/' + filename,'r')
    tmp_check = temp_text.readlines()
    for file_row in tmp_check:
        file_row_str = str(file_row)
        file_row_str = file_row_str.replace('\n','')
        array_var.append(file_row_str)

transitions_all=[]
transitions_swipe=[]
transitions_fade=[]
transitions_slide=[]
transitions_rotate=[]
transitions_slidelr=[]
transitions_slidetb=[]
transitions_rotatelr=[]
transitions_rotatetb=[]
build_array('transitions_all.dat', transitions_all)
build_array('transitions_swipe.dat', transitions_swipe)
build_array('transitions_fade.dat', transitions_fade)
build_array('transitions_slide.dat', transitions_slide)
build_array('transitions_rotate.dat', transitions_rotate)
build_array('transitions_slidelr.dat', transitions_slidelr)
build_array('transitions_slidetb.dat', transitions_slidetb)
build_array('transitions_rotatelr.dat', transitions_rotatelr)
build_array('transitions_rotatetb.dat', transitions_rotatetb)

# Create rest of lists used in SlideShow

font_size_list = {}
font_size_list['small'] = 25   
font_size_list['medium'] = 35   
font_size_list['large'] = 45   
font_size_list['exlarge'] = 55   

brightness_list = {}
brightness_list['LowDim'] = 50   
brightness_list['MidDim'] = 100 
brightness_list['HighDim'] = 150   
brightness_list['Medium'] = 175   
brightness_list['Full'] = 200   
brightness_list['Bright'] = 255   

brightness_list['0%'] = 40   
brightness_list['20%'] = 90 
brightness_list['40%'] = 130   
brightness_list['60%'] = 170   
brightness_list['80%'] = 210   
brightness_list['100%'] = 255   

transition_displays={'Fade':1,'Blur':2,'Pixel':3,'Ripple':4,'Rotate':5,'Slide':6,'Rotate top/bottom':91,'Rotate left/right':92,'Slide top/bottom':93,'Slide left/right':94,'Random Rotate':95,'Random Slide':96,'Random Fade':97,'Random Swipe':98,'Random All':99}
transition_display_names={1:'Fade',2:'Blur',3:'Pixel',4:'Ripple',5:'Rotate',6:'Slide',91:'Rotate top/bottom',92:'Rotate left/right',93:'Slide top/bottom',94:'Slide left/right',95:'Random Rotate',96:'Random Slide',97:'Random Fade',98:'Random Swipe',99:'Random All'}

# The range of SS-FrameConfiguration spreadsheet
RANGE_NAME = 'Frames!A1:ZZ100'
# ----------------------------------------------
class ssFrame:
# ----------------------------------------------
    def __init__(self):   
        self.local_pix = ss_path + 'pix/'
        self.log_path = ss_path + 'logs/'
        self.credential_dir = ss_data_path + 'credentials/'
        self.local_ringtones = ss_data_path + 'ringtones/'
        self.fonts_dir = ss_data_path + 'fonts/'
        self.config_path = ss_path + 'slideshow.cfg'

        self.app_paused = False
        self.frame_sleeping = False
        self.frame_awoken = False 

        self.sleep_enabled = False
        self.random_enabled = False
        self.random_list = []
        self.debug_enabled = False
        
        self.start_sleep_time = ''
        self.start_sleep_datetime = '2020-01-01 00:00:00'
        self.end_sleep_time = ''
        self.end_sleep_datetime = '2020-01-01 00:00:00'
        self.sleep_mode = ''
        self.start_astro_time = ''
        self.end_astro_time = ''
        self.dst_enabled = False        # Enable Daylight Savings Time 
        self.march_dst = None           # Second Sunday in March starts Daylight Savings Time 
        self.november_dst = None        # First Sunday in November ends DST

        self.sync_interval = 60
        self.sync_number = 0            # Variable for future use, placeholder for now.
        self.sync_counter = 0
        self.sync_start_time = None
        self.sleep_seconds = 0         # Value in seconds to sleep until to wake up - calculated in calc_sleep routine.
        self.slideshow_index = 0
        self.slide_count = 0
        self.slide_duration = 7
        self.slide_scale_timing = 0.0
        self.transition_duration = 1.5
        self.transition_type = {}
        self.transition_direction = 'up'
        self.transition_enabled = True
        self.current_brightness = 0
        self.current_volume = 0
        self.test_connect_url = 'https://google.com'
        self.gc_interval = 900          # HARDCODED interval in secs for 15 minutes to trigger python garbage collection & to check weather
        self.display_width = 0
        self.display_height = 0
        self.swipe_enabled = True
        
        self.touch_center = []
        self.slide_left = []
        self.slide_right = []

# Define Captions variables
        
        self.captions_height = 0
        self.captions_width = 0
        self.captions_bottom_y = 0        
        self.caption1_content = '' 
        self.caption2_content = '' 
        self.caption1_label = ''
        self.caption2_label = ''
        self.captions_fontsize = 0
        
        self.captions_enabled = False
        self.captions_changed = False # flag for next to turn off captions when changed by frame-update
        self.captions_displayed = False

        self.captions_fontname = ''   
        self.captions_font = ''
        self.captions_font_file = ''
        self.captions_location = 'bottom'   # Options:  Top/Bottom
        self.captions_opacity = 0.0
        self.captions_color_fg = {}   # Hex RGB
        self.captions_color_bg = {}
        self.captions_fontpixel = 35  # Internal value for setting caption font pixel height
        self.captions_clut_fg = {}    # Internal values for setting caption fg/bg color
        self.captions_clut_bg = {}
        
        self.digitalclock_height = 0
        self.digitalclock_width = 0
        self.digitalclock_bottom_y = 0        
        self.digitalclock1_content = ''
        self.digitalclock2_content = ''
        self.digitalclock1_label = ''
        self.digitalclock2_label = ''
        self.digitalclock1 = ''
        self.digitalclock2 = ''
        self.digitalclock_fontsize = 0

        self.clock_sync = '00:00:00'

        self.digitalclock_fontname = ''
        self.digitalclock_font = ''
        self.digitalclock_font_file = ''
        self.digitalclock_location = 'bottom'   # Options:  Top/Bottom/Above Caption/Below Caption
        self.digitalclock_opacity = 0.0
        self.digitalclock_color_bg = {}
        self.digitalclock_fontpixel = 35  # Internal value for setting caption font pixel height
        self.digitalclock_clut_bg = {}

        self.digitalclock_changed = False
        self.digitalclock_displayed = False
        self.digitalclock_enabled = False
        
        self.digitalclock_day_fontcolor = 'white'
        self.digitalclock_date_fontcolor = 'yellow'
        self.digitalclock_time_fontcolor = 'white'

        self.banner_locations = ''      # Where on the screen the clock and captions appear, only top/bottom options, or disabled.

        self.weather_location = ''      # Spreadsheet location where weather is used by Astral to get coordinates and full info.
        self.weather_location_full = ''      # Astral full location where weather is displayed on screen.
        self.weather_timezone = ''
        self.lat_lon = ''
        self.OWM_id = ''                # OpenWeatherMap App ID.

        self.outside_info_font_file = ''
        self.outside_info_location = 'bottom'   # Options:  Top/Bottom
        self.outside_info_fontcolor = 'white'
        self.outside_info_opacity = 0.0
        self.outside_info_color_bg = {}
        self.outside_info_fontsize = ''
        self.outside_info_fontpixel = 35  # Internal value for setting caption font pixel height
        self.outside_info_clut_bg = {}

        self.outside_info_changed = False
        self.outside_info_displayed = False
        self.outside_info_enabled = False

        self.outside_temp1_content = ''
        self.outside_temp2_content = ''
        self.outside_temp1_label = ''
        self.outside_temp2_label = ''
        self.outside_humidity1_content = ''
        self.outside_humidity2_content = ''
        self.outside_humidity1_label = ''
        self.outside_humidity2_label = ''

        self.outside_info_bottom_y = 0
        self.outside_info_width = 0
        self.outside_info_height = 0
        self.outside_info_bottom_y = 0
        self.outside_humidity_x = 0
        self.outside_humidity_y = 0

# Define Google API variables and Master-Pics tests variables

        self.spreadsheetId = ''
        self.slideshow_album = 'Unknown'
        self.spreadsheet_mod = ''
        self.spreadsheetId = ''
        self.album_id = ''
        self.album_mod = ''
        self.photo_mod = ''
        self.downloading = False    # Used by Check_server to tell NEXT routine to skip
        self.nexting = False        # Used by NEXT routine to tell Check_server to skip
        self.no_internet = False
        self.newpix_enabled = True
        self.newpix_ringtone = 'sirius.ogg'
        self.pause_duration = 90
        self.awake_time_pause = 15      # Amount of time in seconds to stay awake after gone to sleep.
        self.display_center = (0,0)
        self.scale_start = 1.0
        self.scale_end = 1.0

ss = ssFrame()  # Create an instance of app variables

ss.clock_sync = datetime.strptime(str(datetime.now())[11:16], '%H:%M')

# Setup to play audio when enabled.
ringtone_list={}
ringtone_list=os.listdir(ss.local_ringtones)

if not os.path.exists(ss.local_pix):
    os.makedirs(ss.local_pix)

if not os.path.exists(ss.log_path):
    os.makedirs(ss.log_path)

ss_pictures = []  # clear the lists
ss_captions = []
del ss_pictures[:]
del ss_captions[:]

# Setup Frame Initially from config file

config = configparser.ConfigParser()

try:
    config.read(ss.config_path)
except:   # No config file? Exit SlideShow app...
    err = sys.exc_info()[:2]
    logger.critical(str(err) + '---> INIT FATAL 3 - slideshow.cfg missing error: @ ' + str(datetime.now())[0:19])
    sys.exit()

ss_utils.config_load(ss, config)

ss.march_dst = datetime.strptime(str(ss.march_dst)[:10], '%Y-%m-%d')
ss.november_dst = datetime.strptime(str(ss.november_dst)[:10], '%Y-%m-%d')

# Setup Astral for solar start and end times.

astral_server = Astral()
astral_server.solar_depression = 'civil'
location = astral_server[ss.weather_location]
tmp_str = str(location).split(', ')
ss.lat_lon = tmp_str[2] + '&' + tmp_str[3]

logger.info('initiation: SlideShow Album: <[' + ss.slideshow_album + ']>')

if 'clock/' in ss.banner_locations:
    ss.digitalclock_location = 'top'
    ss.captions_location = 'bottom'
else:
    ss.digitalclock_location = 'bottom'
    ss.captions_location = 'top'

if ss.sync_interval == 0: logger.info('initiation: Detached from Google due to ss.sync_interval = 0. Running in manual/local mode only.')
logger.info('initiation: Frame Debug: ' + str(ss.debug_enabled) + ' @ ' + str(datetime.now())[0:19])

# Google connection/authentication configuration

pickle_path_drive = ss.credential_dir + 'token-drive.pickle'
pickle_path_sheets = ss.credential_dir + 'token-sheets.pickle'
pickle_path_photos = ss.credential_dir + 'token-photos.pickle'

credentials_path_drive = ss.credential_dir + 'credentials-drive.json'
credentials_path_sheets = ss.credential_dir + 'credentials-sheets.json'
credentials_path_photos = ss.credential_dir + 'credentials-photos.json'

SCOPES_drive = ['https://www.googleapis.com/auth/drive.metadata.readonly']
SCOPES_sheets = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SCOPES_photos = ['https://www.googleapis.com/auth/photoslibrary.readonly']

creds_drive = None
creds_sheets = None
creds_photos = None

# end of initialization code
############################
# Functions below
# ----------------------------------------------
def test_connect(timeout):
# ----------------------------------------------
    try:
        temp_proc = requests.get(ss.test_connect_url, timeout=timeout)
        ss.no_internet = False
        return True
    except Exception as err:
        if ss.debug_enabled: logger.error('test_connect Connection Error = ' + str(err) + ', test_connect_url=' + str(ss.test_connect_url) + ', timeout=' + str(timeout))   # as err: pass
        ss.no_internet = True
        pass
    return False

# ----------------------------------------------
def set_brightness(brightness):
# ----------------------------------------------
    if platform == 'android':
        temp_proc = subprocess.Popen(args='su root settings put system screen_brightness ' + str(brightness), stdout = subprocess.PIPE, shell = True)
        complete_val, err = temp_proc.communicate()
        if ss.debug_enabled: logger.warning('set_brightness: Brightness set to ' + str(brightness) + ', complete_val=' + str(err) + ', err=' + str(err))

# ----------------------------------------------
def play_newpix():
# ----------------------------------------------
    mixer.music.load(ss.local_ringtones + ss.newpix_ringtone)
    mixer.music.play()
    while mixer.music.get_busy():
        time.sleep(.1)
    if ss.debug_enabled: logger.warning('play_newpix: On ' + platform + ' platform played ' + str(ss.newpix_ringtone) + '.')

# ----------------------------------------------
def blank_screen():
# ----------------------------------------------
    if platform == 'linux':
        temp_proc = subprocess.Popen(args=['vcgencmd display_power 0'], stdout=subprocess.PIPE, shell=True)
    else:
        temp_proc = subprocess.Popen(args='su root am broadcast -a com.android.lcd_bl_off', stdout = subprocess.PIPE, shell = True)
    complete_val, err = temp_proc.communicate()

# ----------------------------------------------
def wake_screen():
# ----------------------------------------------
    if platform == 'linux':
        temp_proc = subprocess.Popen(args=['vcgencmd display_power 1'], stdout=subprocess.PIPE, shell=True)
    else:
        temp_proc = subprocess.Popen(args='su root am broadcast -a com.android.lcd_bl_on', stdout = subprocess.PIPE, shell = True)
    complete_val, err = temp_proc.communicate()

# ----------------------------------------------
def update_gc_mem():
# ----------------------------------------------
    gc.collect()   # Garbage Collect
    temp_proc = subprocess.Popen(args='free -m | grep Mem:', stdout=subprocess.PIPE, shell=True)
    complete_val, err = temp_proc.communicate()
    cropped = str(complete_val).split()
    logger.info('------> Collecting Garbage - Total Memory Free: ' + cropped[3] + ', Used: ' + cropped[2] + ' @ ' + str(datetime.now())[0:19])

# ----------------------------------------------
def config_dst():
# ----------------------------------------------
# Make sure DST values set for current year. This is important should SlideShow run for many years.
##  NOTE: I have no idea why these values need to be set back to date types. Was set during intiation code.
    ss.march_dst = datetime.strptime(str(ss.march_dst)[:10], '%Y-%m-%d')
    ss.november_dst = datetime.strptime(str(ss.november_dst)[:10], '%Y-%m-%d')

    if datetime.now().year != ss.march_dst.year:
        start_sundays = calendar.Calendar(firstweekday=calendar.SUNDAY)
        if ss.debug_enabled: logger.warning('config_dst: DST CURRENT Days outdated for march_dst and november_dst: ' + str(ss.march_dst)[:10] + ', ' + str(ss.november_dst)[:10])

        monthcal = start_sundays.monthdatescalendar(datetime.now().year,3)
        ss.march_dst = [day for week in monthcal for day in week if day.weekday() == calendar.SUNDAY and day.month == 3][1]

        monthcal = start_sundays.monthdatescalendar(datetime.now().year,11)
        ss.november_dst = [day for week in monthcal for day in week if day.weekday() == calendar.SUNDAY and day.month == 11][0]
        if ss.debug_enabled: logger.warning('config_dst: DST Years updated to march_dst and november_dst: ' + str(ss.march_dst) + ', ' + str(ss.november_dst))

        try:
            config.read(ss.config_path)
            config.set('Frame Parameters', 'march_dst', str(ss.march_dst)[:10])
            config.set('Frame Parameters', 'november_dst', str(ss.november_dst)[:10])
            with open(ss.config_path, 'w') as configfile:
                config.write(configfile)
        except Exception as err:   # No config file? Exit SlideShow app...
            logger.error('config_dst: DST configfile write Exception '+ str(err))
            pass

# ----------------------------------------------
def calc_dst():
# ----------------------------------------------
    # It's time to apply Daylight Savings Time seconds to sleep_seconds.

    if str(ss.end_sleep_datetime)[:10] == str(ss.march_dst)[:10]:
        if ss.sleep_seconds > 3600:
            if ss.debug_enabled: logger.warning('calc_dst: March DST Date: ' + str(ss.march_dst)[:10] + ', change to sleep_seconds minus 3600 (1 hour). From ' + str(ss.sleep_seconds) + ' to : ' + str(ss.sleep_seconds - 3600))
            ss.sleep_seconds = ss.sleep_seconds - 3600
        else:
            if ss.debug_enabled: logger.warning('calc_dst: March DST Date, CANNOT change sleep_seconds, too low to subtract 3600 (1 hour). From seconds remaining: ' + str(ss.sleep_seconds))
    elif str(ss.end_sleep_datetime)[:10] == str(ss.november_dst)[:10]:
        if ss.debug_enabled: logger.warning('calc_dst: November DST Date: ' + str(ss.november_dst)[:10] + ', change to sleep_seconds plus 3600 (1 hour). From ' + str(ss.sleep_seconds) + ' to : ' + str(ss.sleep_seconds + 3600))
        ss.sleep_seconds = ss.sleep_seconds + 3600

# ----------------------------------------------
def format_ip(args):
# ----------------------------------------------
	temp_proc = subprocess.Popen(args=[args], stdout=subprocess.PIPE, shell=True)
	complete_val, err = temp_proc.communicate()
	ip_str = str(complete_val).replace('b','')
	start_str = ip_str.find('inet')
	start_str += 5
	end_str = ip_str.find('/',start_str)
	ip_list = ip_str[start_str:end_str]
	start_str = ip_str.find('inet',end_str)
	while start_str > 0:
		start_str += 5
		end_str = ip_str.find('/',start_str)
		ip_list = ip_list + ', ' + ip_str[start_str:end_str]
		start_str = ip_str.find('inet',end_str)
	return ip_list

# ----------------------------------------------
def update_captions():
# ----------------------------------------------
    global this_app, current_page, screenManager, page1, page2

    if this_app.screenManager.current == 'page2':
        this_app.page1.remove_widget(ss.caption1_content)
        ss.caption1_content.remove_widget(ss.caption1_label)
        current_caption = html.unescape(ss_captions[ss.slideshow_index])
        current_caption = ss_utils.caption_markup(current_caption, ss.captions_font, ss.fonts_dir)
        ss.caption1_label = Label(text= '[color=#' + ss.captions_clut_fg[3] + ']' + current_caption + '[/color]', font_name=ss.captions_font_file, markup=True, font_size=ss.captions_fontpixel, valign='bottom')
        if len(ss_captions[ss.slideshow_index]) != 0:
            ss.caption1_content.add_widget(ss.caption1_label)
            this_app.page1.add_widget(ss.caption1_content)
    else:
        this_app.page2.remove_widget(ss.caption2_content)
        ss.caption2_content.remove_widget(ss.caption2_label)
        current_caption = html.unescape(ss_captions[ss.slideshow_index])
        current_caption = ss_utils.caption_markup(current_caption, ss.captions_font, ss.fonts_dir)
        ss.caption2_label = Label(text= '[color=#' + ss.captions_clut_fg[3] + ']' + current_caption + '[/color]', font_name=ss.captions_font_file, markup=True, font_size=ss.captions_fontpixel, valign='bottom')
        if len(ss_captions[ss.slideshow_index]) != 0:
            ss.caption2_content.add_widget(ss.caption2_label)
            this_app.page2.add_widget(ss.caption2_content)

# ----------------------------------------------
def get_creds(pickle_path, credentials_path, SCOPES):
# ----------------------------------------------
# The file token.pickle stores the user's access and refresh tokens, and is created
# automatically when the authorization flow completes for the first time.
    creds = None
    if os.path.exists(pickle_path):
        with open(pickle_path, 'rb') as token:
            creds = pickle.load(token)
# If there are no valid credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                logger.error('get_creds: Connecting to Service Refresh Error @ ' + str(datetime.now())[0:19])
                err = sys.exc_info()[:2]
                logger.error('*********** error: ' + str(err))
                creds = -1
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server()
            except:
                logger.error('get_creds: Connecting to Service Flow Error @ ' + str(datetime.now())[0:19])
                err = sys.exc_info()[:2]
                logger.error('*********** error: ' + str(err))
                creds = -1
# Save the credentials for the next run
        with open(pickle_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds

# ----------------------------------------------
def read_from_pickle(path):
# ----------------------------------------------
    with open(path, 'rb') as file:
        try:
            while True:
                yield pickle.load(file)

        except EOFError:
            pass
# ----------------------------------------------
def sync_frame_vars(frame_feed):
# ----------------------------------------------
    global ss_pictures, ss_captions

    tmp_duration = frame_feed['slide_duration']
    if ' ' in tmp_duration:                     ######## THIS CAN BE REMOVED AFTER ALL SPREADSHEETS UPDATED, and tested.
        tmp_duration = tmp_duration.split(' ')
        if 'second' in tmp_duration[1]:
            ss.slide_duration = int(tmp_duration[0])
        if 'minute' in tmp_duration[1]:
            ss.slide_duration = int(int(tmp_duration[0]) * 60)
        if 'hour' in tmp_duration[1]:
            ss.slide_duration = int(int(tmp_duration[0]) * 3600)
    else:
        ss.slide_duration = int(tmp_duration)
    ss.scale_start = float(frame_feed['scale_start'].strip('%')) / 100
    if ss.scale_start == 0:ss.scale_start=.01
    ss.scale_end = float(frame_feed['scale_end'].strip('%')) / 100
    if ss.scale_end == 0:ss.scale_end=.01
    ss.slide_scale_timing = float(frame_feed['slide_scale_timing'])
    if ss.slide_scale_timing == int(0): # when duration is zero, set start and end to highest value
        if ss.scale_end > ss.scale_start: ss.scale_start = ss.scale_end
        else: ss.scale_end = ss.scale_start

    if frame_feed['sleep_enabled'] == 'FALSE' or frame_feed['sleep_enabled'] == 'NO': ss.sleep_enabled = False
    else: ss.sleep_enabled = True
    ss.start_sleep_time = frame_feed['start_sleep_time'] + ':00'
    ss.end_sleep_time = frame_feed['end_sleep_time'] + ':00'
    if ss.start_sleep_time == ss.end_sleep_time: # if user inputs same start/end time,
        ss.sleep_enabled = False                       # disable sleep mode
    ss.sleep_mode = frame_feed['sleep_mode'].lower()
    ss.start_astro_time = frame_feed['start_astro_time'].lower()
    ss.end_astro_time = frame_feed['end_astro_time'].lower()
    ss.weather_location = frame_feed['weather_location'].lower()
    location = astral_server[ss.weather_location]
    tmp_str = str(location).split(', ')
    ss.weather_location_full = tmp_str[0]
    ss.lat_lon = tmp_str[2] + '&' + tmp_str[3]
    ss.weather_timezone = str(location.timezone)
    ss.OWM_id = frame_feed['OWM_id']

    temp_interval = frame_feed['sync_interval']     # Handle string like '960 = 16 hours'
    temp_interval = int(temp_interval.split('=')[0])*60
    if ss.sync_interval != temp_interval:
        ss.sync_interval = temp_interval
        if ss.sync_interval != 0 and ss.sync_interval < 300: ss.sync_interval = 300
        Clock.unschedule(SS_Loader.check_server)                        # Turn off any clock scheduled
        Clock.schedule_once(SS_Loader.check_server, ss.sync_interval)

    if frame_feed['transition_enabled'] == 'FALSE' or frame_feed['transition_enabled'] == 'NO': ss.transition_enabled = False
    else: ss.transition_enabled = True
    ss.transition_duration = float(frame_feed['transition_duration'])
    if ss.transition_duration < 1: ss.transition_duration = 1

    # Need to protect from unsupported transition durations:
    if ss.transition_duration > float(ss.slide_duration - 2):   
        ss.transition_duration = float(ss.slide_duration - 2)
    ss.transition_type = frame_feed['transition_type']      # Convert to number
    if ss.transition_type not in transition_displays: ss.transition_type = 1      # Default to Fade transition if invalid feed
    else: ss.transition_type = transition_displays[ss.transition_type]

    if frame_feed['pause_duration'] == 'Never': ss.pause_duration = 0
    else: ss.pause_duration = int(frame_feed['pause_duration'])
    ss.transition_direction = frame_feed['transition_direction']
    if ss.transition_direction == 'Top': ss.transition_direction = 'down'
    elif ss.transition_direction == 'Bottom': ss.transition_direction = 'up'
    elif ss.transition_direction == 'Right': ss.transition_direction = 'right'
    elif ss.transition_direction == 'Left': ss.transition_direction = 'left'
    else: ss.transition_direction = 'left'    # This might need work to determine right default.
    if frame_feed['debug_enabled'] == 'FALSE' or frame_feed['debug_enabled'] == 'NO': ss.debug_enabled = False
    else: ss.debug_enabled = True
    if frame_feed['dst_enabled'] == 'NO': ss.dst_enabled = False
    else: ss.dst_enabled = True
    ss.newpix_ringtone = frame_feed['newpix_ringtone'] + '.ogg'
    if ss.newpix_ringtone not in ringtone_list:
        ss.newpix_ringtone = 'sirius.ogg'     # Default to sirius.ogg if invalid feed

#    ss.banner_locations = frame_feed['banner_locations'].lower()
    if ss.banner_locations != frame_feed['banner_locations'].lower():
        ss.banner_locations = frame_feed['banner_locations'].lower()
        ss.digitalclock_changed = True              # Set indicator for NEXT processing to update digitalclock.
        ss.captions_changed = True                  # Set indicator for NEXT processing to update captions.

# Process captions FEED info
    if frame_feed['captions_enabled'] == 'YES' and not ss.captions_enabled:
        ss.captions_enabled = True
        ss.captions_changed = True                  # Set indicator for NEXT processing to update captions.
    elif frame_feed['captions_enabled'] == 'NO' and ss.captions_enabled: 
        ss.captions_enabled = False
        ss.captions_changed = True                  # Set indicator for NEXT processing to update captions.
    ss.captions_fontsize = frame_feed['captions_fontsize'].lower()  # .lower() is to make all UI values lower case.
    ss.captions_fontname, ss.captions_font = ss_utils.confirm_fontname(frame_feed['captions_fontname'])

    if 'captions/' in ss.banner_locations: ss.captions_location = 'top'
    else: ss.captions_location = 'bottom'
    ss.captions_color_fg = frame_feed['captions_color_fg'].lower()
    ss.captions_color_bg = frame_feed['captions_color_bg'].lower()
    ss.captions_opacity = float(frame_feed['captions_opacity'].strip('%'))/100
    if ss.captions_opacity > 1 or ss.captions_opacity < 0.00: ss.captions_opacity = 1.0

# Validate table entries from feed
    if ss.captions_fontsize not in font_size_list: ss.captions_fontsize = 'medium'
    if ss.captions_color_fg not in color_lut: ss.captions_color_fg = 'white'
    if ss.captions_color_bg not in color_lut: ss.captions_color_bg = 'black'

# Process digital clock FEED info
    if frame_feed['digitalclock_enabled'] == 'YES' and not ss.digitalclock_enabled:
        ss.digitalclock_enabled = True
        ss.digitalclock_changed = True                  # Set indicator for NEXT processing to update digitalclock.
    elif frame_feed['digitalclock_enabled'] == 'NO' and ss.digitalclock_enabled: 
        ss.digitalclock_enabled = False
        ss.digitalclock_changed = True

    ss.digitalclock_fontsize = frame_feed['digitalclock_fontsize'].lower()
    ss.digitalclock_fontname, ss.digitalclock_font = ss_utils.confirm_fontname(frame_feed['digitalclock_fontname']) # This is overkill but reuses code to get valid fontname.

    if 'clock/' in ss.banner_locations: ss.digitalclock_location = 'top'
    else: ss.digitalclock_location = 'bottom'
    ss.digitalclock_color_bg = frame_feed['digitalclock_color_bg'].lower()
    ss.digitalclock_day_fontcolor = frame_feed['digitalclock_day_fontcolor'].lower()
    ss.digitalclock_date_fontcolor = frame_feed['digitalclock_date_fontcolor'].lower()
    ss.digitalclock_time_fontcolor = frame_feed['digitalclock_time_fontcolor'].lower()
    ss.digitalclock_opacity = float(frame_feed['digitalclock_opacity'].replace('%',''))/100 
    if ss.digitalclock_opacity > 1 or ss.digitalclock_opacity < 0.00: ss.digitalclock_opacity = 1

# Validate table entries from feed and set bogus to defaults...
    if ss.digitalclock_fontsize not in font_size_list: ss.digitalclock_fontsize = 'medium'
    if ss.digitalclock_color_bg not in color_lut: ss.digitalclock_color_bg = 'black'
    if ss.digitalclock_day_fontcolor not in color_lut: ss.digitalclock_day_fontcolor = 'white'
    if ss.digitalclock_date_fontcolor not in color_lut: ss.digitalclock_date_fontcolor = 'white'
    if ss.digitalclock_time_fontcolor not in color_lut: ss.digitalclock_time_fontcolor = 'white'

# Load outside weather information parameters
    if frame_feed['outside_info_enabled'] == 'YES' and not ss.outside_info_enabled:
        ss.outside_info_enabled = True
        ss.outside_info_changed = True                  # Set indicator for NEXT processing to update digitalclock.
    elif frame_feed['outside_info_enabled'] == 'NO' and ss.outside_info_enabled: 
        ss.outside_info_enabled = False
        ss.outside_info_changed = True

    else: ss.outside_info_changed = False
    if ss.outside_info_location != frame_feed['outside_info_location'].lower():
        ss.outside_info_location = frame_feed['outside_info_location'].lower()
        ss.outside_info_changed = True
    if ss.outside_info_color_bg != frame_feed['outside_info_color_bg'].lower():
        ss.outside_info_color_bg = frame_feed['outside_info_color_bg'].lower()
        ss.outside_info_changed = True
    if ss.outside_info_fontcolor != frame_feed['outside_info_fontcolor'].lower():
        ss.outside_info_fontcolor = frame_feed['outside_info_fontcolor'].lower()
        ss.outside_info_changed = True
    if str(ss.outside_info_opacity) != str(float(frame_feed['outside_info_opacity'].replace('%',''))/100):
        ss.outside_info_opacity = float(frame_feed['outside_info_opacity'].replace('%',''))/100 
        ss.outside_info_changed = True
    if ss.outside_info_fontsize != frame_feed['outside_info_fontsize'].lower():
        ss.outside_info_fontsize = frame_feed['outside_info_fontsize'].lower()
        ss.outside_info_changed = True

# Validate table entries from feed and set bogus to defaults...
    if ss.outside_info_opacity > 1 or ss.outside_info_opacity < 0.00: ss.outside_info_opacity = 1
    if ss.outside_info_fontsize not in font_size_list: ss.outside_info_fontsize = 'medium'
    if ss.outside_info_color_bg not in color_lut: ss.outside_info_color_bg = 'black'
    if ss.outside_info_fontcolor not in color_lut: ss.outside_info_fontcolor = 'white'

# Random order slides here for frame_update changed after loading config file.
    if frame_feed['slideshow_random'] == 'FALSE' or frame_feed['slideshow_random'] == 'NO': slideshow_random = False
    else: slideshow_random = True
    if ss.random_enabled != slideshow_random:
        ss.random_enabled = slideshow_random
        ss.slide_count = config.getint('Slideshow Order', 'slide_count')
        ss_pictures = []    # clear the lists
        ss_captions = []
        del ss_pictures[:]
        del ss_captions[:]
        i = 0
        while (i < ss.slide_count):
            file = config.get('Slideshow Order', 'slide[' + str(i) + ']')
            ss_pictures.append(ss.local_pix + file)
            current_caption = config.get('Captions List', 'caption[' + str(i) + ']')
            ss_captions.append(current_caption)
            i += 1
        if ss.slide_count == 1: # put dup in for page 2 when only one picture in album
            ss_pictures.append(ss.local_pix + file)
            ss_captions.append(current_caption)
        if ss.random_enabled and ss.slide_count > 2:  # setup initial sequence to randomize
            ss.random_list = [i for i in range(ss.slide_count)]
            randomize_slides()
        
    if frame_feed['brightness'] not in brightness_list: tmp_brightness = 1 
    else: tmp_brightness = brightness_list[frame_feed['brightness']]
    if int(ss.current_brightness) != tmp_brightness:                  # Handle brightness changed
        ss.current_brightness = tmp_brightness
    set_brightness(ss.current_brightness)

    if frame_feed['volume'] == 'Mute': ss.current_volume = float(0)   # Convert Mute
    else: ss.current_volume = float(int(frame_feed['volume'].strip('%')) / 100)
    mixer.music.set_volume(ss.current_volume)
    if ss.debug_enabled: logger.warning('sync_frame_vars: Frame feed processed @ ' + str(datetime.now())[0:19])
    return True
# end of sync_frame_vars

# ----------------------------------------------
def sync_server_pix(contents):
# ----------------------------------------------
# Get NEW picture feed from server.
# Get the list setup of local photos to pull new pictures from server while 
# building the feed_picture array.
# NOTE: the local store of pictures is the slave; we delete and add pictures based
# on what is in the server picture feed.
    global ss_pictures, ss_captions

    if ss.debug_enabled: logger.warning('sync_server_pix: Pictures loading from server @ ' + str(datetime.now())[0:19])

    # Clear the config file section of all Slideshow Order entries and recreate it.
    # This sucks in the worse way because Picasa API provided a modified date that prevented 
    # downloading every sync cycle. This greatly increases traffic.
    feed_picture_files = []
    feed_picture_captions = []
    del feed_picture_files[:]  
    del feed_picture_captions[:]
    config.remove_section('Slideshow Order')
    config.add_section('Slideshow Order')
    config.remove_section('Captions List')
    config.add_section('Captions List')

    local_picture_files = next(os.walk(ss.local_pix))[2]
    slide_counter = 0
    new_pix_ringer = ss.newpix_enabled
        
    for photo in contents:
        pname = photo['filename']
        try: 
            tmp_caption = photo['description']
            tmp_caption = tmp_caption.split('\n')[0]
            tmp_caption = tmp_caption.strip()
        except: 
            tmp_caption = ''
            err = sys.exc_info()[:2]
            if "KeyError('description'" not in str(err):
                if ss.debug_enabled: logger.error('sync_server_pix: photo caption error: ' + str(err) + ' for filename ' + str(pname) + ' @ ' + str(datetime.now())[0:19])
            pass

#   Handle NEW validated picture arrival - play enabled sound & rotate to exif spec.

        if pname not in local_picture_files and pname != '':        # check to see if any of the server pictures 
            try:                                                    # are new and if so, copy them to local folder
                response = requests.get(photo['baseUrl'] + '=w1920-h1080', timeout=10)
            except requests.exceptions.Timeout:
                if ss.debug_enabled: logger.error('sync_server_pix: requests.get(photo[baseUrl] timed out for pname=' + str(pname) + '. Attempting one more time before aborting.')
                pass
                try:
                    response = None
                    response = requests.get(photo['baseUrl'] + '=w1920-h1080', timeout=10)
                except requests.exceptions.Timeout:
                    if ss.debug_enabled: logger.error('sync_server_pix: requests.get(photo[baseUrl] timed out for pname=' + str(pname) + ' a second time, now aborting.')
                    pass
                except Exception as err:
                    if ss.debug_enabled: logger.error('sync_server_pix: requests.get(photo[baseUrl] error: ' + str(err) + ' for pname=' + str(pname))
                    pass
            except Exception as err:
                if ss.debug_enabled: logger.error('sync_server_pix: requests.get(photo[baseUrl] error: ' + str(err) + ' for pname=' + str(pname))
                pass
            pix_type = ''
            if '.jpg' in pname.lower() or '.jpeg' in pname.lower(): pix_type = 'jpg'
            if '.png' in pname.lower(): pix_type = 'png'

            if pix_type != '': 
                feed_picture_files.append(pname)     #add filename to Frame Slideshow list
                feed_picture_captions.append(tmp_caption)  #add caption to Frame Slideshow list 
                file = open(ss.local_pix + '/' + pname , "wb")
                file.write(response.content)
                file.close()
                if ss.newpix_enabled and new_pix_ringer:
                    mixer.music.load(ss.local_ringtones + ss.newpix_ringtone)
                    mixer.music.play()
                    new_pix_ringer = False              # Turn off ringtone generator, just one play
                if ss.debug_enabled: logger.warning('sync_server_pix: NEW photo downloaded: ' + str(pname) + ' @ ' + str(datetime.now())[0:19])
                slide_counter += 1
        else:
            slide_counter += 1      # use this to indicate amount of pictures in SlideShow album
            feed_picture_files.append(pname)     #add filename to Frame Slideshow list
            feed_picture_captions.append(tmp_caption)  #add caption to Frame Slideshow list 

    if ss.debug_enabled: logger.warning('sync_server_pix: ---> RESYNCing <[' + str(ss.slideshow_album) + ']> from Server!! Number of Picture items= ' + str(slide_counter))

    if slide_counter == 1:                    # put dup in for page 2 when only one picture in album
        feed_picture_files.append(pname)
        feed_picture_captions.append(tmp_caption)  #add caption to Frame Slideshow list 
        slide_counter = 2
    
    if slide_counter == 0:                    # handle NO pictures in album
        logger.error('sync_server_pix: NO Slideshow pix in FEED.')
        copy(ss_path + 'data/pix/Slide-nopix.jpg',ss.local_pix)
        feed_picture_files.append('Slide-nopix.jpg')    # Load the slide for screenmanager
        feed_picture_files.append('Slide-nopix.jpg')
        feed_picture_captions.append('SlideShow Album Missing Pictures')
        feed_picture_captions.append('SlideShow Album Missing Pictures')
        slide_counter = 2
        ss.captions_enabled = True
    ss.slide_count = slide_counter
    ss.album_mod = str(datetime.now())[:19]
    ss.photo_mod = str(datetime.now())[:19]
    config.set('Slideshow Order', 'slide_count', str(slide_counter))

# This section builds the SlideShow app playlist and pictures info for display, such as captions

    if ss.debug_enabled: logger.warning('sync_server_pix: Building SlideShow app playlist')
    
    ss_pictures = []    # clear the lists
    ss_captions = []
    mp_updated = []
    del ss_pictures[:]
    del ss_captions[:]
    del mp_updated[:]
    
    tmp_index = 0
    for file in feed_picture_files:
        ss_pictures.append(ss.local_pix + file)
        ss_captions.append(feed_picture_captions[tmp_index])
        config.set('Slideshow Order', 'slide[' + str(tmp_index) + ']', str(file))
        config.set('Captions List', 'caption[' + str(tmp_index) + ']', str(feed_picture_captions[tmp_index]))
        if ss.debug_enabled:
            logger.warning('Slideshow Order: slide[' + str(tmp_index) + ']' + str(file))
            logger.warning('Captions List: caption[' + str(tmp_index) + ']' + str(feed_picture_captions[tmp_index]))
        tmp_index += 1
    with open(ss.config_path, 'w') as configfile:
        config.write(configfile)
    if ss.random_enabled and slide_counter > 2:
        ss.random_list = [i for i in range(slide_counter)]  # setup initial sequence to randomize
        randomize_slides()

    # Now that the playlist is complete, check to see if any of the local pictures
    # are no longer in the server picture feed and if not, delete the local file

    for file in local_picture_files:
        if file not in feed_picture_files:
            try:
                os.remove(ss.local_pix + file)
                if ss.debug_enabled: logger.warning('sync_server_pix: REMOVING: ' + str(file))
            except: pass
    return True
    
# End of sync_server_pix
# ----------------------------------------------
def randomize_slides(*kwargs):
# ----------------------------------------------
    ss.slide_count = config.getint('Slideshow Order', 'slide_count')
    random.shuffle(ss.random_list)
    if ss.debug_enabled: logger.warning('randomize_slides: random.shuffle(ss.random_list): ' + str(ss.random_list))
    del ss_pictures[:]
    del ss_captions[:]
    i = 0
    while i < ss.slide_count:
        file = config.get('Slideshow Order', 'slide[' + str(ss.random_list[i]) + ']')
        ss_pictures.append(ss.local_pix + file)
        current_caption = config.get('Captions List', 'caption[' + str(ss.random_list[i]) + ']')
        ss_captions.append(current_caption)
        i += 1
    return
    
# ----------------------------------------------
def setup_captions():
# ----------------------------------------------
    ss.captions_clut_fg = color_lut[ss.captions_color_fg]
    ss.captions_clut_bg = color_lut[ss.captions_color_bg]

    ss.captions_font_file = ss.fonts_dir + ss.captions_fontname
    ss.captions_fontpixel = font_size_list[ss.captions_fontsize]
    
    ss.captions_height = ss.captions_fontpixel + 15
    ss.captions_width = ss.display_width
    
    if ss.captions_location == 'bottom':    # Captions location Bottom:
        ss.captions_bottom_y = 0
    else:                                   # Captions location Top:
        ss.captions_bottom_y = ss.display_height-ss.captions_height

# ----------------------------------------------
def setup_digitalclock():
# ----------------------------------------------
    # Clock setup code below
    # Calculate default placement values

    ss.digitalclock_clut_bg = color_lut[ss.digitalclock_color_bg]

    ss.digitalclock_font_file = ss.fonts_dir + ss.digitalclock_fontname
    ss.digitalclock_fontpixel = font_size_list[ss.digitalclock_fontsize]
    
    ss.digitalclock_height = ss.digitalclock_fontpixel + 25
    ss.digitalclock_width = ss.display_width

    if ss.digitalclock_location == 'bottom':    # digitalclock location Bottom:
        ss.digitalclock_bottom_y = 0
    else:                                       # digitalclock location Top:
        ss.digitalclock_bottom_y = ss.display_height-ss.digitalclock_height

# ----------------------------------------------
def setup_outside_info():
# ----------------------------------------------
    # Weather temp (icon hard coded with display size) setup code below

    ss.outside_info_clut_bg = color_lut[ss.outside_info_color_bg]

    ss.outside_info_font_file = ss.fonts_dir + 'Roboto-Regular'
    ss.outside_info_fontpixel = font_size_list[ss.outside_info_fontsize]

# Weather Humidity hard coded for top/bottom
    if ss.outside_info_location == 'top':
        ss.outside_humidity_y = int(ss.display_height - (ss.outside_info_fontpixel * .65))
    else:
        ss.outside_humidity_y = int(ss.outside_info_fontpixel * .75)
    ss.outside_humidity_x = ss.display_width - 50

    ss.outside_info_height = ss.outside_info_fontpixel + 15
    ss.outside_info_width = ss.outside_info_fontpixel * 3

    if ss.outside_info_location == 'bottom': 
        ss.outside_info_top_y = ss.display_height-ss.outside_info_height
        ss.outside_info_bottom_y = 0
    else:                                       # location Top:
        ss.outside_info_top_y = ss.display_height 
        ss.outside_info_bottom_y = ss.display_height - ss.outside_info_height

# ----------------------------------------------
def init_vars_reload():
# ----------------------------------------------
    ss_utils.config_load(ss, config)
    location = astral_server[ss.weather_location]
    tmp_str = str(location).split(', ')
    ss.lat_lon = tmp_str[2] + '&' + tmp_str[3]
    ss.captions_fontname, ss.captions_font = ss_utils.confirm_fontname(ss.captions_fontname)
    if ss.debug_enabled: logger.warning('init_vars_reload: FONTS: captions_fontname, captions_font = ' + str(ss.captions_fontname) + ', ' + str(ss.captions_font))
    setup_system()

# ----------------------------------------------
def init_vars(force_feed):
# ----------------------------------------------
# This routine reads the Master-Pics spreadsheet for the frame display parameters
# and writes them to the local config file. Should the db be inaccessible,
# code loads the configuration file slideshow.cfg for the frame display
# parameters. Routine used during init app build and reloading a new SlideShow Album.

    global gdrv_files
    
    if test_connect(15) == False:
        logger.error('init_vars: No Internet Connection, reloading local config file @ ' + str(datetime.now())[0:19])
        init_vars_reload()
        return False

    if ss.debug_enabled: logger.warning('init_vars: Basic WAN Connection SUCCESSFUL. @ ' + str(datetime.now())[0:19])
    
    # This routine loads all program variables from the server database and used in different places, once connected.

    try:
        creds_drive = get_creds(pickle_path_drive, credentials_path_drive, SCOPES_drive)
        service = build('drive', 'v3', credentials=creds_drive)
        next_PageToken = None
        gdrv_files = service.files().list(q="name='SS-FrameConfiguration'", spaces='drive', fields='nextPageToken, files(id, name, modifiedTime, mimeType)', pageToken=next_PageToken).execute()
    except Exception as err:
        pass
        logger.error('init_vars: *** GOOGLE Drive database access error: [' + str(err) + '] @ ' + str(datetime.now())[0:19] + '.')
        init_vars_reload()
        return False

    if not gdrv_files:
        logger.critical('init_vars: ---> No SS-FrameConfiguration file in Google Drive, reloading local config file @ ' + str(datetime.now())[0:19])
        init_vars_reload()
        return False

    if ss.debug_enabled: logger.warning('init_vars: <[' + ss.slideshow_album + ']> configuration from SS-FrameConfiguration spreadsheet loaded @ ' + str(datetime.now())[0:19])

    frame_id_found = False
    drive_files = gdrv_files.get('files', [])
    for file in drive_files:
        ss.spreadsheetId = file.get('id')
        MODIFIED_TIME = file.get('modifiedTime')

# GOOGLE Spreadsheet starts here - Need to find album in all Drive files:

        try:
            creds_sheets = get_creds(pickle_path_sheets, credentials_path_sheets, SCOPES_sheets)
            service = build('sheets', 'v4', credentials=creds_sheets)
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=ss.spreadsheetId, range=RANGE_NAME).execute()
            values = result.get('values', [])
        except Exception as err:
            pass
            logger.error('init_vars: *** GOOGLE Spreadsheet access error: [' + str(err) + '], reloading local config file @ ' + str(datetime.now())[0:19])
            init_vars_reload()
            return False

        if not values:
            logger.error('init_vars: No data found in GOOGLE Spreadsheet, reloading local config file @ ' + str(datetime.now())[0:19])
            init_vars_reload()
            return False

        for row in values: 
            if row[0] == 'slideshow_album':
                i = 0
                for column in row:
                    if column == ss.slideshow_album:
                        if ss.debug_enabled: logger.warning('init_vars: DOWNLOADING <[' + ss.slideshow_album + ']> Frame configuration with Spreadsheet FEED data @ ' + str(datetime.now())[0:19])
                        frame_feed = {}
                        for new_row in values:
                            frame_feed[str(new_row[0])] = str(new_row[i])
                        frame_id_found = True
                        str_datetime = MODIFIED_TIME[:10] + ' ' + MODIFIED_TIME[11:19]
                        mod_date_object = datetime.strptime(str_datetime, '%Y-%m-%d %H:%M:%S')
                        mod_last_object = datetime.strptime(ss.spreadsheet_mod, '%Y-%m-%d %H:%M:%S')
                        if mod_date_object <= mod_last_object and not force_feed:
                            if ss.debug_enabled: logger.warning('init_vars: Spreadsheet DATA NOT MODIFIED since last Frame update: UTC @ ' + str(mod_date_object)[0:19])
                            init_vars_reload()
                            return False
                        ss.spreadsheet_mod = str(datetime.now())[:19]
                        break
                    i += 1
            if frame_id_found: break

    if not frame_id_found:
        logger.error('init_vars: FRAME ID: ' + str(ss.slideshow_album) + ' is not in Google Spreadsheet, reloading local config file @ ' + str(mod_date_object)[0:19])
        init_vars_reload()
        return False

    if ss.debug_enabled: logger.warning('init_vars: Spreadsheet data downloaded for <[' + str(ss.slideshow_album) + ']>, loading sync_frame_vars @ ' + str(datetime.now())[0:19])
    if sync_frame_vars(frame_feed):   
        setup_system()
        ss.spreadsheet_mod = str(mod_date_object)   # File loaded, save date
        config.set('Frame Parameters', 'spreadsheet_mod', str(ss.spreadsheet_mod))
        with open(ss.config_path, 'w') as configfile:
            config.write(configfile)
    else:     # If feed fails to load, use config file to start. Needs to handle initial Frame startup.
        logger.warning('init_vars: ---> Failure to connect to the database - loading config file: ' + str(datetime.now())[0:19])
        init_vars_reload()
        return False
    return True

#   end of init_vars

# ----------------------------------------------
def sync_pix():
# ----------------------------------------------
# load local config file if there is no internet connectivity

    if test_connect(5) == False:
        logger.error('sync_pix: ---> No Internet Connection - sync_pix - reloading Config File pictures')
        reload_config_pix()
        return False

# Now read the server album/picture feed to update captions or pictures each sync cycle - THANKS GOOGLE!
     
    get_creds(pickle_path_photos, credentials_path_photos, SCOPES_photos)
    for item in read_from_pickle(pickle_path_photos):
        client_id = item.client_id
        client_secret = item.client_secret
        refresh_token = item.refresh_token
    
    cred_photos = GoogleCredentials(None, client_id, client_secret, refresh_token, None, "https://accounts.google.com/o/oauth2/token", None)
    if cred_photos == -1:
        logger.error('sync_pix: Albums credentials Failed @ ' + str(datetime.now())[0:19])
        err = sys.exc_info()[:2]
        logger.error('sync_pix: *********** error: ' + str(err))
        reload_config_pix()
        return cred_photos
        
    http = cred_photos.authorize(httplib2.Http())
    cred_photos.refresh(http)
    access_token = cred_photos.access_token
    params = {'access_token' : "no", 'fields' : "*"}
    params['access_token'] = access_token
    database = 'https://photoslibrary.googleapis.com/v1/albums'
    albums = []
    albumlist = []
    response = ''
    logger.info('sync_pix: - Google Drive starting download album info @ ' + str(datetime.now())[0:19])
    while True:
        try:
            response = requests.get(database, params = params).json()
        except:
            if ss.debug_enabled: logger.error('sync_pix: - Google Drive failed to respond with albums - reloading Config File pictures @ ' + str(datetime.now())[0:19])
            reload_config_pix()
            return False
        if 'albums' in response:
            albums = response['albums']
            for album in albums:
                albumlist.append(album.copy())
        else:
            if ss.debug_enabled: logger.error('sync_pix: - Google Drive failed to find albums - reloading Config File pictures @ ' + str(datetime.now())[0:19])
            reload_config_pix()
            return False
        if 'nextPageToken' in response:
            params["pageToken"] = response["nextPageToken"]
            if ss.debug_enabled: logger.error('sync_pix: nextPageToken in response')
        else:
            break

    search_database = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
    params_search = {"albumId": "id", "pageSize": "100", "access_token" : "none"}
    params_search['access_token'] = params['access_token']
    dicts = {}
    media_pages = {}
    ss.album_id = ''
    for album in albumlist:
        if album['title'] == ss.slideshow_album:
            ss.album_id = album['id']
            config.set('Frame Parameters', 'album_id', str(ss.album_id))  # save album_id for future access
            with open(ss.config_path, 'w') as configfile:
                config.write(configfile)
            params_search['albumId'] = album['id']
            try:
                album_content = requests.post(search_database, params = params_search).json()
            except:
                if ss.debug_enabled: logger.error('sync_pix: - Google Drive failed to respond with nextPageToken albums - reloading Config File pictures @ ' + str(datetime.now())[0:19])
                reload_config_pix()
                return False
            if 'mediaItems' in album_content:
                media_items = album_content['mediaItems']
                media_pages = media_items
                if 'nextPageToken' in album_content:
                    while True:
                        params_search['pageToken'] = album_content['nextPageToken']
                        try:
                            album_content = requests.post(search_database, params = params_search).json()
                        except:
                            if ss.debug_enabled: logger.error('sync_pix: - Google Drive failed to respond with nextPageToken albums - reloading Config File pictures @ ' + str(datetime.now())[0:19])
                            reload_config_pix()
                            return False
                        if 'mediaItems' in album_content:
                            media_items = album_content['mediaItems']
                            media_pages = media_pages + media_items
                        if 'nextPageToken' not in album_content:
                            dicts[album['title']] = media_pages
                            break
                else:
                    dicts[album['title']] = media_pages
    if ss.album_id == '':    # Album not found
        if ss.debug_enabled: logger.error('sync_pix: - Google Drive failure finding album: ' + ss.slideshow_album + ' - reloading Config File pictures @ ' + str(datetime.now())[0:19])
        reload_config_pix()
        return False
    album_with_media = dicts
    if album_with_media[ss.slideshow_album] == '':
        if ss.debug_enabled: logger.error('sync_pix: Pictures feed errored, loading locally @ ' + str(datetime.now())[0:19])
        err = sys.exc_info()[:2]
        if ss.debug_enabled: logger.error('sync_pix: *********** error: ' + str(err))
        reload_config_pix()
        return False
    if sync_server_pix(album_with_media[ss.slideshow_album]):
        str_datetime = str(datetime.utcnow())
        str_datetime = str_datetime[:10] + ' ' + str_datetime[11:19]
        mod_date_object = datetime.strptime(str_datetime, '%Y-%m-%d %H:%M:%S')
        config.set('Frame Parameters', 'album_mod', str(mod_date_object))
        config.set('Frame Parameters', 'photo_mod', str(mod_date_object))
        with open(ss.config_path, 'w') as configfile:
            config.write(configfile)
    else:
        if ss.debug_enabled: logger.error('sync_pix: Error reading sync_server_pix(): ' + str(datetime.now())[0:19])
        return False
    return True
#  end of sync_pix():

# ----------------------------------------------
def setup_system(*kwargs):
# ----------------------------------------------
# do prep work on the Sleep parms and check if frame was asleep then recovering from power failure or restart

    if ss.sleep_enabled:
        calc_sleep()

# Set Frame Brightness
    if ss.frame_sleeping == False:
        set_brightness(ss.current_brightness)    # set server brightness value

# Need to setup counter based on sync_count to test for network and server (i.e. Google) connectivity. Icon to indicate offline
# in cases where it should be online. That is, if there is an option to not connect to server, connectivity is superfluous.

    ss_utils.config_write(ss, config, logger)
    if ss.debug_enabled: logger.warning('setup_system: Config File written @ ' + str(datetime.now())[0:19])
    setup_captions()
    setup_digitalclock()     # Setup new feed values for digitalclock
    setup_outside_info()     # Setup new feed values for weather

# ----------------------------------------------
def reload_config_pix(*kwargs):
# ----------------------------------------------
# This routine handles reloading the pictures from the pix folder. If there are none in that
# folder then it is possibly the first time this Frame has started and there's no network 
# connection. In this case, load pictures from data/data/com.masterpics.slideshow/pix folder
# - standard offline init.
    global ss_pictures, ss_captions

# if no internet connection the first time through so read the local config file for picture names
    ss_pictures = []
    ss_captions = []
    del ss_pictures[:]  # clear the list
    del ss_captions[:] 
    config.read(ss.config_path)
    ss.slide_count = config.getint('Slideshow Order', 'slide_count')
    if ss.slide_count == 0:
        logger.critical('reload_config_pix: ---> SlideShow Order is zero (0) in slideshow.cfg file.')
        return False

    if len(os.listdir(ss.local_pix))==0:
        logger.error('reload_config_pix: - No Local PIX - Loading Offline Initialization slides')
        if platform == 'android': 
	        from android.storage import primary_external_storage_path
	        ss.local_pix = primary_external_storage_path() + '/.slideshow/data/pix/'
        else: 
            ss.local_pix = os.path.dirname(os.path.realpath(sys.argv[0])) + '/data/pix/'

    i = 0
    while (i < ss.slide_count):
        file = config.get('Slideshow Order', 'slide[' + str(i) + ']')
        ss_pictures.append(ss.local_pix + file)
        current_caption = config.get('Captions List', 'caption[' + str(i) + ']')
        ss_captions.append(current_caption)
        if ss.debug_enabled: logger.warning('reload_config_pix: [' + str(i) + '] ' + str(file))
        i += 1
    if ss.slide_count == 1:
        ss_pictures.append(ss.local_pix + file)  # put dup in for page 2 when only one picture in album
        ss_captions.append(current_caption)
    logger.info('reload_config_pix: RELOADED pix from config file locally. Ordered pix=' + str(ss.slide_count))
    if ss.random_enabled and ss.slide_count > 2:
        ss.random_list = [i for i in range(ss.slide_count)]  # setup initial sequence to randomize
        randomize_slides()
    return

# ----------------------------------------------
def calc_sleep(*kwargs):
# ----------------------------------------------
# This is a core routine to determine start and end of Sleep Time. Because starting the SlideShow can occur any time of day, this routine
# needs to setup the start and end time based on the day, all flags indicating current sleep or awakened states, and handle when Daylight
# Savings Time (DST) starts/ends. All these conditions are setup by the user at any times of the day, same day or overnight sleep times. 
# In the code below, the logic handles overnight restarts due to power outages or other restart conditions.

    waketime = datetime.strptime(str(datetime.now())[:19], '%Y-%m-%d %H:%M:%S')
    dt_start_sleep_time = datetime.strptime(ss.start_sleep_time, '%H:%M:%S')
    dt_end_sleep_time = datetime.strptime(ss.end_sleep_time, '%H:%M:%S')
    ss.frame_sleeping = False

    # The code below handles same day processing for timed/timed sleep that is NOT sleep_modes: timed/solar, solar/timed, and solar/solar.

    if 'solar' not in ss.sleep_mode and dt_start_sleep_time > dt_end_sleep_time:     # Overnight Sleep Times
        ss.start_sleep_datetime = waketime.replace(hour=dt_start_sleep_time.hour, minute=dt_start_sleep_time.minute, second=dt_start_sleep_time.second)
        ss.end_sleep_datetime = waketime.replace(hour=dt_end_sleep_time.hour, minute=dt_end_sleep_time.minute, second=dt_end_sleep_time.second)
        if waketime <= ss.start_sleep_datetime:
            ss.end_sleep_datetime = ss.end_sleep_datetime + timedelta(days=1)
            if ss.debug_enabled: logger.warning('calc_sleep: Timed Overnight Sleep woke @ ' + str(waketime) + ' before start_sleep_datetime @ ' + str(ss.start_sleep_datetime) + ' - end date = ' + str(ss.end_sleep_datetime) + '.')
        elif waketime > ss.end_sleep_datetime:
            if ss.debug_enabled: logger.warning('calc_sleep: Timed Overnight Sleep woke @ ' + str(waketime) + ' after end_sleep_datetime @ ' + str(ss.end_sleep_datetime) + '.')
            ss.start_sleep_datetime = ss.start_sleep_datetime + timedelta(days=1)
            ss.end_sleep_datetime = ss.end_sleep_datetime + timedelta(days=1)
        if waketime > ss.start_sleep_datetime and waketime < ss.end_sleep_datetime:
            ss.frame_sleeping = True 
            if ss.debug_enabled: logger.warning('calc_sleep: Timed Sleeping Overnight @ ' + str(waketime) + ' until end_sleep_datetime @ ' + str(ss.end_sleep_datetime) + '.')
            ss.sleep_seconds = (ss.end_sleep_datetime - waketime).seconds
            if ss.debug_enabled: logger.warning('calc_sleep: New Overnight ss.sleep_seconds = ' + str(ss.sleep_seconds))
            return 
        ss.sleep_seconds = (ss.end_sleep_datetime - ss.start_sleep_datetime).seconds
        if ss.debug_enabled: logger.warning('calc_sleep: Timed overnight start_sleep_datetime = ' + str(ss.start_sleep_datetime) + ', end_sleep_datetime = ' + str(ss.end_sleep_datetime) + ', sleep_seconds = ' + str(ss.sleep_seconds))
        return

    elif 'solar' not in ss.sleep_mode and dt_start_sleep_time < dt_end_sleep_time:     # Same Day Sleep Times
        ss.start_sleep_datetime = waketime.replace(hour=dt_start_sleep_time.hour, minute=dt_start_sleep_time.minute, second=dt_start_sleep_time.second)
        ss.end_sleep_datetime = waketime.replace(hour=dt_end_sleep_time.hour, minute=dt_end_sleep_time.minute, second=dt_end_sleep_time.second)
        logger.info('calc_sleep: Set same day start_sleep_datetime=' + str(ss.start_sleep_datetime) + ' and end_sleep_datetime=' + str(ss.end_sleep_datetime))
        return

    elif 'solar' not in ss.sleep_mode and dt_start_sleep_time == dt_end_sleep_time:
        ss.sleep_enabled = False
        logger.info('calc_sleep: Ignoring same start_sleep_datetime=' + str(ss.start_sleep_datetime) + ' and end_sleep_datetime=' + str(ss.end_sleep_datetime))
        return

    # The code below handles same day processing for sleep that contains solar sleep_modes: timed/solar, solar/timed, and solar/solar.

    try:
        sun = location.sun(date=waketime, local=True)
    except Exception as err:
        ss.end_sleep_datetime = ss.end_sleep_datetime + timedelta(days=1) 
        ss.start_sleep_datetime = ss.start_sleep_datetime + timedelta(days=1) 
        logger.error('calc_sleep: Failed to obtain solar times, using default Timed times. Exception = ' + str(err))
        logger.info('calc_sleep: Final: waketime=' + str(waketime) + ', start_sleep_datetime=' + str(ss.start_sleep_datetime) + ', end_sleep_datetime=' + str(ss.end_sleep_datetime))
        pass
        return 

    solar_end_datetime = datetime.strptime(str(sun[ss.end_astro_time])[:19], '%Y-%m-%d %H:%M:%S')
    solar_start_datetime = datetime.strptime(str(sun[ss.start_astro_time])[:19], '%Y-%m-%d %H:%M:%S')

    if waketime >= solar_end_datetime:
        tmp_waketime = waketime + timedelta(days=1)
        sun = location.sun(date=tmp_waketime, local=True)
        solar_end_datetime = datetime.strptime(str(sun[ss.end_astro_time])[:19], '%Y-%m-%d %H:%M:%S')
        if ss.sleep_mode == 'timed/timed':
            ss.start_sleep_datetime = waketime.replace(hour=dt_start_sleep_time.hour, minute=dt_start_sleep_time.minute, second=dt_start_sleep_time.second)
            ss.end_sleep_datetime = tmp_waketime.replace(hour=dt_end_sleep_time.hour, minute=dt_end_sleep_time.minute, second=dt_end_sleep_time.second)
        if ss.sleep_mode == 'solar/timed':
            ss.start_sleep_datetime = waketime.replace(hour=dt_start_sleep_time.hour, minute=dt_start_sleep_time.minute, second=dt_start_sleep_time.second)
            ss.end_sleep_datetime = solar_end_datetime
        if ss.sleep_mode == 'timed/solar':
            ss.start_sleep_datetime = solar_start_datetime
            ss.end_sleep_datetime = tmp_waketime.replace(hour=dt_end_sleep_time.hour, minute=dt_end_sleep_time.minute, second=dt_end_sleep_time.second)
        if ss.sleep_mode == 'solar/solar':
            ss.end_sleep_datetime = solar_end_datetime
            ss.start_sleep_datetime = solar_start_datetime
    else:
        tmp_waketime = waketime - timedelta(days=1)
        sun = location.sun(date=tmp_waketime, local=True)
        solar_start_datetime = datetime.strptime(str(sun[ss.start_astro_time])[:19], '%Y-%m-%d %H:%M:%S')
        if ss.sleep_mode == 'timed/timed':
            ss.start_sleep_datetime = tmp_waketime.replace(hour=dt_start_sleep_time.hour, minute=dt_start_sleep_time.minute, second=dt_start_sleep_time.second)
            ss.end_sleep_datetime = waketime.replace(hour=dt_end_sleep_time.hour, minute=dt_end_sleep_time.minute, second=dt_end_sleep_time.second)
        if ss.sleep_mode == 'solar/timed':
            ss.start_sleep_datetime = tmp_waketime.replace(hour=dt_start_sleep_time.hour, minute=dt_start_sleep_time.minute, second=dt_start_sleep_time.second)
            ss.end_sleep_datetime = solar_end_datetime
        if ss.sleep_mode == 'timed/solar':
            ss.start_sleep_datetime = solar_start_datetime
            ss.end_sleep_datetime = waketime.replace(hour=dt_end_sleep_time.hour, minute=dt_end_sleep_time.minute, second=dt_end_sleep_time.second)
        if ss.sleep_mode == 'solar/solar':
            ss.end_sleep_datetime = solar_end_datetime
            ss.start_sleep_datetime = solar_start_datetime

    ss.sleep_seconds = (ss.end_sleep_datetime - ss.start_sleep_datetime).seconds

    # At this point all dates are setup based on the day awoken. If slideshow isn't asleep, then exit.
    # Otherwise, now is the time to return the slideshow back to sleep.

    if waketime >= ss.start_sleep_datetime and waketime < ss.end_sleep_datetime:   # Slideshow is Sleeping.
        ss.sleep_seconds = (ss.end_sleep_datetime - waketime).seconds
        ss.frame_sleeping = True 
        if ss.debug_enabled: logger.warning('calc_sleep: SlideShow is asleep until ' + str(ss.end_sleep_datetime) + '.')
    if ss.dst_enabled: 
        config_dst()
        calc_dst()
    if ss.debug_enabled: logger.warning('calc_sleep: Final Solar: waketime=' + str(waketime) + ', start_sleep_datetime=' + str(ss.start_sleep_datetime) + ', end_sleep_datetime=' + str(ss.end_sleep_datetime))
    return
# End of calc_sleep routine.

#--------------------------------------------------------
class SS_Sync:
#--------------------------------------------------------
#  This is the class for the slideshow clock so that slides sitting more than a few seconds is accurate, not off more than 3 seconds.
#  This object runs only while NOT asleep, i.e. framesleeping == False.
    global page1, page2, this_app
    
    logger.info('SS_SYNC: Instantiated @ ' + str(datetime.now())[0:19])
    
    #--------------------------------------------------------
    def check_time(*kwargs):
    #--------------------------------------------------------

        if ss.nexting:    # don't do anything while downloading in process...
            if ss.debug_enabled: logger.warning('check_time: NEXT routine in process, exiting for a while.')
            Clock.schedule_once(SS_Sync.check_time, 3)  # come back in a few seconds after NEXT finishes
            return

        if not ss.frame_sleeping and ss.digitalclock_displayed:
            if ss.clock_sync != datetime.strptime(str(datetime.now())[11:16], '%H:%M'):
            # Don't update clock during transition...
                if this_app.page1.transition_progress == 0.0 or this_app.page2.transition_progress == 0.0:
                    if this_app.screenManager.current=='page1':
                        this_app.clock_page1_update()
                    elif this_app.screenManager.current=='page2':
                        this_app.clock_page2_update()
                    ss.clock_sync = datetime.strptime(str(datetime.now())[11:16], '%H:%M')
                else:
                    logger.warning('SS_Sync.check_time: page1.transition_progress = ' + str(round(this_app.page1.transition_progress,2)) + ', page2.transition_progress = ' + str(round(this_app.page2.transition_progress,2)) + ', transition in process, exiting for 5 seconds.')
                    Clock.schedule_once(SS_Sync.check_time, 5)
                    return

#   Go to sleep when it's time instead of waiting for next()
#   NOTE: This is the same code to sleep in next routine with exceptions: ss.nexting not set to False and only do this sleep mode 
#         when app not awoken. Otherwise, you can never wake from sleep.

        if ss.sleep_enabled and not ss.frame_sleeping and not ss.frame_awoken and datetime.now() > ss.start_sleep_datetime and datetime.now() < ss.end_sleep_datetime:
            Clock.unschedule(this_app.next)
            blank_screen()
            ss.frame_sleeping = True
            ss.sleep_seconds = (ss.end_sleep_datetime - datetime.now()).seconds     # Set seconds based on current time due to display duration.
            if ss.dst_enabled: 
                config_dst()
                calc_dst()
            logger.info('SS_Sync.check_time Going to SLEEP starting at @ ' + str(datetime.now())[0:19] + ', until: end_sleep_datetime=' + str(ss.end_sleep_datetime) + ', sleep_seconds = ' + str(ss.sleep_seconds))
            Clock.schedule_once(this_app.wakeup, ss.sleep_seconds)

        if not ss.frame_sleeping and datetime.now() > ss.sync_start_time + timedelta(seconds=ss.gc_interval):
            update_gc_mem()
            if ss.outside_info_enabled: this_app.weather_update()
            ss.sync_start_time = datetime.now()

        Clock.schedule_once(SS_Sync.check_time, 3)  # check again in 3 seconds

#--------------------------------------------------------
class SS_Loader:
#--------------------------------------------------------
#  This is the class for the slideshow connection
    global this_app
    
    logger.info('CHECK_SERVER: Instantiated @ ' + str(datetime.now())[0:19])
    
    #--------------------------------------------------------
    def check_server(*kwargs):
    #--------------------------------------------------------

        if ss.sync_interval == 0:
            logger.warning('check_server: Shutdown Google kills this module and is terminating.')
            return

        if ss.nexting:    # don't do anything while downloading in process...
            if ss.debug_enabled: logger.warning('check_server: NEXT routine in process, exiting for a while.')
            Clock.schedule_once(SS_Loader.check_server, 20)  # come back in a couple seconds after NEXT finishes
            return

        if test_connect(15) == False:
            logger.error('check_server: - failed to connect to server @ ' + str(datetime.now())[0:19] + ' - retrying in a minute.')
            Clock.schedule_once(SS_Loader.check_server, 60) # Try again in a while
            ss.downloading = False   # Tell NEXT that we're clear for now...
            return

        if this_app.page1.transition_progress < 1.0 and this_app.page1.transition_progress != 0.0 :
            if ss.debug_enabled: logger.warning('check_server: page1.transition_progress = ' + str(this_app.page1.transition_progress) + ', transition in process, returning in 5 seconds.')
            Clock.schedule_once(SS_Loader.check_server, 5)  # come back after transition finishes
            return

        ss.downloading = True   # Tell NEXT we're busy with updates...
        logger.warning('CHECK_SERVER @ ' + str(datetime.now())[0:19])
        init_vars(False)
        sync_pix()
        
        ss.downloading = False   # Tell NEXT we're done.
        Clock.schedule_once(SS_Loader.check_server, ss.sync_interval)
        return True
        
#  end of SS_Loader Class and check_server()
# ----------------------
class MessageBoxApp(App):
# ----------------------
    global credentials_gdrv, credentials_ss, this_app, page1, page2, anim, current_page
    
    #--------------------------------------------------------
    def callpopup(self,*largs):
    #--------------------------------------------------------
        Clock.unschedule(this_app.next) # Turn off next clock
        # This routine loads all program variables from the server database
        # Now calling on Google for the spreadsheet containing the FrameConfiguration values...
        new_option = {}
        if not ss.frame_sleeping:
            new_option['About SlideShow']='process_control(' + chr(34) + 'About' + chr(34) + ')'
        new_option['Close Window']='process_control(' + chr(34) + 'Close' + chr(34) + ')'
        new_option['Download New Pictures']='process_control(' + chr(34) + 'Download' + chr(34) + ')'
        new_option['Exit SlideShow']='process_control(' + chr(34) + 'Exit' + chr(34) + ')'
        new_option['Play New-Picture Audio']='process_control(' + chr(34) + 'PlayNewPic' + chr(34) + ')'
        new_option['Reload SlideShow Configuration']='process_control(' + chr(34) + 'Reload' + chr(34) + ')'
        if test_connect(5):
            new_option['View Albums']='process_control(' + chr(34) + 'List_Albums' + chr(34) + ')'
        else:
            new_option['Offline: Albums not available.']='process_control(' + chr(34) + 'Close' + chr(34) + ')'
        dlg = MessageBox(self, titleheader="SlideShow Control Panel", message='', options=new_option, size=(400, len(new_option)*60))
        return

    #--------------------------------------------------------
    def load_about(self,*largs):
    #--------------------------------------------------------

        import datetime     # This line of code is something that does not work at the top of this file. Strange things in python world.
        Clock.unschedule(self.load_about)
        pops = AboutPopup()
        about_contents = 'Version: ' + dev_version + '\n-----------------------------\n'
        if platform == 'android':
            temp_proc = subprocess.Popen(args=["getprop ro.build.version.release"], stdout=subprocess.PIPE, shell=True)
            complete_val, err = temp_proc.communicate()
            about_contents = about_contents + 'Android Version: ' + str(complete_val)[2:len(str(complete_val))-3] + '\n'
            temp_proc = subprocess.Popen(args=["getprop net.hostname"], stdout=subprocess.PIPE, shell=True)
        else:
            temp_proc = subprocess.Popen(args=["uname -r"], stdout=subprocess.PIPE, shell=True)
            complete_val, err = temp_proc.communicate()
            about_contents = about_contents + 'Linux Version: ' + str(complete_val)[2:len(str(complete_val))-3] + '\n'
            temp_proc = subprocess.Popen(args=["hostname"], stdout=subprocess.PIPE, shell=True)
        complete_val, err = temp_proc.communicate()
        about_contents = about_contents + 'Host Name: ' + str(complete_val)[2:len(str(complete_val))-3] + '\n'
        ip_list = format_ip("ip a s eth0 | grep -w 'inet'")
        if ip_list == '': ip_list = 'Not Connected'
        about_contents = about_contents + 'Wired IP Addresses: ' + ip_list + '\n'
        ip_list = format_ip("ip a s wlan0 | grep -w 'inet'")
        if ip_list == '': ip_list = 'Not Connected'
        about_contents = about_contents + 'Wireless IP Addresses: ' + ip_list + '\n'
        about_contents = about_contents + '-----------------------------\n'
        about_contents = about_contents + 'SlideShow Album: ' + ss.slideshow_album + '\n'
        about_contents = about_contents + 'SlideShow Started: ' + slideshow_started_datetime + '\n'
        about_contents = about_contents + 'Number of Slides: ' + str(ss.slide_count) + '\n'
        about_contents = about_contents + 'Captions Enabled: ' + str(ss.captions_enabled) + '\n'
        about_contents = about_contents + 'Digital Clock Enabled: ' + str(ss.digitalclock_enabled) + '\n'
        about_contents = about_contents + 'Outside Info Enabled: ' + str(ss.outside_info_enabled) + '\n'
        about_contents = about_contents + 'Banner Locations: ' + str(ss.banner_locations) + '\n'
        about_contents = about_contents + 'Weather Location: ' + ss.weather_location_full + '\n'
        about_contents = about_contents + 'Weather Time Zone: ' + ss.weather_timezone + '\n'
        about_contents = about_contents + 'Display Brightness: ' + str(int(float(ss.current_brightness) * (100/255))) + '%\n'
        about_contents = about_contents + 'Frame Volume: ' + str(int(float(ss.current_volume) * 100)) + '% \n'
        if int(ss.pause_duration) == 0: timeout = 'Never'
        else: timeout = str(ss.pause_duration) + ' seconds'
        about_contents = about_contents + 'Tap Pause Timeout: ' + timeout + '\n'
        about_contents = about_contents + 'Tap Pause Timeout (sleeping): ' + str(ss.awake_time_pause) + ' seconds\n'
        about_contents = about_contents + 'Transition Type: ' + transition_display_names[ss.transition_type] + '\n'
        about_contents = about_contents + 'Transition Duration: ' + str(ss.transition_duration) + ' seconds\n'
        about_contents = about_contents + 'Slides Displayed Duration: ' + str(datetime.timedelta(seconds=ss.slide_duration))[:8] + ' (hh:mm:ss)\n'   #str(ss.slide_duration) + ' seconds\n'
        about_contents = about_contents + 'New Picture Notification: ' + str(ss.newpix_enabled) + '\n'
        about_contents = about_contents + 'New Picture Ringtone: ' + ss.newpix_ringtone + '\n'
        about_contents = about_contents + 'Sleep Enabled: ' + str(ss.sleep_enabled) + '\n'
        about_contents = about_contents + 'Sleep Mode: ' + ss.sleep_mode + '\n'
        if 'solar' in ss.sleep_mode: 
            if 'timed/' in ss.sleep_mode:
                about_time_start = str(ss.start_sleep_datetime) + ' (' + ss.start_astro_time + ')'
                about_time_end = str(ss.end_sleep_datetime) + ' (timed)'
            elif '/timed' in ss.sleep_mode:
                about_time_start = str(ss.start_sleep_datetime) + ' (timed)'
                about_time_end = str(ss.end_sleep_datetime) + ' (' + ss.end_astro_time + ')'
            else:
                about_time_start = str(ss.start_sleep_datetime) + ' (' + ss.start_astro_time + ')'
                about_time_end = str(ss.end_sleep_datetime) + ' (' + ss.end_astro_time + ')'
        else:
            about_time_end = str(ss.end_sleep_time) + ' (timed)'
            about_time_start = str(ss.start_sleep_time) + ' (timed)'
        about_contents = about_contents + 'Sleep Start Time: ' + about_time_start + '\n'
        about_contents = about_contents + 'Sleep End Time: ' + about_time_end + '\n'
        about_contents = about_contents + 'Daylight Savings Time Enabled: ' + str(ss.dst_enabled) + '\n'
        about_contents = about_contents + 'Daylight Savings Time Start: ' + str(ss.march_dst)[:10] + '\n'
        about_contents = about_contents + 'Daylight Savings Time End: ' + str(ss.november_dst)[:10] + '\n'
        about_contents = about_contents + 'Debug Enabled: ' + str(ss.debug_enabled) + '\n'
        about_contents = about_contents + 'Swipe Enabled: ' + str(ss.swipe_enabled) + '\n'
        about_contents = about_contents + 'Server Sync Intervals: ' + str(datetime.timedelta(seconds=ss.sync_interval))[:5] + ' (hh:mm)\n'
        about_contents = about_contents + 'Spreadsheet Last Download: ' + str(ss.spreadsheet_mod) + ' UTC\n'
        about_contents = about_contents + 'Album Last Download: ' + str(ss.album_mod) + ' UTC\n'
        about_contents = about_contents + 'Photos Last Download: ' + str(ss.photo_mod) + ' UTC\n'
        pops.contents = about_contents
        pops.open()
        return

    #--------------------------------------------------------
    def load_albums(self,*largs):
    #--------------------------------------------------------
        global  gdrv_files

        Clock.unschedule(self.load_albums)
        if not gdrv_files:
            logger.error('callpopup: gdrv_files not valid')
            return False
            
        if ss.debug_enabled: logger.warning('load_albums: Attempting connection to Album server @ ' + str(datetime.now())[0:19])

        Album_list = []
        for item in gdrv_files.get('files', []):
            if str(item['name']) == 'SS-FrameConfiguration' and 'spreadsheet' in str(item['mimeType']):
                if ss.debug_enabled: logger.warning('load_albums: Frame configuration from SS-FrameConfiguration spreadsheet loaded @ ' + str(datetime.now())[0:19])
                ss.spreadsheetId = item['id']

                try:
                    creds_sheets = get_creds(pickle_path_sheets, credentials_path_sheets, SCOPES_sheets)
                    service_ss = build('sheets', 'v4', credentials=creds_sheets)
                    sheet = service_ss.spreadsheets()
                    results = sheet.values().get(spreadsheetId=ss.spreadsheetId, range=RANGE_NAME).execute()
                except:
                    err = sys.exc_info()[:2]
                    if "callpopup: 'socket.error'" not in str(err):
                        logger.critical('load_albums: - Google Spreadsheet no response, loading local config @ ' + str(datetime.now())[0:19])
                        logger.error('*********** error: ' + str(err))
                        setup_system()
                        return False
                    
                values = results.get('values', [])
                frame_feed = {}

                if not values:
                    logger.critical('load_albums: - Invalid Google Spreadsheet db feed null results @ ' + str(datetime.now())[0:19])
                    return False
                    
                Albums_index = 0
                for row in values: 
                    if row[0] == 'slideshow_album':
                        for column in row:
                            if Albums_index > 1 and ss.slideshow_album!=column: 
                                Album_list.append(column)
                            Albums_index +=1
        new_option = {}
        new_option['Close Window']='process_control(' + chr(34) + 'Close' + chr(34) + ')'
        for name in Album_list:
            new_option[name]='process_control(' + chr(34) + name + chr(34) + ')'
        dlg = MessageBox(self, titleheader="Choose SlideShow Album", message='', options=new_option, size=(400, len(new_option)*60))
        Clock.unschedule(this_app.next)
        return

    #--------------------------------------------------------
    def process_control(self, msg):
    #--------------------------------------------------------
        global screenManager, page1, page2
        
        if msg=='Exit':
            logger.critical('process_control: Exiting SlideShow app from Control Panel.')
            sys.exit()
        if msg=='About':
            if ss.debug_enabled: logger.warning('process_control: Showing SlideShow ABOUT WINDOW.')
            Clock.schedule_once(self.load_about, .1)
            if int(ss.pause_duration) == 0:             # If PAUSED forever, get over it for ABOUT.
                Clock.schedule_once(this_app.next, 1)
            this_app.check_sleeping()
            return
        if msg=='Close' and not ss.frame_sleeping:
            if ss.debug_enabled: logger.warning('process_control: Closing Control Panel while awake.')
            this_app.check_sleeping()
            return
        if msg=='Close' and ss.frame_sleeping:
            if ss.debug_enabled: logger.warning('process_control: Closing Control Panel while sleeping.')
            this_app.check_sleeping()
            return
        if msg=='Download':
            if ss.debug_enabled: logger.warning('process_control: Attempting to Download new Album from server, if any changes.')
            sync_pix()
            this_app.check_sleeping()
            return
        if msg=='Reload':
            if ss.debug_enabled: logger.warning('process_control: Attempting to Reload Remote Configuration file from server, if any changes.')
            init_vars(True)
            if ss.outside_info_enabled: this_app.weather_update()
            this_app.check_sleeping()
            return
        if msg=='PlayNewPic':
            if ss.debug_enabled: logger.warning('process_control: Playing New Picture Song.')
            play_newpix()
            this_app.check_sleeping()
            return
        if msg=='List_Albums':
            if ss.debug_enabled: logger.warning('process_control: Attempting to download Albums from server.')
            Clock.schedule_once(self.load_albums, .1)
            return
        ss.slideshow_album = str(msg)
        if ss.captions_displayed:
            ss.captions_displayed = False
            this_app.page1.remove_widget(ss.caption1_content)           # Remove all widgets from both pages
            this_app.page2.remove_widget(ss.caption2_content)
        if ss.digitalclock_displayed:
            ss.digitalclock_displayed = False
            this_app.page1.remove_widget(ss.digitalclock1_content) 
            this_app.page2.remove_widget(ss.digitalclock2_content)
        if ss.outside_info_displayed:
            ss.outside_info_displayed = False
            this_app.page2.remove_widget(ss.outside_temp2_content)
            ss.outside_temp2_content.remove_widget(ss.outside_temp2_label)
            this_app.page1.remove_widget(ss.outside_temp1_content)
            ss.outside_temp1_content.remove_widget(ss.outside_temp1_label)
            this_app.page1.remove_widget(ss.outside_humidity1_content)
            this_app.page2.remove_widget(ss.outside_humidity2_content)
            this_app.page1.remove_widget(ss.outside_temp1_content)
            this_app.page2.remove_widget(ss.outside_temp2_content)
#            this_app.page1.remove_widget(ss.weather_icon1_content)
#            this_app.page2.remove_widget(ss.weather_icon2_content)

# Do it again since sometimes it doesn't work the first time in android, maybe linux too.
        try:
            this_app.page1.remove_widget(ss.caption1_content)
            this_app.page2.remove_widget(ss.caption1_content)
        except Exception as err:
            logger.error('process_control: ss.caption1_content remove_widget err: ' + str(err))
            pass
        try:
            this_app.page1.remove_widget(ss.caption2_content)
            this_app.page2.remove_widget(ss.caption2_content)
        except Exception as err:
            logger.error('process_control: ss.caption2_content remove_widget err: ' + str(err))
            pass
        try:
            this_app.page1.remove_widget(ss.digitalclock1_content) 
            this_app.page2.remove_widget(ss.digitalclock1_content) 
        except Exception as err:
            logger.error('process_control: ss.digitalclock1_content remove_widget err: ' + str(err))
            pass
        try:
            this_app.page1.remove_widget(ss.digitalclock2_content)
            this_app.page2.remove_widget(ss.digitalclock2_content)
        except Exception as err:
            logger.error('process_control: ss.digitalclock2_content remove_widget err: ' + str(err))
            pass
        try:
#            this_app.page1.remove_widget(ss.weather_icon1_content)
            this_app.page1.remove_widget(ss.outside_humidity1_content)
            this_app.page2.remove_widget(ss.outside_humidity1_content)
        except Exception as err:
            logger.error('process_control: ss.outside_humidity1_content remove_widget err: ' + str(err))
            pass
        try:
#            this_app.page2.remove_widget(ss.weather_icon2_content)
            this_app.page1.remove_widget(ss.outside_humidity2_content)
            this_app.page2.remove_widget(ss.outside_humidity2_content)
        except Exception as err:
            logger.error('process_control: ss.outside_humidity2_content remove_widget err: ' + str(err))
            pass
        try:
            this_app.page1.remove_widget(ss.outside_temp1_content)
            this_app.page2.remove_widget(ss.outside_temp1_content)
        except Exception as err:
            logger.error('process_control: ss.outside_temp1_content remove_widget err: ' + str(err))
            pass
        try:
            this_app.page1.remove_widget(ss.outside_temp2_content)
            this_app.page2.remove_widget(ss.outside_temp2_content)
        except Exception as err:
            logger.error('process_control: ss.outside_temp2_content remove_widget err: ' + str(err))
            pass
#        try:
#            this_app.page1.remove_widget(ss.weather_icon1_content)
#        except Exception as err:
#            logger.error('process_control: ss.weather_icon1_content remove_widget err: ' + str(err))
#            pass
#        try:
#            this_app.page2.remove_widget(ss.weather_icon2_content)
#        except Exception as err:
#            logger.error('process_control: ss.weather_icon2_content remove_widget err: ' + str(err))
#            pass

        this_app.screenManager.remove_widget(this_app.page1)
        this_app.screenManager.remove_widget(this_app.page2)
        this_app.screenManager.clear_widgets()
        try:
            this_app.screenManager.remove_widget(this_app.page1)
        except Exception as err:
            logger.error('process_control: screenManager.remove_widget(this_app.page1) err: ' + str(err))
            pass
        try:
            this_app.screenManager.remove_widget(this_app.page2)
        except Exception as err:
            logger.error('process_control: screenManager.remove_widget(this_app.page2) err: ' + str(err))
            pass
        try:
            this_app.screenManager.clear_widgets()
        except Exception as err:
            logger.error('process_control: screenManager.clear_widgets() err: ' + str(err))
            pass
        this_app.page1 = Page(name='page1', source = ss_data_path + 'pix/loading-slideshow.png')
        this_app.page2 = Page(name='page2', source = ss_data_path + 'pix/loading-slideshow.png')
        this_app.screenManager.add_widget(this_app.page1)
        this_app.screenManager.add_widget(this_app.page2)

        this_app.page1.source = ss_data_path + 'pix/loading-slideshow.png'  # Show downloading slide...
        this_app.page2.source = ss_data_path + 'pix/loading-slideshow.png'
        Clock.schedule_once(self.reset_frame, 1)

#   This is where ss.object variables are reset, the frame id is set, and all frame variables reloaded in this routine.

    #--------------------------------------------------------
    def reset_frame(*kwargs):
    #--------------------------------------------------------
        global page1, page2, anim, current_page, screenManager

        ss.spreadsheet_mod = '2000-01-01 12:00:00'
        ss.photo_mod = '2000-01-01 12:00:00'
        ss.album_mod = '2000-01-01 12:00:00'

        init_vars(True)
        sync_pix()
        ss.slideshow_index = 0     # reset photo index back to zero

        config = configparser.ConfigParser()
        try:
            config.read(ss.config_path)
        except Exception as err:   # No config file? Exit SlideShow app...
            logger.error('reset_frame: Exception during config.read '+ str(err))
            sys.exit()
        config.set('Frame Parameters', 'id', str(ss.slideshow_album))
        with open(ss.config_path, 'w') as configfile:
            config.write(configfile)
        if ss.debug_enabled: logger.warning('reset_frame: local config file updated with SlideShow Album named <[' + ss.slideshow_album + ']> @ ' + str(datetime.now())[0:19])

        if(this_app.screenManager.current == 'page1'):
            next = 'page2'
            current_page = this_app.page2
        else:
            next = 'page1'
            current_page = this_app.page1

        # Setup next caption when enabled
        if ss.captions_enabled: update_captions()
        if ss.digitalclock_enabled: this_app.clock_update()
        if ss.outside_info_enabled: this_app.weather_update()

        this_app.screenManager.transition = SlideTransition(direction='left')
        current_page.source = ss_pictures[ss.slideshow_index]
        current_page.background.scale = ss.scale_start
        this_app.screenManager.current = next
        anim = Animation(center=ss.display_center, d=0) + Animation(scale=float(ss.scale_end), duration=int(ss.slide_scale_timing), center=ss.display_center)
        anim.start(current_page.background)
        update_gc_mem()                         # Garbage collect and log memory
        Clock.schedule_once(this_app.next, 10)

#--------------------------------------------------------
class MessageBox(MessageBoxApp):
#--------------------------------------------------------
    def __init__(self, parent, titleheader="default", message="default", options={"OK": ""}, size=(400, 400)):

        def popup_callback(instance):
            self.retvalue = instance.text
            self.popup.dismiss()

        self.parent = parent
        self.retvalue = None
        self.titleheader = titleheader
        self.message = message
        self.options = options
        self.size = size
        box = GridLayout(cols=1)
        b_list =  []
        buttonbox = BoxLayout(orientation='vertical')   #horizontal
        new_options=sorted(self.options)
        for b in new_options:
            b_list.append(Button(text=b, size_hint=(1,.35), font_size=20))
            b_list[-1].bind(on_press=popup_callback)
            buttonbox.add_widget(b_list[-1])
        box.add_widget(buttonbox)
        self.popup = Popup(title=titleheader, title_align='center', title_size=24, content=box, size_hint=(None, None), size=self.size)
        self.popup.open()
        self.popup.bind(on_dismiss=self.OnClose)

    #--------------------------------------------------------
    def OnClose(self, event):
    #--------------------------------------------------------
        self.popup.unbind(on_dismiss=self.OnClose)
        self.popup.dismiss()
        if self.retvalue != None and self.options[self.retvalue] != "":
            command = "self.parent."+self.options[self.retvalue]
            exec(command)
        else: Clock.schedule_once(this_app.next, .5)

MessageBoxApp = MessageBoxApp()  # Create an instance of MessageBoxApp

# --------------------
# class for Kivy screens  (see slideshow.kv file)
# --------------------
class Page(Screen):
    source = StringProperty()
# --------------------
class AboutPopup(Popup):
    contents = StringProperty()
# --------------------
class ScreenManagement(ScreenManager):
    pass
# --------------------
class SlideShow(App):
# --------------------
# the main application
    global page1, page2, screenManager

    # ----------------------------------------------
    def build(self):
    # ----------------------------------------------
        global page1, page2, screenManager, this_app
        this_app = self

# This section sets up the ScreenManager for two pages of initial splash screen.
# The startup routine will load and display the first image of the SlideShow.
# The next routine will load and display the second and subsequent images of the SlideShow.
        wake_screen()                   # Make sure screen is turned on should power be off
        self.screenManager = ScreenManagement(transition=FadeTransition(duration=1.5))
        self.page1 = Page(name='page1', source = ss_path + 'data/pix/bootstill.png')
        self.page2 = Page(name='page2', source = ss_path + 'data/pix/bootstill.png')

        self.screenManager.add_widget(self.page1)
        self.screenManager.add_widget(self.page2)
        self.screenManager.current = 'page1'
        anim = Animation(scale=1)
        anim.start(self.page1.background)
        Clock.schedule_once(self.startup, 7)

        ss.display_width = Window.size[0]
        ss.display_height = Window.size[1]
        ss.display_center = (ss.display_width/2,ss.display_height/2)
        if ss.debug_enabled: logger.warning('build: Frame Display Reported Resolution: ' + str(ss.display_width) + 'x' + str(ss.display_height))

        return self.screenManager

    # ----------------------------------------------
    def startup(self,*largs):
    # ----------------------------------------------
        #--- test for exception handling
        #Clock.schedule_once(ExceptionTest, 30)

        global transitions, move_count, current_page, page1, page2, screenManager, menubox_x_pos, menubox_y_pos
        global menubox_width, menubox_height, ss_pictures, ss_captions

        Clock.unschedule(self.startup)
        if ss.debug_enabled: logger.warning('startup: Beginning startup processing @ ' + str(datetime.now())[0:19])

        if ss.dst_enabled: config_dst()
        mixer.music.load(ss.local_ringtones + 'sirius.ogg')
        mixer.music.play()

        if ss.sync_interval != 0:   # Case when Google deprecates API, skip init_vars and load local configuration.
            init_vars(True)
        else:
            setup_system()
        sync_pix()
        self.move_count = 0
        self.page1.source = ss_data_path + 'pix/blank.jpg'
        self.page1.source = ss_pictures[0]
        self.page2.source = ss_data_path + 'pix/blank.jpg'
        self.page2.source = ss_pictures[1]

        current_page = self.page1
        current_page.background.scale = ss.scale_start

        anim = Animation(center=ss.display_center, d=0) + Animation(scale=float(ss.scale_end), duration=int(ss.slide_scale_timing), center=ss.display_center)
        anim.start(self.page1.background)

    # Display the Captions box on pages - Always create the canvas for majority usage.

        ss.caption1_content = BoxLayout(orientation='vertical', padding=20, spacing=20, size_hint=(None, None), width=ss.captions_width, center_y = ss.captions_bottom_y + (ss.captions_height/2)) 

        with ss.caption1_content.canvas:        # the values below are setup in sync_frame_vars.
            Color(ss.captions_clut_bg[0], ss.captions_clut_bg[1], ss.captions_clut_bg[2], ss.captions_opacity)
            Rectangle(pos=(0, ss.captions_bottom_y), size=(ss.captions_width, ss.captions_height))

        current_caption = html.unescape(ss_captions[0])
        current_caption = ss_utils.caption_markup(current_caption, ss.captions_font, ss.fonts_dir)
        ss.caption1_label = Label(text = '[color=#' + ss.captions_clut_fg[3] + ']' + current_caption + '[/color]', font_name=ss.captions_font_file, markup=True, font_size=ss.captions_fontpixel, halign='center', valign='center')
        ss.caption1_label.bind(size=ss.caption1_label.setter('text_size'))
        ss.caption1_content.add_widget(ss.caption1_label)
        
        ss.caption2_content = BoxLayout(orientation='vertical', padding=20, spacing=20, size_hint=(None, None), width=ss.captions_width, center_y = ss.captions_bottom_y + (ss.captions_height/2))

        # the values below are setup above.
        with ss.caption2_content.canvas: 
            Color(ss.captions_clut_bg[0], ss.captions_clut_bg[1], ss.captions_clut_bg[2], ss.captions_opacity)
            Rectangle(pos=(0, ss.captions_bottom_y), size=(ss.captions_width, ss.captions_height))
                    
        current_caption = html.unescape(ss_captions[1])
        current_caption = ss_utils.caption_markup(current_caption, ss.captions_font, ss.fonts_dir)
        ss.caption2_label = Label(text = '[color=#' + ss.captions_clut_fg[3] + ']' + current_caption + '[/color]', font_name=ss.captions_font_file, markup=True, font_size=ss.captions_fontpixel, halign='center', valign='center')
        ss.caption2_label.bind(size=ss.caption2_label.setter('text_size'))
        ss.caption2_content.add_widget(ss.caption2_label)

        if ss.captions_enabled:
            if len(ss_captions[0]) != 0:  
                self.page1.add_widget(ss.caption1_content)

            # Display the Captions box on page2
            if len(ss_captions[1]) != 0:  
                self.page2.add_widget(ss.caption2_content)
            ss.captions_displayed = True
            
# End of Captions box -----------
# Create the digitalclock box on pages

        ss.digitalclock1_content = BoxLayout(orientation='vertical', padding=2, spacing=2, size_hint=(None, None), width=ss.digitalclock_width, center_y = ss.digitalclock_bottom_y+(ss.digitalclock_height/2)) 

        with ss.digitalclock1_content.canvas:        # the values below are setup in sync_frame_vars.
            Color(ss.digitalclock_clut_bg[0], ss.digitalclock_clut_bg[1], ss.digitalclock_clut_bg[2], ss.digitalclock_opacity)
            Rectangle(pos=(0, ss.digitalclock_bottom_y), size=(ss.digitalclock_width, ss.digitalclock_height))

        dt = datetime.now()
        if platform == 'android':   # Handle Android display bug - doesn't handle omitting leading zero (0) in date/time (minus sign does not work). This will be a problem when date format chages.
            digitalclock_date = dt.strftime("%d %B %Y")
            if digitalclock_date[0] == '0':     # Strip leading zero in date
                digitalclock_date = digitalclock_date[1:15]
            digitalclock_date = str(digitalclock_date)
            digitalclock_time = dt.strftime("%I:%M %p")
            if digitalclock_time[0] == '0':     # Strip leading zero in time
                digitalclock_time = digitalclock_time[1:8]
            digitalclock_time = str(digitalclock_time)
            digitalclock_string = '[color=#' + str(color_lut[ss.digitalclock_day_fontcolor][3]) + ']' + str(dt.strftime("%A")) + '[/color][color=#' + str(color_lut[ss.digitalclock_date_fontcolor][3]) + ']' +' - ' + digitalclock_date + ' - [/color][color=#' + str(color_lut[ss.digitalclock_time_fontcolor][3]) + ']' + digitalclock_time + '[/color]'
        else:                       # CANNOT Handle Linux alignment problem when 'y' in day strings but not month and time. Has to be only one color or bug.
            digitalclock_string = '[color=#' + str(color_lut[ss.digitalclock_day_fontcolor][3]) + ']' + str(dt.strftime("%A")) + ' - ' + str(dt.strftime("%-d %B %Y")) + ' - ' + str(dt.strftime("%-I:%M %p"))
        ss.digitalclock1_label = Label(text = digitalclock_string, font_name = ss.digitalclock_font_file, markup=True, font_size=ss.digitalclock_fontpixel, halign='center', valign='center')
        ss.digitalclock1_label.bind(size=ss.digitalclock1_label.setter('text_size'))
        ss.digitalclock1_content.add_widget(ss.digitalclock1_label)
        
        ss.digitalclock2_content = BoxLayout(orientation='vertical', padding=2, spacing=2, size_hint=(None, None), width=ss.digitalclock_width, center_y = ss.digitalclock_bottom_y+(ss.digitalclock_height/2)) 

        with ss.digitalclock2_content.canvas: 
            Color(ss.digitalclock_clut_bg[0], ss.digitalclock_clut_bg[1], ss.digitalclock_clut_bg[2], ss.digitalclock_opacity)
            Rectangle(pos=(0, ss.digitalclock_bottom_y), size=(ss.digitalclock_width, ss.digitalclock_height))

        ss.digitalclock2_label = Label(text = digitalclock_string, font_name = ss.digitalclock_font_file, markup=True, font_size=ss.digitalclock_fontpixel, halign='center', valign='center')
        ss.digitalclock2_label.bind(size=ss.digitalclock2_label.setter('text_size'))
        ss.digitalclock2_content.add_widget(ss.digitalclock2_label)

#   Display clock when enabled:
        if ss.digitalclock_enabled:
            self.page1.add_widget(ss.digitalclock1_content)
            self.page2.add_widget(ss.digitalclock2_content)
            ss.digitalclock_displayed = True
# End of digitalclock box ----------- 

        if ss.outside_info_enabled: 
# Display the outside_temp box on pages
            try:
                setup_outside_info()
                res=requests.get('https://api.openweathermap.org/data/2.5/onecall?' + ss.lat_lon + '&exclude=hourly,daily&appid=' + ss.OWM_id + '&units=imperial')
                outside_temp_str = '[color=#' + str(color_lut[ss.outside_info_fontcolor][3]) + '] ' + str(round(res.json()['current']['temp'])) + '°F' + '[/color]'
                outside_humidity_str = '[color=#' + str(color_lut[ss.outside_info_fontcolor][3]) + '] ' + str(round(res.json()['current']['humidity'])) + '%' + '[/color]'
            except Exception as err:
                logger.error('startup: Failed to receive openweathermap values, exception: ' + str(err))
                outside_temp_str = '[color=#' + str(color_lut[ss.outside_info_fontcolor][3]) + '] ??°F' + '[/color]'
                outside_humidity_str = '[color=#' + str(color_lut[ss.outside_info_fontcolor][3]) + '] ??%' + '[/color]'
                icon_url = ''
                pass

            ss.outside_temp1_content = BoxLayout(orientation='vertical', padding=1, spacing=1, size_hint=(None, None), width=ss.outside_info_width, center_y = ss.outside_info_bottom_y+(ss.outside_info_height/2)) 
            with ss.outside_temp1_content.canvas:
                Color(ss.outside_info_clut_bg[0], ss.outside_info_clut_bg[1], ss.outside_info_clut_bg[2], ss.outside_info_opacity)
                Rectangle(pos=(0, ss.outside_info_bottom_y), size=(ss.outside_info_width, ss.outside_info_height))

            ss.outside_temp1_label = Label(text = outside_temp_str, font_name = ss.outside_info_font_file, markup=True, font_size=ss.outside_info_fontpixel, halign='left', valign='center')
            ss.outside_temp1_label.bind(size=ss.outside_temp1_label.setter('text_size'))
            ss.outside_temp1_content.add_widget(ss.outside_temp1_label)

            ss.outside_temp2_content = BoxLayout(orientation='vertical', padding=1, spacing=1, size_hint=(None, None), width=ss.outside_info_width, center_y = ss.outside_info_bottom_y+(ss.outside_info_height/2)) 
            with ss.outside_temp2_content.canvas: 
                Color(ss.outside_info_clut_bg[0], ss.outside_info_clut_bg[1], ss.outside_info_clut_bg[2], ss.outside_info_opacity)
                Rectangle(pos=(0, ss.outside_info_bottom_y), size=(ss.outside_info_width, ss.outside_info_height))

            ss.outside_temp2_label = Label(text = outside_temp_str, font_name = ss.outside_info_font_file, markup=True, font_size=ss.outside_info_fontpixel, halign='left', valign='center')
            ss.outside_temp2_label.bind(size=ss.outside_temp2_label.setter('text_size'))
            ss.outside_temp2_content.add_widget(ss.outside_temp2_label)

#			Display the Humidity on pages hard coded with display size

            ss.outside_humidity1_content = BoxLayout(orientation='vertical', padding=1, spacing=1, size_hint=(None, None), width=ss.outside_info_width, center_x = ss.outside_humidity_x-10, center_y = ss.outside_info_bottom_y+(ss.outside_info_height/2)) 
            with ss.outside_humidity1_content.canvas:
                Color(ss.outside_info_clut_bg[0], ss.outside_info_clut_bg[1], ss.outside_info_clut_bg[2], ss.outside_info_opacity)
                Rectangle(pos=(ss.display_width-ss.outside_info_width, ss.outside_info_bottom_y), size=(ss.outside_info_width, ss.outside_info_height))

            ss.outside_humidity1_label = Label(text = outside_humidity_str, font_name = ss.outside_info_font_file, markup=True, font_size=ss.outside_info_fontpixel, halign='left', valign='center')
            ss.outside_humidity1_label.bind(size=ss.outside_humidity1_label.setter('text_size'))
            ss.outside_humidity1_content.add_widget(ss.outside_humidity1_label)

            ss.outside_humidity2_content = BoxLayout(orientation='vertical', padding=1, spacing=1, size_hint=(None, None), width=ss.outside_info_width, center_x = ss.outside_humidity_x-10, center_y = ss.outside_info_bottom_y+(ss.outside_info_height/2)) 
            with ss.outside_humidity2_content.canvas: 
                Color(ss.outside_info_clut_bg[0], ss.outside_info_clut_bg[1], ss.outside_info_clut_bg[2], ss.outside_info_opacity)
                Rectangle(pos=(ss.display_width-ss.outside_info_width, ss.outside_info_bottom_y), size=(ss.outside_info_width, ss.outside_info_height))

            ss.outside_humidity2_label = Label(text = outside_humidity_str, font_name = ss.outside_info_font_file, markup=True, font_size=ss.outside_info_fontpixel, halign='left', valign='center')
            ss.outside_humidity2_label.bind(size=ss.outside_humidity2_label.setter('text_size'))
            ss.outside_humidity2_content.add_widget(ss.outside_humidity2_label)

            self.page1.add_widget(ss.outside_humidity1_content)
            self.page2.add_widget(ss.outside_humidity2_content)
            self.page1.add_widget(ss.outside_temp1_content)
            self.page2.add_widget(ss.outside_temp2_content)

            ss.outside_info_displayed = True

# End of weather_icon and outside_temp box ----------- 

# Work in progress below - testing position is good on page1 here, need to add page2 and handle removing when connection back up.
#        ss.nointernet_icon_y = 40
#        ss.nointernet_icon_x = ss.display_width - 50
#        ss.nointernet_icon_content = BoxLayout(orientation='vertical', padding=0, spacing=0, size_hint=(None, None), width=60, height=60, center_x = ss.nointernet_icon_x, center_y = ss.nointernet_icon_y) 
#        ss.nointernet_icon_content.add_widget(Image_source(source=ss_data_path + 'pix/wifi-disconnect.png'))
#        self.page1.add_widget(ss.nointernet_icon_content)
#        self.page2.add_widget(ss.nointernet_icon_content)

        # Control coordinates are for the secret control access to configuration
        # features and nav buttons to slide pictures, below are left/right buttons,
        # control right area 200x200 centered top, sleep in middle.
        ss.slide_left = [0, 100, 200, ss.display_height-100]
        ss.slide_right = [ss.display_width-200, 100, ss.display_width, ss.display_height-100]
        ss.touch_center = [(ss.display_width/2)-100, (ss.display_height/2)-100, (ss.display_width/2)+100, (ss.display_height/2)+100]

        update_gc_mem()         # Garbage collect and log memory
        Clock.schedule_once(self.next, 10)
        if ss.sync_interval != 0:               # Only start the Loader if Google hasn't bricked this app...ss.sync_interval = 0
            Clock.schedule_once(SS_Loader.check_server, ss.sync_interval)
            if ss.debug_enabled: logger.warning('startup: SS_Loader.check_server started @ ' + str(datetime.now())[0:19] + '.')
        else:
            if ss.debug_enabled: logger.error('startup: SS_Loader.check_server NOT started due to 0 sync_interval.')

        ss.sync_start_time = datetime.now()
        Clock.schedule_once(SS_Sync.check_time, 3)
        if ss.debug_enabled: logger.warning('startup: Finished startup processing and started SS_Sync.check_time @ ' + str(datetime.now())[0:19] + '.')
        return

#  End of startup() routine
    # ----------------------------------------------
    def next(self,*largs):
    # ----------------------------------------------
    # This routine is used when frame is not asleep; however, it still handles
    # returning from paused mode, after pause times out. This is part 2 of the
    # app start to load, display, and animate the slideshow going forward.  App
    # will cycle through this routine regularly based on picture display times
    # and while awake, showing slide pictures.

        global page1, page2, anim, current_page, screenManager, ss_pictures, transitions, digitalclock2, digitalclock1

        Clock.unschedule(self.next)

        if ss.downloading:    # don't do anything while downloading in process...
            if ss.debug_enabled: logger.warning('NEXT: Downloading Frame updates, exiting entrance.')
            Clock.schedule_once(self.next, ss.slide_duration)
            return

        if ss.frame_sleeping:   # If next gets called after starting during sleep time, setup wake time and go to sleep.
            if ss.debug_enabled: logger.warning('NEXT: check.sleeping(), exiting this entrance and possibly returning in a second.')
            ss.frame_awoken = True      # This needs to be here in case new album downloaded and frame_awoken gets set to False.
            self.check_sleeping()
            return

        ss.nexting = True   # set flag for check_server to skip while processing next routine

        if ss.app_paused:
            ss.app_paused = False
            if ss.debug_enabled: logger.warning('NEXT: ---> PAUSED App Restarted: ' + str(datetime.now())[0:19])

        ss.sync_counter += 1    # This timer is used to check periodic events like checking the server for connectivity and new feeds.
        if ss.sync_counter == ss.sync_number:   # This code is currently not being used. Needed for connectivity check.
            ss.sync_counter = 0

#        ss.sync_start_time += 1                  # The sync_start_time is used to determine when to garbage collect based on number of slides displayed.
#        if ss.sync_start_time >= ss.gc_number:   # Currently, this timer is set for 15 minutes and also uses that time before updating the weather info.
#            update_gc_mem()
#            if ss.outside_info_enabled: self.weather_update()

# This section sets up the Next picture image to display and transition.

        if(self.screenManager.current == 'page1'):
            next = 'page2'
            current_page = self.page2
            trans_toggle = 0
        else:
            next = 'page1'
            current_page = self.page1
            trans_toggle = 1

        ss.slideshow_index += 1     # reset photo index back to zero after all photos in list displayed
        if ss.slideshow_index >= len(ss_pictures):
            ss.slideshow_index = 0
            if ss.random_enabled:
                randomize_slides()
        current_page.source = ss_pictures[ss.slideshow_index]
        if ss.debug_enabled: logger.warning('NEXT: Loaded Picture: ' + str(ss_pictures[ss.slideshow_index]) + ' @ ' + str(datetime.now())[0:19])

# Setup next caption when enabled - user can change all values

        if ss.captions_enabled:
            ss.captions_displayed = True
            if next == 'page1':     # update captions with any new changes.
                self.page1.remove_widget(ss.caption1_content)
                ss.caption1_content.remove_widget(ss.caption1_label)
                current_caption = html.unescape(ss_captions[ss.slideshow_index])
                current_caption = ss_utils.caption_markup(current_caption, ss.captions_font, ss.fonts_dir)
                ss.caption1_label = Label(text= '[color=#' + ss.captions_clut_fg[3] + ']' + current_caption + '[/color]', font_name=ss.captions_font_file, markup=True, font_size=ss.captions_fontpixel, valign='bottom')
                if ss.captions_changed:   # Handle both pages when captions changed
                    ss.captions_changed = False
                    self.page2.remove_widget(ss.caption2_content)
                    ss.caption2_content.remove_widget(ss.caption2_label)
                    ss.caption1_content = BoxLayout(orientation='vertical', padding=20, spacing=20, size_hint=(None, None), width=ss.captions_width, center_y = ss.captions_bottom_y+(ss.captions_height/2)) 
                    with ss.caption1_content.canvas:        # the values below are setup in sync_frame_vars.
                        Color(ss.captions_clut_bg[0], ss.captions_clut_bg[1], ss.captions_clut_bg[2], ss.captions_opacity)
                        Rectangle(pos=(0, ss.captions_bottom_y), size=(ss.captions_width, ss.captions_height))

                    ss.caption2_content = BoxLayout(orientation='vertical', padding=20, spacing=20, size_hint=(None, None), width=ss.captions_width, center_y = ss.captions_bottom_y+(ss.captions_height/2)) 
                    with ss.caption2_content.canvas:        # the values below are setup in sync_frame_vars.
                        Color(ss.captions_clut_bg[0], ss.captions_clut_bg[1], ss.captions_clut_bg[2], ss.captions_opacity)
                        Rectangle(pos=(0, ss.captions_bottom_y), size=(ss.captions_width, ss.captions_height))

                if len(ss_captions[ss.slideshow_index]) != 0:  
                    ss.caption1_content.add_widget(ss.caption1_label)
                    self.page1.add_widget(ss.caption1_content)
                    
            else:   # Next: Page2
                self.page2.remove_widget(ss.caption2_content)
                ss.caption2_content.remove_widget(ss.caption2_label)
                current_caption = html.unescape(ss_captions[ss.slideshow_index])
                current_caption = ss_utils.caption_markup(current_caption, ss.captions_font, ss.fonts_dir)
                ss.caption2_label = Label(text= '[color=#' + ss.captions_clut_fg[3] + ']' + current_caption + '[/color]', font_name=ss.captions_font_file, markup=True, font_size=ss.captions_fontpixel, valign='center')
                if ss.captions_changed:   # Handle both pages when captions changed
                    ss.captions_changed = False
                    self.page1.remove_widget(ss.caption1_content)
                    ss.caption1_content.remove_widget(ss.caption1_label)
                    ss.caption2_content = BoxLayout(orientation='vertical', padding=20, spacing=20, size_hint=(None, None), width=ss.captions_width, center_y = ss.captions_bottom_y+(ss.captions_height/2)) 
                    with ss.caption2_content.canvas:        # the values below are setup in sync_frame_vars.
                        Color(ss.captions_clut_bg[0], ss.captions_clut_bg[1], ss.captions_clut_bg[2], ss.captions_opacity)
                        Rectangle(pos=(0, ss.captions_bottom_y), size=(ss.captions_width, ss.captions_height))

                    ss.caption1_content = BoxLayout(orientation='vertical', padding=20, spacing=20, size_hint=(None, None), width=ss.captions_width, center_y = ss.captions_bottom_y+(ss.captions_height/2)) 
                    with ss.caption1_content.canvas:        # the values below are setup in sync_frame_vars.
                        Color(ss.captions_clut_bg[0], ss.captions_clut_bg[1], ss.captions_clut_bg[2], ss.captions_opacity)
                        Rectangle(pos=(0, ss.captions_bottom_y), size=(ss.captions_width, ss.captions_height))

                if len(ss_captions[ss.slideshow_index]) != 0:  
                    ss.caption2_content.add_widget(ss.caption2_label)
                    self.page2.add_widget(ss.caption2_content)

        elif ss.captions_changed:  # if captions turned off, clear widgets
            if ss.debug_enabled: logger.warning('NEXT: captions_changed == ' + str(ss.captions_changed) + ' and captions_enabled == ' + str(ss.captions_enabled))
            if ss.captions_displayed:
                self.page1.remove_widget(ss.caption1_content)
                self.page2.remove_widget(ss.caption2_content)
            ss.captions_changed = False
            ss.captions_displayed = False

        if ss.digitalclock_enabled: 
            self.clock_update()
            ss.digitalclock_changed = False
        elif ss.digitalclock_changed and not ss.digitalclock_enabled:  # if captions turned off, clear widgets
            if ss.debug_enabled: logger.warning('NEXT: digitalclock_changed == ' + str(ss.digitalclock_changed) + ' and digitalclock_enabled == ' + str(ss.digitalclock_enabled))
            if ss.digitalclock_displayed:
                self.page1.remove_widget(ss.digitalclock1_content)
                self.page2.remove_widget(ss.digitalclock2_content)
            ss.digitalclock_changed = False
            ss.digitalclock_displayed = False

        if ss.outside_info_enabled and ss.outside_info_changed: 
            if ss.debug_enabled: logger.warning('NEXT: outside_info_changed == ' + str(ss.outside_info_changed) + ' and outside_info_enabled == ' + str(ss.outside_info_enabled))
            self.weather_update()
            ss.outside_info_changed = False
        elif not ss.outside_info_enabled and ss.outside_info_changed:  # if weather info turned off, clear widgets
            if ss.debug_enabled: logger.warning('NEXT: outside_info_changed == ' + str(ss.outside_info_changed) + ' and outside_info_enabled == ' + str(ss.outside_info_enabled))
            if ss.outside_info_displayed:
                logger.info('NEXT: page1.remove_widget(ss.outside_temp1_content)')
                self.page1.remove_widget(ss.outside_temp1_content)
                logger.info('NEXT: page1.remove_widget(ss.outside_temp2_content)')
                self.page1.remove_widget(ss.outside_temp2_content)
                logger.info('NEXT: page1.remove_widget(ss.outside_humidity1_content)')
                self.page1.remove_widget(ss.outside_humidity1_content)
                logger.info('NEXT: page1.remove_widget(ss.outside_humidity2_content)')
                self.page1.remove_widget(ss.outside_humidity2_content)
                logger.info('NEXT: page2.remove_widget(ss.outside_temp1_content)')
                self.page2.remove_widget(ss.outside_temp1_content)
                logger.info('NEXT: page2.remove_widget(ss.outside_temp2_content)')
                self.page2.remove_widget(ss.outside_temp2_content)
                logger.info('NEXT: page2.remove_widget(ss.outside_humidity1_content)')
                self.page2.remove_widget(ss.outside_humidity1_content)
                logger.info('NEXT: page2.remove_widget(ss.outside_humidity2_content)')
                self.page2.remove_widget(ss.outside_humidity2_content)
            ss.outside_info_changed = False
            ss.outside_info_displayed = False

        if ss.transition_enabled:
            if ss.transition_type == 99:  # Random All Transitions
                tmp_trans = transitions_all[random.randint(0, len(transitions_all) -1)].split(',')  # get random index into transitions list.
                tmp_type = int(tmp_trans[0])  # separate values for screen manager setup below.
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            elif ss.transition_type == 98:  # Random Swipe Transitions
                tmp_trans = transitions_swipe[random.randint(0, len(transitions_swipe) -1)].split(',')
                tmp_type = int(tmp_trans[0])  
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            elif ss.transition_type == 97:  # Random Fade Transitions
                tmp_trans = transitions_fade[random.randint(0, len(transitions_fade) -1)].split(',')
                tmp_type = int(tmp_trans[0])  
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            elif ss.transition_type == 96:  # Random Slide Transitions: Top/Bottom/Left/Right
                tmp_trans = transitions_slide[random.randint(0, len(transitions_slide) -1)].split(',')
                tmp_type = int(tmp_trans[0])  
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            elif ss.transition_type == 95:  # Random Rotate Transitions: Top/Bottom/Left/Right
                tmp_trans = transitions_rotate[random.randint(0, len(transitions_rotate) -1)].split(',')
                tmp_type = int(tmp_trans[0])  
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            elif ss.transition_type == 94:
                tmp_trans = transitions_slidelr[trans_toggle].split(',')  # get toggle (set in NEXT) index into transitions list.
                tmp_type = int(tmp_trans[0])  
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            elif ss.transition_type == 93:
                tmp_trans = transitions_slidetb[trans_toggle].split(',') 
                tmp_type = int(tmp_trans[0])  
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            elif ss.transition_type == 92:
                tmp_trans = transitions_rotatelr[trans_toggle].split(',') 
                tmp_type = int(tmp_trans[0])  
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            elif ss.transition_type == 91:
                tmp_trans = transitions_rotatetb[trans_toggle].split(',') 
                tmp_type = int(tmp_trans[0])  
                tmp_duration = tmp_trans[1]
                tmp_direction = tmp_trans[2]
            else:
                tmp_type = ss.transition_type
                tmp_duration = ss.transition_duration
                tmp_direction = ss.transition_direction
            if tmp_type == 1:
                self.screenManager.transition = FadeTransition(duration=float(tmp_duration))
            if tmp_type == 2:
                self.screenManager.transition = BlurTransition(duration=float(tmp_duration))
            if tmp_type == 3:
                self.screenManager.transition = PixelTransition(duration=float(tmp_duration))
            if tmp_type == 4:
                self.screenManager.transition = RippleTransition(duration=float(tmp_duration))
            if tmp_type == 5:
                if tmp_direction == 'None':
                    self.screenManager.transition = RotateTransition(duration=0)
                else:
                    self.screenManager.transition = RotateTransition(duration=float(tmp_duration),direction=str(tmp_direction))
            if tmp_type == 6:
                if tmp_direction == 'None':
                    self.screenManager.transition = SlideTransition(duration=0)
                else:
                    self.screenManager.transition = SlideTransition(duration=float(tmp_duration),direction=str(tmp_direction))
        else:
            self.screenManager.transition = FadeTransition(duration=0)

        current_page.background.scale = ss.scale_start
        self.screenManager.current = next

        anim = Animation(center=ss.display_center, d=0) + Animation(scale=float(ss.scale_end), duration=int(ss.slide_scale_timing), center=ss.display_center)
        anim.start(current_page.background)
        
## SLEEP PROCESSING: [This can never happen since it returns at the beginnig of this NEXT routine.]
#        if ss.frame_sleeping:    # If frame was asleep and still asleep, then leave it awake for awake_time_pause amount of time defined above.
#            if ss.debug_enabled: logger.warning('NEXT-sleeping: frame_sleeping=' + str(ss.frame_sleeping) + ' @ ' + str(datetime.now())[0:19])
#            ss.frame_awoken = True
#            ss.nexting = False   # clear flag for check_server to skip while processing next routine
#            Clock.schedule_once(this_app.wakeup, ss.awake_time_pause)

# First use of sleep time set to call wakeup for original end_sleep_datetime ====================================================================
# This is barely going to happen during the NEXT routine but will be handled mostly during SS_Sync.check_time:
        if ss.sleep_enabled and datetime.now() > ss.start_sleep_datetime and datetime.now() < ss.end_sleep_datetime:
            update_gc_mem()
            blank_screen()
            ss.frame_sleeping = True
            ss.frame_awoken = False
            ss.nexting = False   # clear flag for check_server to skip while processing next routine
            ss.sleep_seconds = (ss.end_sleep_datetime - datetime.now()).seconds     # Set seconds based on current time due to display duration.
            logger.info('NEXT: Going to SLEEP until: end_sleep_datetime=' + str(ss.end_sleep_datetime) + ', starting at @ ' + str(datetime.now())[0:19] + ', sleep_seconds = ' + str(ss.sleep_seconds))
            Clock.schedule_once(this_app.wakeup, ss.sleep_seconds + 1)

# Otherwise, keep the slideshow rolling... ======================================================================================================
        else: 
            ss.nexting = False   # clear flag for check_server to skip while processing next routine
            Clock.schedule_once(self.next, ss.slide_duration)

# End of NEXT routine

    # ----------------------------------------------
    def clock_page1_update(self):
    # ----------------------------------------------
        dt = datetime.now()
        if platform == 'android':   # Handle Android display bug: -d and -I.
            digitalclock_date = dt.strftime("%d %B %Y")
            if digitalclock_date[0] == '0':     # Strip leading zero in date
                digitalclock_date = digitalclock_date[1:15]
            digitalclock_date = str(digitalclock_date)
            digitalclock_time = dt.strftime("%I:%M %p")
            if digitalclock_time[0] == '0':     # Strip leading zero in time
                digitalclock_time = digitalclock_time[1:8]
            digitalclock_time = str(digitalclock_time)
            digitalclock_string = '[color=#' + str(color_lut[ss.digitalclock_day_fontcolor][3]) + ']' + str(dt.strftime("%A")) + '[/color][color=#' + str(color_lut[ss.digitalclock_date_fontcolor][3]) + ']' +' - ' + digitalclock_date + ' - [/color][color=#' + str(color_lut[ss.digitalclock_time_fontcolor][3]) + ']' + digitalclock_time + '[/color]'
        else:
            digitalclock_string = '[color=#' + str(color_lut[ss.digitalclock_day_fontcolor][3]) + ']' + str(dt.strftime("%A")) + '[/color][color=#' + str(color_lut[ss.digitalclock_date_fontcolor][3]) + ']' +' - ' + str(dt.strftime("%-d %B %Y")) + ' - [/color][color=#' + str(color_lut[ss.digitalclock_time_fontcolor][3]) + ']' + str(dt.strftime("%-I:%M %p") + '[/color]')
#            digitalclock_string = '[color=#' + str(color_lut[ss.digitalclock_day_fontcolor][3]) + ']' + str(dt.strftime("%A")) + ' - ' + str(dt.strftime("%-d %B %Y")) + ' - ' + str(dt.strftime("%-I:%M %p"))
        if ss.outside_info_displayed:               # Remove weather info before adding back after banner displayed
            self.page1.remove_widget(ss.outside_temp1_content)
            self.page1.remove_widget(ss.outside_humidity1_content)
        if ss.digitalclock_displayed:               # Remove clock info before adding back after banner displayed
            self.page1.remove_widget(ss.digitalclock1_content)
            ss.digitalclock1_content.remove_widget(ss.digitalclock1_label)
            ss.digitalclock_displayed = False
        ss.digitalclock1_content = BoxLayout(orientation='vertical', padding=2, spacing=2, size_hint=(None, None), width=ss.digitalclock_width, center_y = ss.digitalclock_bottom_y+(ss.digitalclock_height/2)) 
        with ss.digitalclock1_content.canvas: 
            Color(ss.digitalclock_clut_bg[0], ss.digitalclock_clut_bg[1], ss.digitalclock_clut_bg[2], ss.digitalclock_opacity)
            Rectangle(pos=(0, ss.digitalclock_bottom_y), size=(ss.digitalclock_width, ss.digitalclock_height))
        ss.digitalclock1_label = Label(text = digitalclock_string, font_name = ss.digitalclock_font_file, markup=True, font_size=ss.digitalclock_fontpixel, halign='center', valign='center')
        ss.digitalclock1_label.bind(size=ss.digitalclock1_label.setter('text_size'))
        ss.digitalclock1_content.add_widget(ss.digitalclock1_label)
        self.page1.add_widget(ss.digitalclock1_content)
        ss.digitalclock_displayed = True
        if ss.outside_info_displayed:               # Remove weather info before adding back after banner displayed
            self.page1.add_widget(ss.outside_temp1_content)
            self.page1.add_widget(ss.outside_humidity1_content)

    # ----------------------------------------------
    def clock_page2_update(self):
    # ----------------------------------------------
        dt = datetime.now()
        if platform == 'android':   # Handle Android display bug.
            digitalclock_date = dt.strftime("%d %B %Y")
            if digitalclock_date[0] == '0':     # Strip leading zero in date
                digitalclock_date = digitalclock_date[1:15]
            digitalclock_date = str(digitalclock_date)
            digitalclock_time = dt.strftime("%I:%M %p")
            if digitalclock_time[0] == '0':     # Strip leading zero in time
                digitalclock_time = digitalclock_time[1:8]
            digitalclock_time = str(digitalclock_time)
            digitalclock_string = '[color=#' + str(color_lut[ss.digitalclock_day_fontcolor][3]) + ']' + str(dt.strftime("%A")) + '[/color][color=#' + str(color_lut[ss.digitalclock_date_fontcolor][3]) + ']' +' - ' + digitalclock_date + ' - [/color][color=#' + str(color_lut[ss.digitalclock_time_fontcolor][3]) + ']' + digitalclock_time + '[/color]'
        else:
#            digitalclock_string = '[color=#' + str(color_lut[ss.digitalclock_day_fontcolor][3]) + ']' + str(dt.strftime("%A")) + ' - ' + str(dt.strftime("%-d %B %Y")) + ' - ' + str(dt.strftime("%-I:%M %p"))
            digitalclock_string = '[color=#' + str(color_lut[ss.digitalclock_day_fontcolor][3]) + ']' + str(dt.strftime("%A")) + '[/color][color=#' + str(color_lut[ss.digitalclock_date_fontcolor][3]) + ']' +' - ' + str(dt.strftime("%-d %B %Y")) + ' - [/color][color=#' + str(color_lut[ss.digitalclock_time_fontcolor][3]) + ']' + str(dt.strftime("%-I:%M %p") + '[/color]')
        if ss.outside_info_displayed:               # Remove weather info before adding back after banner displayed
            self.page2.remove_widget(ss.outside_temp2_content)  
            self.page2.remove_widget(ss.outside_humidity2_content)
        if ss.digitalclock_displayed:               # Remove clock info before adding back after banner displayed
            self.page2.remove_widget(ss.digitalclock2_content)
            ss.digitalclock2_content.remove_widget(ss.digitalclock2_label)
            ss.digitalclock_displayed = False
        ss.digitalclock2_content = BoxLayout(orientation='vertical', padding=2, spacing=2, size_hint=(None, None), width=ss.digitalclock_width, center_y = ss.digitalclock_bottom_y+(ss.digitalclock_height/2)) 
        with ss.digitalclock2_content.canvas: 
            Color(ss.digitalclock_clut_bg[0], ss.digitalclock_clut_bg[1], ss.digitalclock_clut_bg[2], ss.digitalclock_opacity)
            Rectangle(pos=(0, ss.digitalclock_bottom_y), size=(ss.digitalclock_width, ss.digitalclock_height))
        ss.digitalclock2_label = Label(text = digitalclock_string, font_name = ss.digitalclock_font_file, markup=True, font_size=ss.digitalclock_fontpixel, halign='center', valign='center')
        ss.digitalclock2_label.bind(size=ss.digitalclock2_label.setter('text_size'))
        ss.digitalclock2_content.add_widget(ss.digitalclock2_label)
        self.page2.add_widget(ss.digitalclock2_content)
        ss.digitalclock_displayed = True
        if ss.outside_info_displayed:           # this_app.weather_update()
            self.page2.add_widget(ss.outside_temp2_content)
            self.page2.add_widget(ss.outside_humidity2_content)

    # ----------------------------------------------
    def clock_update(self):
    # ----------------------------------------------

        if self.screenManager.current=='page1' and not ss.frame_sleeping:
            self.clock_page2_update()
        elif self.screenManager.current=='page2' and not ss.frame_sleeping:
            self.clock_page1_update()
        elif self.screenManager.current=='page1' and ss.frame_sleeping:
            self.clock_page1_update()
        elif self.screenManager.current=='page2' and ss.frame_sleeping:
            self.clock_page2_update()

    # ----------------------------------------------
    def weather_update(self):
    # ----------------------------------------------
        global screenManager

        try:
            res=requests.get('https://api.openweathermap.org/data/2.5/onecall?' + ss.lat_lon + '&exclude=hourly,daily&appid=' + ss.OWM_id + '&units=imperial')
            outside_temp_str = '[color=#' + str(color_lut[ss.outside_info_fontcolor][3]) + '] ' + str(round(res.json()['current']['temp'])) + '°F' + '[/color]'
            outside_humidity_str = '[color=#' + str(color_lut[ss.outside_info_fontcolor][3]) + '] ' + str(round(res.json()['current']['humidity'])) + '%' + '[/color]'
            icon_data = res.json()['current']['weather'][0]['icon']
            icon_url = 'http://openweathermap.org/img/wn/' + str(icon_data) + '@2x.png'
        except Exception as err:
            logger.error('weather_update: Failed to receive openweathermap values, exception: ' + str(err))
            outside_temp_str = '[color=#' + str(color_lut[ss.outside_info_fontcolor][3]) + '] ??°F' + '[/color]'
            outside_humidity_str = '[color=#' + str(color_lut[ss.outside_info_fontcolor][3]) + '] ??%' + '[/color]'
            icon_url = ''
            pass

        if ss.outside_info_displayed:
            self.page2.remove_widget(ss.outside_temp2_content)
            ss.outside_temp2_content.remove_widget(ss.outside_temp2_label)
            self.page1.remove_widget(ss.outside_temp1_content)
            ss.outside_temp1_content.remove_widget(ss.outside_temp1_label)
            self.page2.remove_widget(ss.outside_humidity2_content)
            ss.outside_humidity2_content.remove_widget(ss.outside_humidity2_label)
            self.page1.remove_widget(ss.outside_humidity1_content)
            ss.outside_humidity1_content.remove_widget(ss.outside_humidity1_label)
            ss.outside_info_displayed = False
        try:
            self.page2.remove_widget(ss.outside_temp2_content)
        except Exception as err:
            logger.error('weather_update: outside_temp2_content err: ' + str(err))
            pass
        try:
            ss.outside_temp2_content.remove_widget(ss.outside_temp2_label)
        except Exception as err:
            logger.error('weather_update: outside_temp2_label err: ' + str(err))
            pass
        try:
            self.page1.remove_widget(ss.outside_temp1_content)
        except Exception as err:
            logger.error('weather_update: outside_temp1_content err: ' + str(err))
            pass
        try:
            ss.outside_temp1_content.remove_widget(ss.outside_temp1_label)
        except Exception as err:
            logger.error('weather_update: outside_temp1_label err: ' + str(err))
            pass
        try:
            self.page1.remove_widget(ss.outside_humidity1_content)
        except Exception as err:
            logger.error('weather_update: outside_humidity1_content err: ' + str(err))
            pass
        try:
            self.page2.remove_widget(ss.outside_humidity2_content)
        except Exception as err:
            logger.error('weather_update: outside_humidity2_content err: ' + str(err))
            pass

        ss.outside_temp1_content = BoxLayout(orientation='vertical', padding=1, spacing=1, size_hint=(None, None), width=ss.outside_info_width, center_y = ss.outside_info_bottom_y+(ss.outside_info_height/2)) 
        with ss.outside_temp1_content.canvas:
            Color(ss.outside_info_clut_bg[0], ss.outside_info_clut_bg[1], ss.outside_info_clut_bg[2], ss.outside_info_opacity)
            Rectangle(pos=(0, ss.outside_info_bottom_y), size=(ss.outside_info_width, ss.outside_info_height))
        ss.outside_temp1_label = Label(text = outside_temp_str, font_name = ss.outside_info_font_file, markup=True, font_size=ss.outside_info_fontpixel, halign='left', valign='center')
        ss.outside_temp1_label.bind(size=ss.outside_temp1_label.setter('text_size'))
        ss.outside_temp1_content.add_widget(ss.outside_temp1_label)

        ss.outside_temp2_content = BoxLayout(orientation='vertical', padding=1, spacing=1, size_hint=(None, None), width=ss.outside_info_width, center_y = ss.outside_info_bottom_y+(ss.outside_info_height/2)) 
        with ss.outside_temp2_content.canvas: 
            Color(ss.outside_info_clut_bg[0], ss.outside_info_clut_bg[1], ss.outside_info_clut_bg[2], ss.outside_info_opacity)
            Rectangle(pos=(0, ss.outside_info_bottom_y), size=(ss.outside_info_width, ss.outside_info_height))
        ss.outside_temp2_label = Label(text = outside_temp_str, font_name = ss.outside_info_font_file, markup=True, font_size=ss.outside_info_fontpixel, halign='left', valign='center')
        ss.outside_temp2_label.bind(size=ss.outside_temp2_label.setter('text_size'))
        ss.outside_temp2_content.add_widget(ss.outside_temp2_label)

        ss.outside_humidity1_content = BoxLayout(orientation='vertical', padding=1, spacing=1, size_hint=(None, None), width=ss.outside_info_width, center_x = ss.outside_humidity_x-5, center_y = ss.outside_info_bottom_y+(ss.outside_info_height/2)) 
        with ss.outside_humidity1_content.canvas:
            Color(ss.outside_info_clut_bg[0], ss.outside_info_clut_bg[1], ss.outside_info_clut_bg[2], ss.outside_info_opacity)
            Rectangle(pos=(ss.display_width-ss.outside_info_width, ss.outside_info_bottom_y), size=(ss.outside_info_width, ss.outside_info_height))

        ss.outside_humidity1_label = Label(text = outside_humidity_str, font_name = ss.outside_info_font_file, markup=True, font_size=ss.outside_info_fontpixel, halign='left', valign='center')
        ss.outside_humidity1_label.bind(size=ss.outside_humidity1_label.setter('text_size'))
        ss.outside_humidity1_content.add_widget(ss.outside_humidity1_label)

        ss.outside_humidity2_content = BoxLayout(orientation='vertical', padding=1, spacing=1, size_hint=(None, None), width=ss.outside_info_width, center_x = ss.outside_humidity_x-5, center_y = ss.outside_info_bottom_y+(ss.outside_info_height/2)) 
        with ss.outside_humidity2_content.canvas: 
            Color(ss.outside_info_clut_bg[0], ss.outside_info_clut_bg[1], ss.outside_info_clut_bg[2], ss.outside_info_opacity)
            Rectangle(pos=(ss.display_width-ss.outside_info_width, ss.outside_info_bottom_y), size=(ss.outside_info_width, ss.outside_info_height))

        ss.outside_humidity2_label = Label(text = outside_humidity_str, font_name = ss.outside_info_font_file, markup=True, font_size=ss.outside_info_fontpixel, halign='left', valign='center')
        ss.outside_humidity2_label.bind(size=ss.outside_humidity2_label.setter('text_size'))
        ss.outside_humidity2_content.add_widget(ss.outside_humidity2_label)

        self.page1.add_widget(ss.outside_temp1_content)
        self.page2.add_widget(ss.outside_temp2_content)
        self.page1.add_widget(ss.outside_humidity1_content)
        self.page2.add_widget(ss.outside_humidity2_content)

        ss.outside_info_displayed = True

    # ----------------------------------------------
    def check_sleeping(self,*largs):
    # ----------------------------------------------
    #   check_sleeping is only called when ss.frame_sleeping is True.
    #   This routine executes after user wakes the frame while in sleep mode.
    #   During this time, the user can touch the screen a second time to display a menu.
    #   On return from the menu, this routine is called to determine sleep operation, should the user reload config variables.
    #   If config values have changed that affects the sleep operations, this routine determines that using the loaded values. 
    
        Clock.unschedule(self.check_sleeping)
        logger.warning('check_sleeping: sleep_enabled=' + str(ss.sleep_enabled) + ', frame_awoken=' + str(ss.frame_awoken) + ', frame_sleeping=' + str(ss.frame_sleeping) + ', app_paused=' + str(ss.app_paused))

        # User disabled sleep and config reloaded.
        if not ss.sleep_enabled:
            logger.warning('check_sleeping: ---> Sleep Disabled during Sleep Mode @ ' + str(datetime.now())[0:19])
            Clock.schedule_once(self.next,1)    # go back to showing the photos
            ss.frame_awoken = False             # Turn off sleep mode flags
            ss.frame_sleeping = False
            return

        # Handle Sleep Start Time reset by user changes
        if ss.frame_sleeping and datetime.now() < ss.start_sleep_datetime:
            self.wakeup()
            logger.warning('check_sleeping: ---> Waking up from config update in popup menu @ ' + str(datetime.now())[0:19])
            ss.frame_sleeping = False
            ss.frame_awoken = False             # Turn off sleep mode flags
            ss.app_paused=False
            return

        # must have been a false wakeup, go back to sleep.
        if ss.frame_sleeping and ss.frame_awoken:
            blank_screen()
            ss.sleep_seconds = (ss.end_sleep_datetime - datetime.now()).seconds 
            if ss.dst_enabled: calc_dst()
            Clock.schedule_once(this_app.wakeup, ss.sleep_seconds + 1)
            logger.warning('check_sleeping: GOOD NIGHT, Going BACK to sleep @ ' + str(datetime.now())[:19] + ', sleep_seconds = ' + str(ss.sleep_seconds) + ', waking up @ ' + str(ss.end_sleep_datetime))
            ss.frame_awoken = False
            ss.app_paused = False
            return

        if ss.app_paused:   # Returning from display popup
            ss.app_paused = False
            ss.frame_awoken = False
            Clock.schedule_once(self.next,.1)  # go back to showing slideshow
            logger.warning('check_sleeping: -----> Continuing SlideShow after popup displayed @ ' + str(datetime.now())[0:19])
        return

    # ----------------------------------------------
    def wakeup(self, *largs):
    # ----------------------------------------------

        waketime = datetime.strptime(str(datetime.now())[:19], '%Y-%m-%d %H:%M:%S')
        if waketime < ss.end_sleep_datetime:        # Make sure overnight hanky-panky hasn't hosed the wakeup time. Then exit.
            ss.sleep_seconds = (ss.end_sleep_datetime - waketime).seconds
            if ss.debug_enabled: logger.warning('wakeup: Sleep wakeup not accurate @ ' + str(datetime.now())[0:19] + ', sleeping for sleep_seconds = ' + str(ss.sleep_seconds) + ' more.')
            Clock.schedule_once(self.wakeup, ss.sleep_seconds + 1)
            return
        if ss.digitalclock_enabled: self.clock_update()
        if ss.outside_info_enabled: self.weather_update()
        calc_sleep()
        update_gc_mem()
        wake_screen()
        logger.info('wakeup: GOOD MORNING - Waking up @ ' + str(datetime.now())[0:19])
        ss.frame_sleeping = False 
        ss.frame_awoken = False
        Clock.schedule_once(self.next,1)                                        # go back to showing photos

    # ----------------------------------------------
    def on_pause(self, *pos):
    # ----------------------------------------------
        logger.warning('---> on_pause triggered: ' + str(datetime.now())[0:19])
        Clock.unschedule(self.next)
        Clock.unschedule(self.check_sleeping)
        Clock.unschedule(SS_Loader.check_server)
        return True

    # ----------------------------------------------
    def on_resume(self):
    # ----------------------------------------------
        # Here you can check if any data needs replacing (usually nothing)

        logger.warning('---> on_resume triggered ' + str(datetime.now())[0:19])
        if test_connect(10): Clock.schedule_once(SS_Loader.check_server, 10)  #check_server('ON_RESUME') in 10 seconds
        else: logger.warning('ON_RESUME Init: No Internet Connection for this Frame.')
        self.check_sleeping()
        return True

    # ----------------------------------------------
    def on_moved(self, pos):
    # ----------------------------------------------
    # This handles touch screen move input - code below handles slide swiping left and right while playing SideShow.
 
        global move_count, move_pos, move_max, screenManager
        
        if ss.frame_sleeping:  return True
        if ss.swipe_enabled == False:  return True

        x_position = int(pos[1].pos[0])
        y_position = int(pos[1].pos[1])

        if ss.app_paused:
            return True

        move_max = 6 # this is the number of move coordinates to use in routine below
        if self.move_count == 0:
            Clock.unschedule(self.next)
            self.move_count = 1
            self.move_pos = array('i',[x_position])
            Clock.schedule_once(self.clear_move_count, 1)
            return True
        if self.move_count == move_max:
#            if ss.debug_enabled: logger.warning('Move touches captured: ' + str(self.move_pos))
            if ss.app_paused:    # Need to turn off screen pause indicator, if set
                ss.app_paused = False
                logger.info('---> PAUSED App Restarted: ' + str(datetime.now())[0:19])
            
#            if ss.debug_enabled: logger.warning('abs(self.move_pos[self.move_count-1]-self.move_pos[0])=' + str(abs(self.move_pos[self.move_count-1]-self.move_pos[0])))
            if abs(self.move_pos[self.move_count-1]-self.move_pos[0]) < 20:   # if not wide enough swipe in x direction, bu-bye...
                self.move_count = 0
                Clock.schedule_once(self.clear_move_count, 1)
                return True
            
    # This section sets up the Next picture image to display and transition.

            if(self.screenManager.current == 'page1'):
                next = 'page2'
                current_page = self.page2
            else:
                next = 'page1'
                current_page = self.page1

            if self.move_pos[self.move_count-1] < self.move_pos[0]:
                ss.slideshow_index += 1     # reset photo index back to zero after all photos in list displayed
                if ss.slideshow_index >= len(ss_pictures):
                    ss.slideshow_index = 0
                self.screenManager.transition = SlideTransition(direction='left')
            else:
#                if ss.debug_enabled: logger.warning('self.move_pos[self.move_count-1] <= self.move_pos[0]')
                if ss.slideshow_index == 0:
                    ss.slideshow_index = len(ss_pictures)-1     # reset photo index back to zero after all photos in list displayed
                else:
                    ss.slideshow_index -= 1
                self.screenManager.transition = SlideTransition(direction='right')
            current_page.source = ss_pictures[ss.slideshow_index]

    # Setup next caption when enabled

            if ss.captions_enabled: update_captions()
            current_page.background.scale = ss.scale_start
            self.screenManager.current = next

            anim = Animation(center=ss.display_center, d=0) + Animation(scale=float(ss.scale_end), duration=int(ss.slide_scale_timing), center=ss.display_center)
            anim.start(current_page.background)
            Clock.schedule_once(self.next, ss.slide_duration)
#            logger.info('on_moved: Clock.schedule_once(self.next, ' + str(ss.slide_duration) + ') @ ' + str(datetime.now())[0:19])
            return True
            
        elif self.move_count < move_max:
            self.move_pos.append(x_position)
            self.move_count += 1
        return True

    # ----------------------------------------------
    def clear_move_count(self, pos):
    # ----------------------------------------------
        global move_count, move_max

        Clock.unschedule(self.clear_move_count)
        if self.move_count < move_max:
            Clock.schedule_once(self.next, 1)
#            logger.info('clear_move_count: Clock.schedule_once(self.next, 1) @ ' + str(datetime.now())[0:19])
        del self.move_pos  # clear the list
        self.move_count = 0
        return True

    # -----------------------------------------------
    def tap_left_right(self, x_position, y_position):
    # -----------------------------------------------
        global touch_start, current_page, screenManager, page1, page2, anim

        touch_dir = ''
        # Left side pressed - Slide picture right
        if x_position > ss.slide_left[0] and y_position > ss.slide_left[1] and x_position < ss.slide_left[2] and y_position < ss.slide_left[3]: # slide left touch
            touch_dir = 'left'
            ss.slideshow_index += 1     # reset photo index back to zero after all photos in list displayed
            if ss.slideshow_index >= len(ss_pictures):
                ss.slideshow_index = 0

        # Right side pressed - Slide picture right
        if x_position > ss.slide_right[0] and y_position > ss.slide_right[1] and x_position < ss.slide_right[2] and y_position < ss.slide_right[3]: # slide right touch
            touch_dir = 'right'
            if ss.slideshow_index == 0:
                ss.slideshow_index = len(ss_pictures)-1     # reset photo index back to zero after all photos in list displayed
            else:
                ss.slideshow_index -= 1

        # This section sets up the Next picture image to display and transition.
        if touch_dir == 'left' or touch_dir == 'right':
            if ss.captions_enabled: update_captions()
#            if ss.digitalclock_enabled: self.clock_update()
            if ss.outside_info_enabled: self.weather_update()
            if self.screenManager.current == 'page1':
                next = 'page2'
                current_page = self.page2
                if ss.digitalclock_enabled: self.clock_page2_update()
            else:
                next = 'page1'
                current_page = self.page1
                if ss.digitalclock_enabled: self.clock_page1_update()

            self.screenManager.transition = SlideTransition(direction=touch_dir)
            current_page.source = ss_pictures[ss.slideshow_index]
            current_page.background.scale = ss.scale_start
            self.screenManager.current = next
            anim = Animation(center=ss.display_center, d=0) + Animation(scale=float(ss.scale_end), duration=int(ss.slide_scale_timing), center=ss.display_center)
            anim.start(current_page.background)
            return touch_dir

    # ----------------------------------------------
    def on_touch_down(self, touch):
    # ----------------------------------------------
        global touch_start, current_page, screenManager, page1, page2, anim
        # This handles touch screen taps input by users.
        # The final control-touch combination is once in the center to pause,
        # then a second touch in the middle. Otherwise, it just pauses until timeout.
        # This routine also handles touches during sleep.

        x_position = int(touch[1].pos[0])
        y_position = int(touch[1].pos[1])
        # Unschedule all slideshow timers, regardless if not scheduled
        Clock.unschedule(self.check_sleeping)
        Clock.unschedule(self.wakeup)
        Clock.unschedule(self.next)

        # check for shutdown request when awoken from sleep with previous touch, this differentiates the startup combination.
        if ss.frame_awoken and ss.app_paused: 
            logger.warning('on_touch_down: sleep touch FRAME AWOKEN @ ' + str(datetime.now())[0:19])
            if x_position > ss.touch_center[0] and x_position < ss.touch_center[2] and y_position > ss.touch_center[1] and y_position < ss.touch_center[3]:
                if datetime.now() - touch_start < timedelta(seconds=10):  # Here's the exit from sleep in control touch area.
                    if ss.debug_enabled: logger.warning('on_touch_down: Control Touch invoked during awoken mode, displaying popup.')
                    Clock.schedule_once(MessageBoxApp.callpopup, .1)
                    return
                else:
                    if ss.debug_enabled: logger.warning('on_touch_down: Control Touch HIT after 10 seconds (too late). Going back to sleep.')

            # Check for left or right touch while asleep.
            touch_dir = self.tap_left_right(x_position, y_position)
            if touch_dir == 'left' or touch_dir == 'right':
                Clock.schedule_once(self.check_sleeping, ss.awake_time_pause)  # stay awake for amount of time defined at top of this app then go to sleep if nothing happens
                if ss.debug_enabled: logger.warning('on_touch_down: ***** ASLEEP slide touch_dir = ' + touch_dir)
                return True

            # User must have touched the screen again outside control touch, put it back to sleep
            blank_screen()
            ss.sleep_seconds = (ss.end_sleep_datetime - datetime.now()).seconds 
            if ss.dst_enabled: calc_dst()
            Clock.schedule_once(this_app.wakeup, ss.sleep_seconds + 1)
            if ss.debug_enabled: logger.warning('on_touch_down: touch outside Control Touch region - Going back to sleep: sleep_seconds = ' + str(ss.sleep_seconds) + '.')
            ss.frame_awoken = False
            ss.frame_sleeping = True
            ss.app_paused = False
            return True

        # Frame is currently asleep and needs to turn display on
        if ss.frame_sleeping:
            if ss.debug_enabled: logger.warning('on_touch_down: Sleep wakeup touch WAS SLEEPING @ ' + str(datetime.now())[0:19])
            if ss.digitalclock_enabled: self.clock_update()
            if ss.outside_info_enabled: self.weather_update()
            wake_screen()
            touch_start = datetime.now()
            Clock.schedule_once(self.check_sleeping, ss.awake_time_pause)  # stay awake for amount of time defined at top of this app then go to sleep if nothing happens
            ss.frame_awoken = True
            ss.app_paused = True
            if ss.debug_enabled: logger.warning('on_touch_down: frame_sleeping awoken for ' + str(ss.awake_time_pause) + ' seconds.')
            return

################################################################
# Control Touch if twice in center within 3 seconds while awake.
################################################################

        if ss.app_paused:    # On second tap, turn off pause mode if not control touch

            # control touches if within center within 3 seconds.

            # Check for CENTER control touch
            if x_position > ss.touch_center[0] and x_position < ss.touch_center[2] and y_position > ss.touch_center[1] and y_position < ss.touch_center[3]:
                if datetime.now() - touch_start < timedelta(seconds=3):  # Here's the exit from paused with second touch in control touch area within 3 seconds.
                    if ss.debug_enabled: logger.warning('on_touch_down: Control Touch invoked while awake, displaying popup.')
                    Clock.schedule_once(MessageBoxApp.callpopup, .1)
                    return
                else:
                    if ss.debug_enabled: logger.warning('on_touch_down: Control Touch HIT after 3 seconds. Continuing SlideShow.')

            # Check for left or right touch while PAUSED.
            touch_dir = self.tap_left_right(x_position, y_position)
            if touch_dir == 'left' or touch_dir == 'right':
                Clock.schedule_once(self.next, ss.slide_duration)
                if ss.debug_enabled: logger.warning('on_touch_down: ***** Paused and slide touch_dir = ' + touch_dir)
                logger.warning('on_touch_down: Clock.schedule_once(self.next, ' + str(ss.slide_duration) + ') @ ' + str(datetime.now())[0:19])
                return True

            # Continue slideshow carousel when no control touch
            ss.app_paused = False
            if ss.debug_enabled: logger.warning('on_touch_down: ---> APP RESUMED after paused @ ' + str(datetime.now())[0:19])
            Clock.schedule_once(self.next, .5)

####################################################################################################################################
# This is the first touch when SlideShow is not sleeping, so Pause the Slideshow if center touch, or handle left/right side touches.
####################################################################################################################################
        else:
            if x_position > ss.touch_center[0] and y_position > ss.touch_center[1] and x_position < ss.touch_center[2] and y_position < ss.touch_center[3]: # pause only mid-screen touch

                ss.app_paused = True
                touch_start = datetime.now()

                if int(ss.pause_duration) == 0:
                    if ss.debug_enabled: logger.warning('on_touch_down: ---> APP PAUSED FOREVER, starting @ ' + str(datetime.now())[0:19])
                else:
                    if ss.debug_enabled: logger.warning('on_touch_down: ---> APP PAUSED for ' + str(ss.pause_duration) + ' seconds, starting @ ' + str(datetime.now())[0:19])
                    Clock.schedule_once(self.next, float(ss.pause_duration))

        return True

#---------------------
    def on_touch_up(self, touch):
#---------------------
        x_position = int(touch[1].pos[0])
        y_position = int(touch[1].pos[1])

        # Check for left or right touch while running.
        touch_dir = self.tap_left_right(x_position, y_position)
        if touch_dir == 'left' or touch_dir == 'right':
            Clock.schedule_once(self.next, ss.slide_duration)
            if ss.debug_enabled: logger.warning('on_touch_up: ***** Slide touch_dir = ' + touch_dir)
        return True

# start the main program
if __name__ in ('__main__', '__android__'):
    SlideShow().run()
