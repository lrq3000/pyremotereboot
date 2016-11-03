# pyRemoteReboot

A small utility to reboot a computer by scheduling a date on a file stored on a remote web server. The script regularly checks an HTTP url and if the date retrieved is in the future, it schedules a reboot.

This is highly useful when your remote control software hangs up for some reason and you can't access your computer anymore.

Put simply, just register to a free webhost and put this inside a file `nextreboots.txt`:

```
2016-12-25_15-30
```

And run the script pyRemoteReboot on your computer. Your computer will reboot on the 25th december 2016 at 15h30.

Usage:

```
pyRemoteReboot v0.1

usage: pyRemoteReboot.py [startup] [email] [hide] [--help]

[optional] startup: This will add the app to windows startup.
[optional] email: Send an email everytime a reboot is scheduled.
[optional] hide: In combination with pyinstaller --noconsole, run in daemon mode
 (no console shown).

Note: Can also specify the arguments in a file config.cfg placed where this script is located.
```

License: MIT.
