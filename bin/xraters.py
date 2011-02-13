#!/usr/bin/python
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from gtk.gdk import threads_init
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import cwiid
import gobject
import gtk
import os
import sys
import time

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
        self.__acc_cal = ((128, 128, 128),
                          (255, 255, 255))
        self.__acc = [0, 0, 0]
        self.__connected = False
        self.__wiiMote = None
        self.__xAcc = list()
        self.__yAcc = list()
        self.__zAcc = list()
        self.__time = list()
        self.__xlim = time.time()

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
        self.__vboxMain = self.builder.get_object("vboxMain")
        
        self.__accFigure = Figure(figsize=(8,6), dpi=72)
        self.__accAxis = self.__accFigure.add_subplot(111)
        self.__line = self.__accAxis.plot(self.__time, self.__xAcc,
                                          self.__time, self.__yAcc,
                                          self.__time, self.__zAcc, animated=True)
        self.__accAxis.set_ylim(-4, 4)
        self.__accCanvas = FigureCanvas(self.__accFigure)
        self.__accCanvas.mpl_connect("draw_event", self.__upd_background)
        self.__background = self.__accCanvas.copy_from_bbox(self.__accAxis.bbox)
        self.__accCanvas.show()
        self.__accCanvas.set_size_request(600, 400)
        self.__vboxMain.pack_start(self.__accCanvas, True, True)
        self.__vboxMain.show()
        self.__vboxMain.reorder_child(self.__accCanvas, 1)
    
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
        
    def on_wiiConnect(self, widget, data=None):
        self.__menuConnect.set_sensitive(False)
        connectionMaker = WiiConnectionMaker(self.preferences['wiiAddress'],
                                             self.statusBar,
                                             self.__connectCallback)
        connectionMaker.start()
        
    def __connectCallback(self, connectionMaker):
        if connectionMaker.connected:
            self.__connected = True
            self.__wiiMote = connectionMaker.wiiMote
            self.__timestart = time.time()
            gobject.timeout_add(9, self.__getAcc)
        else:
            self.__menuConnect.set_sensitive(True)    
    
    def __upd_background(self, event):
        self.__background = self.__accCanvas.copy_from_bbox(self.__accAxis.bbox)
    
    def __getAcc(self):
        messages = None
        while messages == None:
            messages = self.__wiiMote.get_mesg()
            
        for msg in messages:
            if msg[0] == cwiid.MESG_ACC:
                # Normalize data using calibration info from the controller
                for i in range(3):
                    self.__acc[i] = 4*float(msg[1][i]-self.__acc_cal[0][i])/(self.__acc_cal[1][i]-self.__acc_cal[0][i])
        self.__time.append(time.time())
        self.__xAcc.append(self.__acc[0])
        self.__yAcc.append(self.__acc[1])
        self.__zAcc.append(self.__acc[2])
        if (self.__xlim - self.__time[0] < 5):
            if (self.__time[-1] > self.__xlim):
                self.__xlim = time.time() + 2
                self.__accAxis.set_xlim(self.__time[0], self.__xlim)
                
                gobject.idle_add(self.__accCanvas.draw)
        else:
            if (self.__time[-1] > self.__xlim):
                self.__xlim = time.time() + 2
                self.__accAxis.set_xlim(self.__xlim-5, self.__xlim)
                gobject.idle_add(self.__accCanvas.draw)
        if self.__background != None:
            self.__accCanvas.restore_region(self.__background)
        self.__line[0].set_data(self.__time, self.__xAcc)
        self.__line[1].set_data(self.__time, self.__yAcc)
        self.__line[2].set_data(self.__time, self.__zAcc)
        self.__accAxis.draw_artist(self.__line[0])
        self.__accAxis.draw_artist(self.__line[1])
        self.__accAxis.draw_artist(self.__line[2])
        self.__accCanvas.blit(self.__accAxis.bbox)

        return True

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

