xraters
=======

Xraters is a very simple graphic application that plots the acceleration reading from a Wii remote to the screen in real time. It allows the user to save the data to the disk.

Dependencies
------------

You need to install the cwiid driver from [here](http://abstrakraft.org/cwiid/#Download) or from your distribution's package manager.

It is also possible that you need to install [Glade](http://abstrakraft.org/cwiid/#Download).

Configuration
-------------

You will have to set the address of your particular Wii remote in the Preferences dialog before the application can correctly pair with your remote. The `lswm` command, which is part of the cwiid distribution, can be used to find out the address.
