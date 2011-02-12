#!/usr/bin/python
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import sys
import os
import gtk
from gtk.gdk import threads_init

# Check if we are working in the source tree or from the installed 
# package and mangle the python path accordingly
if os.path.dirname(sys.argv[0]) != ".":
    if sys.argv[0][0] == "/":
        fullPath = os.path.dirname(sys.argv[0])
    else:
        fullPath = os.getcwd() + "/" + os.path.dirname(sys.argv[0])
else:
    fullPath = os.getcwd()
sys.path.insert(0, os.path.dirname(fullPath))

from xraters import AboutXratersDialog, PreferencesXratersDialog
from xraters.WiiConnectionMaker import WiiConnectionMaker
from xraters.xratersconfig import getdatapath

class XratersWindow(gtk.Window):
    __gtype_name__ = "XratersWindow"

    def __init__(self):
        """__init__ - This function is typically not called directly.
        Creation a XratersWindow requires redeading the associated ui
        file and parsing the ui definition extrenally,
        and then calling XratersWindow.finish_initializing().

        Use the convenience function NewXratersWindow to create
        XratersWindow object.

        """
        pass

    def finish_initializing(self, builder):
        """finish_initalizing should be called after parsing the ui definition
        and creating a XratersWindow object with it in order to finish
        initializing the start of the new XratersWindow instance.

        """
        #get a reference to the builder and set up the signals
        self.builder = builder
        self.builder.connect_signals(self)

        #uncomment the following code to read in preferences at start up
        dlg = PreferencesXratersDialog.NewPreferencesXratersDialog()
        self.preferences = dlg.get_preferences()

        #code for other initialization actions should be added here
        self.statusBar = self.builder.get_object("statusbar")
        self.__menuConnect = self.builder.get_object("menuitemConnect")

    def about(self, widget, data=None):
        """about - display the about box for xraters """
        about = AboutXratersDialog.NewAboutXratersDialog()
        response = about.run()
        about.destroy()

    def preferences(self, widget, data=None):
        """preferences - display the preferences window for xraters """
        prefs = PreferencesXratersDialog.NewPreferencesXratersDialog()
        response = prefs.run()
        if response == gtk.RESPONSE_OK:
            #make any updates based on changed preferences here
            pass
        prefs.destroy()

    def quit(self, widget, data=None):
        """quit - signal handler for closing the XratersWindow"""
        self.destroy()

    def on_destroy(self, widget, data=None):
        """on_destroy - called when the XratersWindow is close. """
        #clean up code for saving application state should be added here

        gtk.main_quit()
        
    def __connectCallback(self, connectionMaker):
        if connectionMaker.connected:
            self.__connected = True
        else:
            self.__menuConnect.set_sensitive(True)
    
    def on_wiiConnect(self, widget, data=None):
        self.__menuConnect.set_sensitive(False)
        connectionMaker = WiiConnectionMaker(self.preferences['wiiAddress'],
                                             self.statusBar,
                                             self.__connectCallback)
        connectionMaker.start()

def NewXratersWindow():
    """NewXratersWindow - returns a fully instantiated
    XratersWindow object. Use this function rather than
    creating a XratersWindow directly.
    """

    #look for the ui file that describes the ui
    ui_filename = os.path.join(getdatapath(), 'ui', 'XratersWindow.ui')
    if not os.path.exists(ui_filename):
        ui_filename = None

    builder = gtk.Builder()
    builder.add_from_file(ui_filename)
    window = builder.get_object("xraters_window")
    window.finish_initializing(builder)
    return window

if __name__ == "__main__":
    #support for command line options
    import logging, optparse
    parser = optparse.OptionParser(version="%prog %ver")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help="Show debug messages")
    (options, args) = parser.parse_args()

    #set the logging level to show debug messages
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug('logging enabled')

    #run the application
    window = NewXratersWindow()
    window.show()
    threads_init()
    gtk.main()

