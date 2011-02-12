'''
Created on Feb 7, 2010

@author: carlos
'''

from threading import Thread
import cwiid

class WiiConnectionMaker(Thread):
    def __init__(self, wiiAddress, status=None, callback=None):
        Thread.__init__(self)
        
        self.wiiAddress = wiiAddress
        self.callback = callback
        self.status = status
        if self.status:
            self.sc = self.status.get_context_id('')
        self.wiiMote = None
        self.acc_cal = None
    
        self.reset()
        
    def reset(self):
        self.connected = False
        self.timed_out = False
        
    def run(self):
        if self.status:
            self.status.pop(self.sc)
            self.status.push(self.sc,
                             "Please press 1+2 on your Wiimote...")
        
        try:
            self.wiiMote = cwiid.Wiimote(self.wiiAddress)
            self.connected = True
            self.wiiMote.enable(cwiid.FLAG_MESG_IFC)
            self.wiiMote.rpt_mode = cwiid.RPT_ACC
            self.acc_cal = self.wiiMote.get_acc_cal(cwiid.EXT_NONE)
            
            if self.status:
                self.status.pop(self.sc)
                self.status.push(self.sc,
                                 "Wiimote connected.")
        except:
            self.timed_out = True
            if self.status:
                self.status.pop(self.sc)
                self.status.push(self.sc,
                                 "Connection failed. Please try again.")
        finally:
            if self.callback:
                self.callback(self)
        