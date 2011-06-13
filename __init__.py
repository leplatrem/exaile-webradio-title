import os
import logging
import threading
import time
import random

import xl
from xl.nls import gettext as _
from xl import event, common

from scrap import *

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
        xl.event.add_callback(_PLUGIN.change, signal)



class WebRadioTitlePlugin(object):
 
    def __init__(self, exaile):
        self.exaile = exaile
        self.scrapper = None
        self._stop = None
        self._previous = {}
        self._tmptag = False

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
                if not self._previous or \
                   any(d.get(k) != self._previous.get(k) for k in d):
                    logger.debug(_("New track scrapped %s") % d)
                    self.updatetrack(d)
                    self._previous = d
                time.sleep(FREQUENCY)
            except Exception, e:
                logger.exception(e)
        self.scrapper = None
        logger.info(_("Scrapping stopped"))

    def start(self):
        self._stop = threading.Event()

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

        logger.debug(_("Simulate track change"))
        track.set_tag_raw('__length', random.randint(180, 240))  # fake length
        loc = track.get_tag_raw('__loc')
        self._tmptag = True
        fakepath = os.path.abspath(os.urandom(random.randint(16, 32)))
        track.set_tag_raw('__loc', fakepath)  # fake is_local() for audioscrobbler plugin
        event.log_event('playback_track_start', self.exaile.player, track, async=False)
        track.set_tag_raw('__loc', loc)
        self._tmptag = False
