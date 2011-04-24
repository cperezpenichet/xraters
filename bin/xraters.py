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
from scipy import correlate
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
        self._PATTERN = 17 * [1]
        self._PATTERN.extend(17 * [-1])
        
        self._acc_cal = ((510, 486, 515),
                         (729, 705, 722))
        self._acc = [0, 0, 0]
        self._connected = False
        self._wiiMote = None
        self._resetData()
        self._dataLock = threading.Lock()
        
    isConnected = property(lambda self: self._connected)
    
    def callback(funct):
        """A decorator used to require connection to the Wii Remote
        
        This decorator is used to implement the precondition that 
        the Wii Remote must be connected. 
        """
        def _callback(cls, *args, **kwds):
            if cls.isConnected:
                funct(cls, *args, **kwds)
                return True
            else:
                return False
        return _callback
    
    def _connectCallback(self, connectionMaker):
        """Callback function called upon successful connection to the Wiimote
        """
        if connectionMaker.connected:
            self._connected = True
            self._wiiMote = connectionMaker.wiiMote
            self._resetData()
            gobject.timeout_add(45, self._drawAcc)
            self.widget('actionDisconnect').set_sensitive(True)
            self.widget('actionSave').set_sensitive(True)
            self.widget('actionReset').set_sensitive(True)
            self.widget('actionPause').set_sensitive(True)
            self.widget('toolbutton1').set_related_action(self.widget('actionDisconnect'))
            self._wiiMote.mesg_callback = self._getAcc
            self._updBatteryLevel()
            gobject.timeout_add_seconds(60, self._updBatteryLevel)
        else:
            self.widget('actionWiiConnect').set_sensitive(True)
            
    @callback
    def _upd_background(self, event):
        """Keep a copy of the figure background
        """
        self.__background = self._accCanvas.copy_from_bbox(self._accAxis.bbox)
    
    def _getAcc(self, messages, theTime=0):
        """Process acceleration messages from the Wiimote
        
        This function is intended to be set as cwiid.mesg_callback
        """
        if self._Paused:
            return
        for msg in messages:
            if msg[0] == cwiid.MESG_ACC:
                # Normalize data using calibration info
                for i, axisAcc in enumerate(msg[1]):
                    self._acc[i] = float(axisAcc-self._acc_cal[0][i])
                    self._acc[i] /=(self._acc_cal[1][i]\
                                    -self._acc_cal[0][i])
                with self._dataLock:
                    # Store time and acceleration in the respective arrays
                    self._time.append(theTime-self._startTime)
                    [self._accData[i].append(self._acc[i]) for i in threeAxes]
                # We only keep about 6 seconds worth of data
                if (self._time[-1] - self._time[0] > 6):
                    with self._dataLock:
                        self._time.pop(0)
                        [self._accData[i].pop(0) for i in threeAxes]

    @callback
    def _drawAcc(self):
        """Update the acceleration graph
        
        """
        # Do nothing while paused or there's no data available
        if self._Paused or len(self._time)==0:
            return
        draw_flag = False
        # Update axes limits if the data fall out of range 
        lims = self._accAxis.get_xlim()
        if self._time[-1] > lims[1]:
            self._accAxis.set_xlim(lims[0], lims[1]+2)
            lims = self._accAxis.get_xlim()
            draw_flag = True
        if (self._time[-1] - lims[0] > 6):
            self._accAxis.set_xlim(lims[0]+2, lims[1])
            draw_flag = True
        if draw_flag:
            gobject.idle_add(self._accCanvas.draw)
        # Do the actual update of the background
        if self.__background != None:
            self._accCanvas.restore_region(self.__background)
        # Do the actual update of the lines
        with self._dataLock:
            [self._lines[i].set_data(self._time, self._accData[i]) for i in threeAxes]
        [self._accAxis.draw_artist(self._lines[i]) for i in threeAxes]
        self._accCanvas.blit(self._accAxis.bbox)

    @callback
    def _updBatteryLevel(self):
        """Callback to update the battery indicator in the status bar
        
        """
        self._wiiMote.request_status()
        self._setBatteryIndicator(float(self._wiiMote.state['battery']) / 
                                  cwiid.BATTERY_MAX)
        
    def _setBatteryIndicator(self, level):
        """Actually update the battery indicator in the status bar
        
        """
        progressBar = self.widget("progressbarBattery")
        progressBar.set_fraction(level)
        progressBar.set_text("Battery: %.0f%%" % (level * 100))
    
    def _resetData(self):
        """Reset stored data and status flags to their defaults
        
        """
        self._accData = [list(), list(), list()]
        self._time = list()
        self._startTime = time.time()
        self._moveTime = self._startTime
        self._Paused = False
        
    def widget(self, name):
        """Helper function to retrieve widget handlers
        
        """ 
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
        self._accAxis.set_ylabel("acceleration (g)")
        self._lines = self._accAxis.plot(self._time, self._accData[X],
                                         self._time, self._accData[Y],
                                         self._time, self._accData[Z], 
                                         animated=True)
        self._accFigure.legend(self._lines, ("X", "Y", "Z"), 
                             'upper center', 
                             ncol=3)
        self._accAxis.set_xlim(0, 2)
        self._accAxis.set_ylim(-3, 3)
        self._accCanvas = FigureCanvas(self._accFigure)
        self._accCanvas.mpl_connect("draw_event", self._upd_background)
        self.__background = self._accCanvas.copy_from_bbox(self._accAxis.bbox)
        self._accCanvas.show()
        self._accCanvas.set_size_request(600, 400)
        vbMain = self.widget("vboxMain")
        vbMain.pack_start(self._accCanvas, True, True)
        vbMain.show()
        vbMain.reorder_child(self._accCanvas, 2)
        self._setBatteryIndicator(0)
        
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
        prefs.destroy()

    def quit(self, widget, data=None):
        """quit - signal handler for closing the XratersWindow"""
        self.destroy()

    def on_destroy(self, widget, data=None):
        """on_destroy - called when the XratersWindow is close. """
        #clean up code for saving application state should be added here
        if self.isConnected:
            self.on_wiiDisconnect(widget, data)
        gtk.main_quit()
        
    def on_wiiConnect(self, widget, data=None):
        """Signal handler for the WiiConnect action
        
        """
        self.widget('actionWiiConnect').set_sensitive(False)
        connectionMaker = WiiConnectionMaker(self.preferences['wiiAddress'],
                                             self.widget("statusbar"),
                                             self._connectCallback)
        self._accAxis.set_xlim(0, 2)
        gobject.idle_add(self._accCanvas.draw)
        connectionMaker.start()
        
    def on_wiiDisconnect(self, widget, data=None):
        """Signal handler for the WiiDisconnect action
        
        """
        self._wiiMote.close()
        self._connected = False
        self.widget('actionDisconnect').set_sensitive(False)
        self.widget('actionWiiConnect').set_sensitive(True)
        self.widget('actionReset').set_sensitive(False)
        self.widget('actionPause').set_sensitive(False)
        self.widget('toolbutton1').set_related_action(self.widget('actionWiiConnect'))
        self.widget('actionSave').set_sensitive(True)
        self.widget('statusbar').pop(self.widget("statusbar").get_context_id(''))
        self._setBatteryIndicator(0)
        
    def on_Reset(self, widget, data=None):
        """Signal handler for the reset action
        
        """
        self._resetData()
        self._accAxis.set_xlim(0, 2)
        gobject.idle_add(self._accCanvas.draw)
        
    def on_Pause(self, widge, data=None):
        """Signal handler for the pause action
        
        """
        if not self._Paused:
            self.widget('actionPause').set_short_label("Un_pause")
        else:
            self.widget('actionPause').set_short_label("_Pause")
        self._Paused = not (self._Paused)        

    def save(self, widget, data=None):
        """Signal handler for the save action
        
        """
        fileName = os.sep.join([self.preferences['outputDir'], 
                                "acceleration_" + 
                                time.strftime("%Y-%m-%d_%H-%M-%S") + 
                                ".dat"]) 
        try:
            with open(fileName, 'wb') as outFile:
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

