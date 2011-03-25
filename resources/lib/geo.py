import os
import sys
try:
    import xbmc
except:
    pass
from urllib2 import Request,urlopen,unquote,HTTPError
from urllib import urlencode,urlretrieve,urlcleanup
from traceback import print_exc

MAP_ZOOM_MIN = 1
MAP_ZOOM_MAX = 21
MAP_IMAGE_X_MAX = 640
MAP_IMAGE_Y_MAX = 640
MAP_IMAGE_X_MIN = 100
MAP_IMAGE_Y_MIN = 100
MAP_MARKER_COLOR = "red"
MAP_MARKER_LABEL = "P"

HTTP_USER_AGENT = 'Mozilla/5.0 (X11; U; Linux x86_64; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.151 Safari/534.16'


class GoogleError(Exception):
    def __init__(self, value):
	self.value = value
    def __str__(self):
	return repr(self.value)

def sx_find(js, term, offset, ec='"'):
    term += ":"
    tl = len(term) + 1
    return js[js.find(term, offset) + tl:js.find(ec, js.find(term, offset) + tl)]

def reverse_geocode(lat, lon):
    sx = {}

    try:
	req_url = 'http://maps.google.com/maps'
	req_hdr = { 'User-Agent': HTTP_USER_AGENT }
	req_par = { "q":"%s+%s" % (lat, lon), "output":"js" }
	req_dat = urlencode(req_par)
	req = Request(unquote(req_url + "?" + req_dat), None, req_hdr)
	resp = urlopen(req)
	js = resp.read()
	if ('<error>' in js or 'Did you mean:' in js or 'CAPTCHA' in js):
	    raise GoogleError('Google cannot interpret the address: %s %s' % (lat, lon))

	# if more than one address returned, it's likely a business and the
	# second entry could contain a title.
	offset = js.find('sxcn:') + 6
	if (sx_find(js, 'sxcn', offset) == ""):
	    offset = 0;

	# title
	sx['ti'] = sx_find(js, 'sxti', offset)
	if (sx['ti'] == ""):
	    sx['ti'] = sx_find(js, 'laddr', offset, ',')
	# street
	sx['st'] = sx_find(js, 'sxst', offset)
	# street number
	sx['sn'] = sx_find(js, 'sxsn', offset)
	# county
	sx['ct'] = sx_find(js, 'sxct', offset)
	# province
	sx['pr'] = sx_find(js, 'sxpr', offset)
	# post code
	sx['po'] = sx_find(js, 'sxpo', offset)
	# country
	sx['cn'] = sx_find(js, 'sxcn', offset)

	for a in sx:
	    sx[a] = sx[a].replace('\\x26', '&')
    except HTTPError, e:
	print to_str(e.geturl())
	raise e
    except Exception, e:
	raise e

    return sx

class staticmap:
    def __init__(self, imagepath="", loc="", marker=True, imagefmt="", zoomlevel=18, xsize=640, ysize=640, maptype=""):
	if (imagepath == ""):
	    raise ValueError("imagepath is required.")
	self.imagepath = imagepath

	if (loc == ""):
	    raise ValueError("loc (lat/lon pair or address) is required.")
	self.loc = loc
	self.showmarker = marker
	self.marker = "color:%s|label:%s|%s" % (MAP_MARKER_COLOR, MAP_MARKER_LABEL, self.loc)

	self.imagefmt = (imagefmt or "jpg")

	if (zoomlevel < MAP_ZOOM_MIN or zoomlevel > MAP_ZOOM_MAX):
	    raise ValueError("zoomlevel must be between %d and %d" % (MAP_ZOOM_MIN, MAP_ZOOM_MAX))
	self.zoomlevel = zoomlevel

	if (xsize < MAP_IMAGE_X_MIN or xsize > MAP_IMAGE_X_MAX):
	    raise ValueError("xsize must be between %d and %d" % (MAP_IMAGE_X_MIN, MAP_IMAGE_X_MAX))
	if (ysize < MAP_IMAGE_Y_MIN or ysize > MAP_IMAGE_Y_MAX):
	    raise ValueError("ysize must be between %d and %d" % (MAP_IMAGE_Y_MIN, MAP_IMAGE_Y_MAX))
	self.xsize = xsize
	self.ysize = ysize

	self.maptype = (maptype or "hybrid")

    def set_imageformat(self, imagefmt):
	if (imagefmt != ""):
	    self.imagefmt = (imagefmt or "jpg")

    def set_xsize(self, xsize):
	if (xsize >= MAP_IMAGE_X_MIN and xsize <= MAP_IMAGE_X_MAX):
	    self.xsize = xsize

    def set_ysize(self, ysize):
	if (ysize >= MAP_IMAGE_Y_MIN and ysize <= MAP_IMAGE_Y_MAX):
	    self.ysize = ysize

    def set_type(self, maptype):
	self.maptype = (maptype or "hybrid")

    def toggle_marker(self):
	self.showmarker = not self.showmarker

    def zoom(self, way, step=1):
	if (way == "+"):
	    self.zoomlevel = self.zoomlevel + step
	elif (way == "-"):
	    self.zoomlevel = self.zoomlevel - step
	else:
	    self.zoomlevel = step
	if (self.zoomlevel < MAP_ZOOM_MIN):
	    self.zoomlevel = MAP_ZOOM_MIN
	if (self.zoomlevel > MAP_ZOOM_MAX):
	    self.zoomlevel = MAP_ZOOM_MAX

    def fetch(self, file_prefix="", file_suffix=""):
	imagefile = ""

	# http://gmaps-samples.googlecode.com/svn/trunk/geocoder/singlegeocode.html
	try:
	    imagefile = os.path.join(self.imagepath, file_prefix + self.loc + file_suffix + "." + self.imagefmt)

	    req_url = "http://maps.google.com/maps/api/staticmap"
	    req_par = {
		"zoom":self.zoomlevel,
		"size":"%dx%d" % (self.xsize, self.ysize),
		"format":"%s" % (self.imagefmt),
		"maptype":"%s" % (self.maptype),
		"sensor":"false"
	    }
	    if (self.showmarker == True):
		req_par['markers'] = self.marker
	    else:
		req_par['center'] = self.loc
	    if (self.xsize <= 256 or self.ysize <= 256):
		req_par['style'] = "feature:road.local|element:geometry|visibility:simplified"
	    req_dat = urlencode(req_par)
	except Exception, e:
	    raise e

	try:
	    try:
		xbmc.sleep(1000)
	    except:
		pass
	    urlretrieve(unquote(req_url + "?" + req_dat), imagefile)
	except HTTPError, e:
	    print to_str(e.geturl())
	    raise e
	except:
	    urlcleanup()
	    remove_tries = 3
	    while remove_tries and os.path.isfile(imagefile):
		try:
		    os.remove(imagefile)
		except:
		    remove_tries -= 1
		    try:
			xbmc.sleep(1000)
		    except:
			pass

	return imagefile

if (__name__ == "__main__"):
    try:
	lat = sys.argv[1]
	lon = sys.argv[2]
    except:
	print "Usage geo.py <latitude> <longitude>"
	sys.exit(1)

    try:
	sx = reverse_geocode(lat, lon)
	print "Fetching maps for address:"
	print sx['ti']
	print "%s %s" % (sx['sn'], sx['st'])
	print "%s, %s  %s" % (sx['ct'], sx['pr'], sx['po'])
	print "%s\n" % (sx['cn'])

	loc = "%s+%s" % (lat, lon)
	map = staticmap("./", loc)
	map.set_xsize(640)
	map.set_ysize(640)
	print map.fetch("map_", "")
    except:
	print_exc()
