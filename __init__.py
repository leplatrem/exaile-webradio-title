import logging
import threading
import time

import xl
from xl.nls import gettext as _
from xl import event, common

from scrap import *

FREQUENCY = 5  # seconds

_PLUGIN = None

TRACK_CHANGE_CALLBACKS = (
        'playback_buffering',
        'playback_player_resume',
        'playback_current_changed',
        'playback_track_start',
        'playback_player_start',
        'playback_track_end',
        'player_loaded',
        )


logger = logging.getLogger(__name__)

def enable(exaile):
    if (exaile.loading):
        event.add_callback(_enable, 'exaile_loaded')
    else:
        _enable(None, exaile, None)
 
def disable(exaile):
    global _PLUGIN
    _PLUGIN.stop()
 
def _enable(eventname, exaile, nothing):
    global _PLUGIN
    if not _PLUGIN:
        _PLUGIN = WebRadioTitlePlugin(exaile)
    _PLUGIN.exaile = exaile
    for signal in TRACK_CHANGE_CALLBACKS:
        xl.event.add_callback(_PLUGIN.change, signal)



class WebRadioTitlePlugin(object):
 
    def __init__(self, exaile):
        self.exaile = exaile
        self._stop = threading.Event()
        self.scrapper = None

    def __del__(self):
        self.stop()

    def change(self,  *args, **kwargs):
        if self.exaile is None:
            return
        if not hasattr(self.exaile, 'player'):
            logger.debug(_("Player not loaded, ignoring change call"))
            return

        track = self.exaile.player.current
        if not track:
            logger.debug(_("Player stopped, stop fetching titles"))
            self.stop()
            return
        
        url = track.get_loc_for_io()
        
        # Look for a web scrapper that knows this url
        matchcls = None
        for cls in [FIPScrapper]:  # more coming !
            if cls.match(url):
                matchcls = cls
        if matchcls:
            self.start(matchcls)
        else:
            logger.debug(_("Current track does not match any webradio scrapper"))
            self.stop()

    @common.threaded
    def start(self, scrappercls):
        if self.scrapper and isinstance(self.scrapper, scrappercls):
            return
        logger.info(_("Scrapping started"))        
        self.scrapper = scrappercls()
        while not self.stopped:
            try:
                d = self.scrapper.current()
                logger.debug(_("Scrap gave %s") % d)
                self.updatetrack(d)
                time.sleep(FREQUENCY)
            except Exception, e:
                logger.exception(e)
        self.scrapper = None
        logger.info(_("Scrapping stopped"))

    def stop(self):
        self._stop.set()

    @property
    def stopped(self):
        return self._stop.isSet()

    def updatetrack(self, data):
        track = self.exaile.player.current
        if not track:
            return
        for tag in ['artist', 'title', 'album', 'author']:
            value = data.get(tag)
            if value:
                track.set_tag_raw(tag, value)

