#!/usr/bin/python
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

__metaclass__ = type

from cwiid import X, Y, Z 
from gtk.gdk import threads_init
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import csv
import cwiid
import gobject
import gtk
import os
import sys
import threading
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

threeAxes = [X,Y,Z]

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
        self._acc_cal = ((128, 128, 128),
                         (255, 255, 255))
        self._acc = [0, 0, 0]
        self._connected = False
        self._wiiMote = None
        self._resetData()
        self._dataLock = threading.Lock()
        
    isConnected = property(lambda self: self._connected)
    
    def callback(funct):
        def _callback(cls, *args, **kwds):
            if cls.isConnected:
                funct(cls, *args, **kwds)
                return True
            else:
                return False
        return _callback
    
    def _connectCallback(self, connectionMaker):
        if connectionMaker.connected:
            self._connected = True
            self._wiiMote = connectionMaker.wiiMote
            self._resetData()
            gobject.timeout_add(45, self._drawAcc)
            self.widget('actionDisconnect').set_sensitive(True)
            self.widget('actionSave').set_sensitive(True)
            self._wiiMote.mesg_callback = self._getAcc
            self._updBatteryLevel()
            gobject.timeout_add_seconds(60, self._updBatteryLevel)
        else:
            self.widget('actionWiiConnect').set_sensitive(True)
            
    @callback
    def _upd_background(self, event):
        self.__background = self._accCanvas.copy_from_bbox(self._accAxis.bbox)
    
    def _getAcc(self, messages, theTime=0):
        for msg in messages:
            if msg[0] == cwiid.MESG_ACC:
                # Normalize data using calibration info from the controller
                for i, axisAcc in enumerate(msg[1]):
                    self._acc[i] = float(axisAcc-self._acc_cal[0][i])/(self._acc_cal[1][i]-self._acc_cal[0][i])
                    self._acc[i] *= self.preferences['accRange']
                with self._dataLock:
                    self._time.append(theTime-self._startTime)
                    [self._accData[i].append(self._acc[i]) for i in threeAxes] 
                if (len(self._time) > 600):
                    with self._dataLock:
                        self._time.pop(0)
                        [self._accData[i].pop(0) for i in threeAxes]

    @callback
    def _drawAcc(self):
        if (self._time[-1] > self._xlim or len(self._time)==0):
            self._xlim = time.time() - self._startTime + 2
            self._accAxis.set_xlim(self._time[0]+2, self._xlim)
            gobject.idle_add(self._accCanvas.draw)
        if self.__background != None:
            self._accCanvas.restore_region(self.__background)
        with self._dataLock:
            [self._lines[i].set_data(self._time, self._accData[i]) for i in threeAxes]
        [self._accAxis.draw_artist(self._lines[i]) for i in threeAxes]
        self._accCanvas.blit(self._accAxis.bbox)

    @callback
    def _updBatteryLevel(self):
        self._wiiMote.request_status()
        progressBar = self.widget("progressbarBattery")
        progressBar.set_fraction(float(self._wiiMote.state['battery']) / cwiid.BATTERY_MAX)
        progressBar.set_text("Battery: %.0f%%" % (progressBar.get_fraction() * 100))
    
    def _resetData(self):
        self._accData = [list(), list(), list()]
        self._time = list()
        self._startTime = time.time()
        self._xlim = 0.1
        
    def widget(self, name):
        return self.builder.get_object(name)

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
        self._accFigure = Figure(figsize=(8,6), dpi=72)
        self._accAxis = self._accFigure.add_subplot(111)
        self._accAxis.set_xlabel("time (s)")
        self._accAxis.set_ylabel("gravity (g)")
        self._lines = self._accAxis.plot(self._time, self._accData[X],
                                         self._time, self._accData[Y],
                                         self._time, self._accData[Z], 
                                         animated=True)
        self._accAxis.set_ylim(-self.preferences['accRange'], 
                                self.preferences['accRange'])
        self._accCanvas = FigureCanvas(self._accFigure)
        self._accCanvas.mpl_connect("draw_event", self._upd_background)
        self.__background = self._accCanvas.copy_from_bbox(self._accAxis.bbox)
        self._accCanvas.show()
        self._accCanvas.set_size_request(600, 400)
        vbMain = self.widget("vboxMain")
        vbMain.pack_start(self._accCanvas, True, True)
        vbMain.show()
        vbMain.reorder_child(self._accCanvas, 1)
        
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
            self.preferences = prefs.get_preferences()
            self._accAxis.set_ylim(-self.preferences['accRange'], 
                                    self.preferences['accRange'])
            self._accCanvas.draw()
        prefs.destroy()

    def quit(self, widget, data=None):
        """quit - signal handler for closing the XratersWindow"""
        self.destroy()

    def on_destroy(self, widget, data=None):
        """on_destroy - called when the XratersWindow is close. """
        #clean up code for saving application state should be added here
        gtk.main_quit()
        
    def on_wiiConnect(self, widget, data=None):
        self.widget('actionWiiConnect').set_sensitive(False)
        connectionMaker = WiiConnectionMaker(self.preferences['wiiAddress'],
                                             self.widget("statusbar"),
                                             self._connectCallback)
        connectionMaker.start()
        
    def on_wiiDisconnect(self, widget, data=None):
        self._wiiMote.close()
        self._connected = False
        self.widget('actionDisconnect').set_sensitive(False)
        self.widget('actionWiiConnect').set_sensitive(True)
        self.widget('actionSave').set_sensitive(True)
        
    def save(self, widget, data=None):
        fileName = os.sep.join([self.preferences['outputDir'], 
                                "acceleration_" + 
                                time.strftime("%Y-%m-%d_%H-%M-%S") + 
                                ".dat"]) 
        try:
            with open(fileName, 'wb') as outFile:
                #TODO Display a real save dialog.
                writer = csv.writer(outFile, 'excel-tab')
                outFile.write(writer.dialect.delimiter.join(("#time",
                                                          "Ax",
                                                          "Ay",
                                                          "Az")))
                outFile.write(writer.dialect.lineterminator)
                outFile.write(writer.dialect.delimiter.join(("#s",
                                                          "g",
                                                          "g",
                                                          "g")))
                outFile.write(writer.dialect.lineterminator)
                with self._dataLock:
                    writer.writerows(zip(self._time, *self._accData))
        except IOError as error:
            dialog = gtk.MessageDialog(parent   = None,
                                       flags    = gtk.DIALOG_DESTROY_WITH_PARENT,
                                       type     = gtk.MESSAGE_ERROR,
                                       buttons  = gtk.BUTTONS_OK,
                                       message_format = str(error))
            dialog.set_title(error[1])
            dialog.connect('response', lambda dialog, response: dialog.destroy())
            dialog.show()

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

