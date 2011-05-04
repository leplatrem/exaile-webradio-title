import re
import urllib2


class WebRadioScrapper(object):
    def __init__(self, *args, **kwargs):
        self.uri = kwargs.get('uri')

    @classmethod
    def match(cls, fileuri):
        return False

    def download(self):
        try:
            data = urllib2.urlopen(self.uri)
            return data.read()
        except:
            return None

    def extract(self, d):
        return {}

    def postprocess(self, infos):
        for k, v in infos.items():
            v = v or ''
            try:
                u = v.decode('iso-8859-1')
                v = u.encode('utf8')
                v = unicode(v)
            except UnicodeDecodeError:
                pass
            infos[k] = v.rstrip().lstrip().title()
        return infos

    def current(self):
        d = self.download()
        c = self.extract(d)
        c = self.postprocess(c)
        return c


class FIPScrapper(WebRadioScrapper):
    def __init__(self, *args, **kwargs):
        super(FIPScrapper, self).__init__(*args, **kwargs)
        self.uri = "http://sites.radiofrance.fr/chaines/fip/endirect/"

    @classmethod
    def match(cls, fileuri):
        return fileuri.startswith("http://mp3.live.tv-radio.com/fip/all/")

    def extract(self, d):
        main = {}
        regex = re.compile("<td[^>]*><span class=\"blanc11\">\s*<b>(?P<artist>[^<]*)</b>(\s*\|)(?P<title>[^<\|]*)</span>(?P<extra>.*)</td>", re.IGNORECASE)
        r = regex.search(d)
        if r:
            main = r.groupdict()
            extra = main.pop('extra')
            if extra:
                regex = re.compile("(<br>)?Auteur : (?P<auteur>.*)<br>Album : (?P<album>.*)<Br>", re.IGNORECASE)
                e = regex.search(extra)
                main.update(e.groupdict() if e else {})
        return main


if __name__ == "__main__":
    fs = FIPScrapper()
    print fs.current()
