# -*- coding: utf-8 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from desktopcouch.records.record import Record
from desktopcouch.records.server import CouchDatabase
from xraters.xratersconfig import getdatapath
import cwiid
import gtk
import os
import sys

class PreferencesXratersDialog(gtk.Dialog):
    __gtype_name__ = "PreferencesXratersDialog"
    prefernces = {}

    def __init__(self):
        """__init__ - This function is typically not called directly.
        Creation of a PreferencesXratersDialog requires redeading the associated ui
        file and parsing the ui definition extrenally,
        and then calling PreferencesXratersDialog.finish_initializing().

        Use the convenience function NewPreferencesXratersDialog to create
        NewAboutXratersDialog objects.
        """

        pass

    def finish_initializing(self, builder):
        """finish_initalizing should be called after parsing the ui definition
        and creating a AboutXratersDialog object with it in order to finish
        initializing the start of the new AboutXratersDialog instance.
        """

        #get a reference to the builder and set up the signals
        self.builder = builder
        self.builder.connect_signals(self)

        #set up couchdb and the preference info
        self.__db_name = "xraters"
        self.__database = CouchDatabase(self.__db_name, create=True)
        self.__preferences = None
        self.__key = None

        #set the record type and then initalize the preferences
        self.__record_type = "http://wiki.ubuntu.com/Quickly/RecordTypes/Xraters/Preferences"
        self.__preferences = self.get_preferences()
        #TODO:code for other initialization actions should be added here
        
        self.__entryWiiAddress = self.builder.get_object("entry_WiiAddress")
        self.__entryWiiAddress.set_text(self.__preferences['wiiAddress'])
        self.__filechooserOutput = self.builder.get_object("filechooser_output")
        self.__filechooserOutput.set_filename(self.__preferences['outputDir'])
        
    def get_preferences(self):
        """get_preferences  -returns a dictionary object that contain
        preferences for xraters. Creates a couchdb record if
        necessary.
        """

        if self.__preferences == None: #the dialog is initializing
            self.__load_preferences()
            
        #if there were no saved preference, this 
        return self.__preferences

    def __load_preferences(self):
        #TODO: add prefernces to the self.__preferences dict
        #default preferences that will be overwritten if some are saved
        self.__preferences = {"record_type":self.__record_type,
                              "wiiAddress": "00:17:AB:39:49:98",
                              "outputDir": ".",
                             }
        
        results = self.__database.get_records(record_type=self.__record_type, create_view=True)
       
        if len(results.rows) == 0:
            #no preferences have ever been saved
            #save them before returning
            self.__key = self.__database.put_record(Record(self.__preferences))
        else:
            self.__preferences = results.rows[0].value
            self.__key = results.rows[0].value["_id"]
            
        
    def __save_preferences(self):
        self.__database.update_fields(self.__key, self.__preferences)

    def ok(self, widget, data=None):
        """ok - The user has elected to save the changes.
        Called before the dialog returns gtk.RESONSE_OK from run().
        """

        #make any updates to self.__preferences here
        #self.__preferences["preference1"] = "value2"
                
        self.__preferences['wiiAddress'] = self.__entryWiiAddress.get_text()
        self.__preferences['outputDir'] = self.__filechooserOutput.get_filename()
        self.__save_preferences()

    def cancel(self, widget, data=None):
        """cancel - The user has elected cancel changes.
        Called before the dialog returns gtk.RESPONSE_CANCEL for run()
        """

        #restore any changes to self.__preferences here
        pass

def NewPreferencesXratersDialog():
    """NewPreferencesXratersDialog - returns a fully instantiated
    PreferencesXratersDialog object. Use this function rather than
    creating a PreferencesXratersDialog instance directly.
    """

    #look for the ui file that describes the ui
    ui_filename = os.path.join(getdatapath(), 'ui', 'PreferencesXratersDialog.ui')
    if not os.path.exists(ui_filename):
        ui_filename = None

    builder = gtk.Builder()
    builder.add_from_file(ui_filename)
    dialog = builder.get_object("preferences_xraters_dialog")
    dialog.finish_initializing(builder)
    return dialog

if __name__ == "__main__":
    dialog = NewPreferencesXratersDialog()
    dialog.show()
    gtk.main()

