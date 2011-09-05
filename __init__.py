import os
import logging
import threading
import time
import random

from xl import event, player
from xl.nls import gettext as _
from xl import event, common

from scrap import FIPScrapper

FREQUENCY = 10  # seconds

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
        event.add_callback(_PLUGIN.change, signal)



class WebRadioTitlePlugin(object):
 
    def __init__(self, exaile):
        self.player = player.PLAYER
        self.scrapper = None
        self._stop = None
        self._previous = {}
        self._tmptag = False

    def __del__(self):
        self.stop()

    def change(self,  *args, **kwargs):
        track = self.player.current
        if not track:
            logger.debug(_("Player stopped, stop fetching titles"))
            self.stop()
            return

        if self._tmptag:  # Ignore event while tags set in updatetrack()
            return

        url = track.get_loc_for_io()
        
        # Look for a web scrapper that knows this url
        matchcls = None
        for cls in [FIPScrapper]:  # more coming !
            if cls.match(url):
                matchcls = cls
        if matchcls:
            self.run(matchcls)
        else:
            logger.debug(_("Current track does not match any webradio scrapper"))
            self.stop()

    def haschanged(self, tags):
        return self._previous is None or \
               any(tags.get(k) != self._previous.get(k) for k in tags)

    @common.threaded
    def run(self, scrappercls):
        if self.scrapper and isinstance(self.scrapper, scrappercls):
            # Already running with this scrapper
            return
        logger.info(_("Scrapping started"))
        self.start()
        self.scrapper = scrappercls()
        while not self.stopped:
            try:
                d = self.scrapper.current()                
                # Update track if some field changed
                if self.haschanged(d):
                    logger.debug(_("New track scrapped %s") % d)
                    self.updatetrack(d)
                    self._previous = d
                time.sleep(FREQUENCY)
            except Exception, e:
                logger.exception(e)
        self.scrapper = None
        self._previous = None
        logger.info(_("Scrapping stopped"))

    def start(self):
        self._stop = threading.Event()

    def stop(self):
        if self._stop:
            self._stop.set()

    @property
    def stopped(self):
        return self._stop.isSet()

    def updatetrack(self, data):
        track = self.player.current
        if not track:
            return
        for tag in ['artist', 'title', 'album', 'author']:
            value = data.get(tag)
            if value:
                track.set_tag_raw(tag, value)
