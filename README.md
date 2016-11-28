# pyRemoteReboot

## Description

A small utility to reboot a computer by scheduling a date on a file stored on a remote web server. The script regularly checks an HTTP url and if the date retrieved is in the future, it schedules a reboot.

This is highly useful when your remote control software hangs up for some reason and you can't access your computer anymore.

Put simply, just register to a free webhost and use your favourite FTP client (FileZilla) to upload a simple text file `nextreboots.txt` with this content:

```
2016-12-25_15-30
```

And run the script pyRemoteReboot on your computer. Your computer will reboot on the 25th december 2016 at 15h30.

## Usage

```
pyRemoteReboot v0.1

usage: pyRemoteReboot.py [startup] [email] [hide] [--help]

[optional] startup: This will add the app to windows startup.
[optional] email: Send an email everytime a reboot is scheduled.
[optional] hide: In combination with pyinstaller --noconsole, run in daemon mode
 (no console shown).

Note: Can also specify the arguments in a file config.cfg placed where this script is located.
```

## License
MIT

## FAQ
* How can I package a (frozen) standalone application for Windows/Linux/MacOSX?
The script supports [pyinstaller](http://www.pyinstaller.org/) to freeze this script for Windows or Linux or MacOSX. Just execute the following line:

`pyinstaller pyremotereboot.py`

And a frozen application ready to be run natively on any of these OSes without needing Python will be built.

* Why this architecture? Why not a socket listener allowing direct connection and instant reboot?
Most corporate networks have strict firewall and network security measures (which is good), and thus disallow making servers. Usually, TeamViewer (and other UDP hole punching softwares such as WebRTC like filepizza) can go through, but not the rest. UDP hole punching was beyond the timeframe alloted to make this (quick) script, so the approach is much simpler: it simply access a web resource through HTTP. In other words, a simple web page. Since outgoing HTTP is nearly always authorized by security measures, this allows this script to work in pretty much any condition, and thus to fulfill its purpose as a safe switch in case remote control softwares fail.

* What if my computer freeze?
Then you're screwed, the script cannot bypass that. You can maybe try to run the script as a higher privilege process, like ring-0 on Windows or root + level 1 on Linux, so that it takes precedence over the other processes (so maybe the other processes will freeze but not the higher privilege ones). But nothing can guarantee you that the script will work if the computer freezes. Only an external hardware could provide such a guarantee (and it may not be free from getting frozen itself...).

* What about security?
The script does not execute any foreign code, it simply fetch a date online on your own webhost, and then compares it with the current time and schedule a reboot if necessary. So at worst, your webhost might be compromised by a hacker, who could then schedule reboots on your computer. But that's all. Also, you can always take down the webhost or the script to remove this hindrance if it ever happens. Also, the script does only use your own webhost as a third-party provider, and the script is opensource, so no risk of getting information leakage.
