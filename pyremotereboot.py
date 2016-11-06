#!/usr/bin/env python
#
# pyremotereboot.py
# Copyright (C) 2016 Larroque Stephen
#
# Licensed under the MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#=================================
#                pyRemoteReboot
#                    Python 2.7.11
#                by Stephen Larroque
#                     License: MIT
#            Creation date: 2016-11-03
#=================================
#
#

# MINIMUM REQUIREMENTS
# ===================
# Python 2.7: http://www.python.org/getit/
# requests library
#
# FAQ
# ====
#
# - How to launch the script in hidden mode (no console window) on Windows?
# Change file extension to .pyw to associate with pythonw.exe, this will hide the console window. On Linux there's nothing to do, the console should be hidden by default.
# You can also use pyInstaller to generate a hidden app like this: pyinstaller --noconsole pyremotereboot.py
#

from __future__ import print_function, absolute_import

__version__= '0.2'

import sys
import os
import threading
import smtplib
import datetime, time
import shlex # to parse the config file just like commandline arguments
from copy import deepcopy

import socket
import fnmatch
import traceback
import inspect

import requests

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

# Determine the platform
_WIN = _LIN = _MAC = False

if sys.platform.lower() == 'win32':
    _WIN = True
elif os.platform.lower().startswith('linux'):
    _LIN = True
elif os.platform.lower() == 'Darwin'
    _MAC = True

if _WIN:
    import win32event, win32api, winerror
    from _winreg import *

# Global vars parameters, you can modify
reboot_remote_url = 'http://somewebsite.com/reboot_schedule.txt'
amount_sleep = 30 # time (in seconds) to sleep between each check (or each retry in case of failure to send because no connectivity etc)
# Configuration for email, if enabled
email_server = "smtp.server.com" # Specify Server Here
email_port = 25 # Specify Port Here
email_user = "some@email.com" # Specify Username Here 
email_pass = "mypass" # Specify Password Here
email_tls = True

# Disallowing Multiple Instance
if _WIN:
    mutex = win32event.CreateMutex(None, 1, 'mutex_var_xboz')
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        mutex = None
        print("Multiple Instance not Allowed")
        sys.exit(0)

def get_script_dir(follow_symlinks=True):
    if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path), path

class Logger(object):
    '''Redirect all outputs to a file (only if hidden)'''
    def __init__(self, logfile="debug.log"):
        self.logfilepath = logfile
        self.logfile = open(logfile, 'a')

    def write(self, data):
        self.logfile.write(data)

    def flush(self):
        pass

# Global vars, do not modify
scriptdirpath, scriptfilepath = get_script_dir() # need to get the scriptdirpath for startup and to find the config.cfg file
count=0
metadata = {"windowname": "pyRemoteReboot"}
logger = Logger()

#Hide Console
def hide():
    global _WIN
    if _WIN:
        import win32console,win32gui
        window = win32console.GetConsoleWindow()
        win32gui.ShowWindow(window,0)
    return True

def msg():
    print('''
pyRemoteReboot v%s

usage: pyRemoteReboot.py [startup] [email] [hide] [--help]

[optional] startup: This will add the app to windows startup (only on Windows, for Linux you need to add a cron entry @reboot).
[optional] email: Send an email everytime a reboot is scheduled.
[optional] hide: In combination with pyinstaller --noconsole, run in daemon mode (no console shown) (only on Windows at the moment).

Note: Can also specify the arguments in a file config.cfg placed where this script is located.
''' % __version__)
    return True

# Add to startup
def addStartup():
    global scriptfilepath, _WIN
    if _WIN:
        keyVal= r'Software\Microsoft\Windows\CurrentVersion\Run'

        key2change= OpenKey(HKEY_CURRENT_USER,
        keyVal,0,KEY_ALL_ACCESS)
        
        if len(sys.argv) > 1:
            path_with_args = "\"%s\" %s" % (scriptfilepath, ' '.join(sys.argv[1:]))
        else:
            path_with_args = "\"%s\"" % (scriptfilepath)

        SetValueEx(key2change, "pyRemoteReboot", 0, REG_SZ, path_with_args)

class TimerClass(threading.Thread):
    '''Main loop as a thread: check a remote HTTP url for a datetime and compare with current datetime. If in the future, schedule a reboot at the specified datetime'''

    def __init__(self, email=False, verbose=False):
        threading.Thread.__init__(self)
        self.email = email
        self.verbose = verbose
        self.event = threading.Event()

    def run(self):
        global _WIN, _LIN, _MAC
        reboot_scheduled = None # reboot scheduled?
        while not self.event.is_set():
            # Get remote datetime from HTTP url
            # It's your job to manage a way to modify the content of this url
            r = requests.get(reboot_remote_url)
            remotedatestr = r.text.strip()
            remotedate = datetime.datetime.strptime(remotedatestr, '%Y-%m-%d_%H-%M')
            # Get current datetime
            datenow = datetime.datetime.now()
            datenowstr = datenow.strftime('%Y-%m-%d_%H-%M')

            # Reboot already scheduled: check if the time is reached
            if reboot_scheduled:
                # Check if datenow is strictly greater to scheduled time by at least 1 minute (to avoid consecutive reboots...)
                if datenow >= (reboot_scheduled + datetime.timedelta(minutes=3)):
                    if self.verbose:
                        print('Preparing for reboot...')
                    # Send an email? (but try/catch to skip if error)
                    # TODO: implement a timeout
                    if self.email:
                        if self.verbose:
                            print('Sending an email')
                        try:
                            self.prepare_and_send_email(datenowstr, remotedatestr)
                        except Exception as exc:
                            # Print the error to debug log
                            print(traceback.format_exc())
                            # Then pass the error
                    # Reset reboot_scheduled flag
                    reboot_scheduled = None
                    # Print a notice about the reboot and wait 5 seconds
                    print('Rebooting NOW!')
                    time.sleep(5)
                    # Reboot now!
                    # Platform specific reboot commands
                    if _WIN:
                        #win32api.InitiateSystemShutdown()
                        os.system("shutdown -t 0 -r -f")
                    elif _LIN:
                        os.system("reboot")
                    elif _MAC:
                        os.system('shutdown -r now "Force remote reboot by pyRemoteReboot v%s"' % __version__)  # could also use osascript for cleaner reboot...
                else:
                    if self.verbose:
                        print('Sleeping until scheduled reboot time...')
                # Else: just wait...

            # Check remote date if in the future, this means it's scheduled
            elif remotedate >= datenow:
                    reboot_scheduled = deepcopy(remotedate)
                    print('Reboot scheduled for: %s' % remotedatestr)
            # Else there is a date but old (in the past, previous schedule), no future schedule
            else:
                if self.verbose:
                    print('Found date but too old: %s < %s' % (remotedatestr, datenowstr))

            # Sleep between each attempt to check remote datetime
            #self.event.wait(amount_sleep)
            time.sleep(amount_sleep) # less cpu consuming than wait since there is no lock to acquire here, see http://stackoverflow.com/questions/29082268/python-time-sleep-vs-event-wait

    def prepare_and_send_email(self, datenowstr, remotedatestr):
        global email_server, email_port, email_user, email_pass, email_tls
        SERVER = email_server
        PORT = email_port
        USER = email_user
        PASS = email_pass
        # Prepare the smtp settings and the message's data
        ctimezone = get_timezone()
        hostname = socket.gethostname()
        FROM = USER #From address is taken from username
        TO = [USER] #Specify to address.Use comma if more than one to address is needed.
        SUBJECT = "pyRemoteReboot scheduled %s %s %s" % (hostname, remotedatestr)
        body = "pyRemoteReboot scheduled for %s at %s (%s) (received at %s)" % (hostname, remotedatestr, ctimezone, datenowstr)

        # Send the mail!
        try:
            # Send the log by mail
            send_mail(FROM, TO, SUBJECT, body, None, server=SERVER, port=PORT, login=USER, passw=PASS, tls=email_tls)
        except Exception as exc:
            # Print the error to debug log
            print(traceback.format_exc())
            # Then pass the error

def find_files_rec(folder, pattern):
    matches = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.join(root, filename))
    return matches

def send_mail(send_from, send_to, subject, text, files=None, server="127.0.0.1", port="25", login=None, passw='', tls=False):
    assert isinstance(send_to, list)

    msg = MIMEMultipart(
        From=send_from,
        To=COMMASPACE.join(send_to),
        Date=formatdate(localtime=True),
        Subject=subject
    )
    msg['Subject'] = subject # Dunno why but we need to supply the subject this way, if we just supply as an argument to MIMEMultipart() the subject stays empty...
    msg.attach(MIMEText('Subject: %s\n\n%s' % (subject, text)))

    if files:
        for f in files or []:
            with open(f, "rb") as fil:
                msg.attach(MIMEApplication(
                    fil.read(),
                    Content_Disposition='attachment; filename="%s"' % os.path.basename(f),
                    Name=os.path.basename(f)
                ))

    smtp = smtplib.SMTP()
    smtp.connect(server, port)
    if tls: smtp.starttls()
    if login: smtp.login(login, passw)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.quit()

def main():
    global hidearg

    # Load commandline arguments
    argv = sys.argv

    # If config file is present, load arguments from config file
    if len(argv) == 1 and os.path.isfile(os.path.join(scriptdirpath, "config.cfg")):
        with open(os.path.join(scriptdirpath, "config.cfg"), "rb") as f:
            argv = shlex.split(f.read()) # Parse string just like argv using shlex
            argv.insert(0, sys.argv[0]) # add the current filename

    # No arguments, we print the help message
    if "--help" in argv or "-h" in argv:
        msg()
        sys.exit(0)
    # Else we have some arguments
    else:
        # Startup argument
        if "startup" in argv:
            addStartup() 
        if "hide" in argv:
            sys.stdout = logger
            sys.stderr = logger
            hide()
        email = True if "email" in argv else False
        verbose = True if "verbose" in argv else False

        # Launch the main loop as a thread
        mainloop = TimerClass(email, verbose)
        mainloop.start()
    return True

def get_timezone():
    ts = time.time()
    utc_offset = datetime.datetime.fromtimestamp(ts) - datetime.datetime.utcfromtimestamp(ts)
    ctimezone = str(datetime.timedelta(seconds=utc_offset.seconds))
    ctimezone_sign = '+' if utc_offset.days >= 0 else '-'
    return "UTC%s%s" % (ctimezone_sign, ctimezone)

if __name__ == '__main__':
    main()
