import logging
import threading
import time

import xl
from xl.nls import gettext as _
from xl import event

from scrap import *

FREQUENCY = 5  # seconds

_PLUGIN = None

TRACK_CHANGE_CALLBACKS = (
        'playback_current_changed',
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
        self.agent = None
        self.exaile = exaile

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

    def start(self, scrappercls):
        self.stop()
        self.agent = ScrapperAgent(self, scrappercls())
        self.agent.start()

    def stop(self):
        if self.agent:
            self.agent.stop()
            self.agent = None

    def updatetrack(self, data):
        track = self.exaile.player.current
        if not track:
            return
        for tag in ['artist', 'title', 'album', 'author']:
            value = data.get(tag)
            if value:
                track.set_tag_raw(tag, value)


class ScrapperAgent(threading.Thread):
    def __init__(self, plugin, scrapper):
        super(ScrapperAgent, self).__init__()
        self.scrapper = scrapper
        self.plugin = plugin
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    @property
    def stopped(self):
        return self._stop.isSet()

    def run(self):
        try:
            logger.info(_("Scrapper agent started"))
            while not self.stopped:
                d = self.scrapper.current()
                logger.debug(_("Scrap gave %s") % d)
                self.plugin.updatetrack(d)
                time.sleep(FREQUENCY)
        except Exception, e:
            logger.exception(e)
        logger.info(_("Scrapper agent stopped"))
