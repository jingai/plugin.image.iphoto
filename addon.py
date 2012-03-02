"""
    Plugin for importing iPhoto library
"""

__plugin__ = "iPhoto"
__author__ = "jingai <jingai@floatingpenguins.com>"
__credits__ = "Anoop Menon, Nuka1195, JMarshal, jingai, brsev (http://brsev.com#licensing)"
__url__ = "git://github.com/jingai/plugin.image.iphoto.git"

import sys
import time
import os
import glob

import xbmc
import xbmcgui as gui
import xbmcplugin as plugin
import xbmcaddon

try:
    import xbmcvfs
except ImportError:
    import shutil
    copyfile = shutil.copyfile
else:
    copyfile = xbmcvfs.copy

try:
    from hashlib import md5
except ImportError:
    import md5

addon = xbmcaddon.Addon(id="plugin.image.iphoto")
ALBUM_DATA_XML = "AlbumData.xml"
BASE_URL = "%s" % (sys.argv[0])
PLUGIN_PATH = addon.getAddonInfo("path")
RESOURCE_PATH = os.path.join(PLUGIN_PATH, "resources")
ICONS_THEME = "token_light"
ICONS_PATH = os.path.join(RESOURCE_PATH, "icons", ICONS_THEME)
LIB_PATH = os.path.join(RESOURCE_PATH, "lib")
sys.path.append(LIB_PATH)

# we do special things for these skins
SKIN_DIR = xbmc.getSkinDir()
if (SKIN_DIR == "skin.confluence"):
    SKIN_NAME = "confluence"
elif (SKIN_DIR == "skin.metropolis"):
    SKIN_NAME = "metropolis"
else:
    SKIN_NAME = ""
view_mode = 0

from resources.lib.iphoto_parser import *
db_file = xbmc.translatePath(os.path.join(addon.getAddonInfo("Profile"), "iphoto.db"))
db = None

apple_epoch = 978307200

# ignore empty albums if configured to do so
album_ign_empty = addon.getSetting('album_ignore_empty')
if (album_ign_empty == ""):
    album_ign_empty = "true"
    addon.setSetting('album_ignore_empty', album_ign_empty)

# force configured sort method when set to "DEFAULT".
# XBMC sorts by file date when user selects "DATE" as the sort method,
# so we have no way to sort by the date stored in the XML or the EXIF
# data without providing an override to "DEFAULT".
# this works out well because I don't believe iPhoto stores the photos
# in the XML in any meaningful order anyway.
media_sort_col = addon.getSetting('default_sort_photo')
if (media_sort_col == ""):
    media_sort_col = "NULL"
    addon.setSetting('default_sort_photo', '0')
elif (media_sort_col == "1"):
    media_sort_col = "mediadate"
else:
    media_sort_col = "NULL"


def generic_context_menu_items(commands=[]):
    commands.append((addon.getLocalizedString(30217), "XBMC.RunPlugin(\""+BASE_URL+"?action=textview&file=README.txt\")",))
    commands.append((xbmc.getLocalizedString(1045), "XBMC.RunPlugin(\""+BASE_URL+"?action=settings\")",))

def slideshow_context_menu_args(mediakind='file', mediaid=None):
    if (mediaid is None):
	print "iPhoto: slideshow_context_menu_args: Trying to add item without media ID!"
	return None
    ss_args = "show=onthego&mediakind=%s&mediaid=%s" % (mediakind, mediaid)
    return ss_args

def slideshow_context_menu_item_add(commands=[], mediakind='file', mediaid=None):
    ss_args = slideshow_context_menu_args(mediakind, mediaid)
    if (ss_args is None):
	return
    commands.append((addon.getLocalizedString(30311), "XBMC.RunPlugin(\""+BASE_URL+"?action=slideshows&cmd=add&%s\")" % (ss_args),))

def slideshow_context_menu_item_del(commands=[], mediakind='file', mediaid=None):
    ss_args = slideshow_context_menu_args(mediakind, mediaid)
    if (ss_args is None):
	return
    commands.append((addon.getLocalizedString(30312), "XBMC.RunPlugin(\""+BASE_URL+"?action=slideshows&cmd=del&%s\")" % (ss_args),))

def slideshow_maint_context_menu_items(commands=[]):
    commands.append((addon.getLocalizedString(30310), "XBMC.RunPlugin(\""+BASE_URL+"?action=slideshows&show=onthego&cmd=clear\")",))

def generic_maint_context_menu_items(commands=[]):
    commands.append((addon.getLocalizedString(30213), "XBMC.RunPlugin(\""+BASE_URL+"?action=rescan\")",))
    commands.append((addon.getLocalizedString(30216), "XBMC.RunPlugin(\""+BASE_URL+"?action=resetdb\")",))
    commands.append((addon.getLocalizedString(30215), "XBMC.RunPlugin(\""+BASE_URL+"?action=rm_caches\")",))

def textview(file):
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    xbmc.executebuiltin("ActivateWindow(%d)" % (WINDOW))
    retries = 5
    while (gui.getCurrentWindowDialogId() != WINDOW and retries):
	retries -= 1
	xbmc.sleep(100)

    window = gui.Window(WINDOW)

    try:
	heading = os.path.splitext(os.path.basename(file))[0]
	text = open(os.path.join(PLUGIN_PATH, file)).read()
    except:
	print traceback.print_exc()
    else:
	try:
	    window.getControl(CONTROL_LABEL).setLabel("%s - %s" % (heading, __plugin__))
	except:
	    pass
	window.getControl(CONTROL_TEXTBOX).setText(text)

def md5sum(filename):
    try:
	m = md5()
    except:
	m = md5.new()
    with open(filename, 'rb') as f:
	for chunk in iter(lambda: f.read(128 * m.block_size), ''):
	    m.update(chunk)
    return m.hexdigest()

def render_media(media, in_slideshow=False):
    global view_mode

    if (not media):
	return 0

    # default view for select skins
    if (SKIN_NAME != ""):
	vm = addon.getSetting(SKIN_NAME + '_view_default')
	if (vm == ""):
	    addon.setSetting(SKIN_NAME + '_view_default', "0")
	else:
	    vm = int(vm)
	    if (SKIN_NAME == "confluence"):
		if (vm == 1):
		    view_mode = 514	    # Pic Thumbs
		elif (vm == 2):
		    view_mode = 510	    # Image Wrap
	    if (SKIN_NAME == "metropolis"):
		if (vm == 1):
		    view_mode = 500	    # Picture Grid
		elif (vm == 2):
		    view_mode = 59	    # Galary Fanart

    sort_date = False
    n = 0
    for (caption, mediapath, thumbpath, originalpath, rating, mediadate, mediasize) in media:
	if (not mediapath):
	    mediapath = originalpath
	if (not thumbpath):
	    thumbpath = mediapath
	if (not caption):
	    caption = mediapath

	if (caption):
	    item = gui.ListItem(caption, thumbnailImage=thumbpath)

	    try:
		item_date = time.strftime("%d.%m.%Y", time.localtime(apple_epoch + float(mediadate)))
		#JSL: setting the date here to enable sorting prevents XBMC
		#JSL: from scanning the EXIF/IPTC info
		#item.setInfo(type="pictures", infoLabels={ "date": item_date })
		#sort_date = True
	    except:
		pass

	    commands = []
	    if (in_slideshow == False):
		slideshow_context_menu_item_add(commands, 'file', mediapath)
	    else:
		slideshow_context_menu_item_del(commands, 'file', mediapath)
	    slideshow_maint_context_menu_items(commands)
	    item.addContextMenuItems(commands, False)

	    plugin.addDirectoryItem(handle = int(sys.argv[1]), url = mediapath, listitem = item, isFolder = False)
	    n += 1

    if (n > 0):
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_UNSORTED)
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_LABEL)
	if (sort_date == True):
	    plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_DATE)

    # default view in Confluence
    vm = addon.getSetting('view_mode')
    if (vm == ""):
	vm = "0"
	addon.setSetting('view_mode', vm)
    vm = int(vm)
    if (vm == 1):
	view_mode = 510
    elif (vm == 2):
	view_mode = 514
    else:
	view_mode = vm

    return n

def photo_list(mediakind, mediaid):
    global db, media_sort_col

    media = []
    if (mediakind == 'file'):
	media = db.GetMedia(mediaid, media_sort_col)
    elif (mediakind == 'album'):
	media = db.GetMediaInAlbum(mediaid, media_sort_col)
    elif (mediakind == 'event'):
	media = db.GetMediaInEvent(mediaid, media_sort_col)
    elif (mediakind == 'face'):
	media = db.GetMediaWithFace(mediaid, media_sort_col)
    elif (mediakind == 'place'):
	media = db.GetMediaWithPlace(mediaid, media_sort_col)
    elif (mediakind == 'keyword'):
	media = db.GetMediaWithKeyword(mediaid, media_sort_col)
    elif (mediakind == 'rating'):
	media = db.GetMediaWithRating(mediaid, media_sort_col)
    elif (mediakind == 'slideshow'):
	print "XXX: Viewing slideshow '%s'" % (mediaid)

    return media

def album_list(params):
    global db, BASE_URL, ICONS_PATH, album_ign_empty, view_mode

    try:
	albumid = params['albumid']
	media = photo_list('album', albumid)
	return render_media(media)
    except:
	pass

    albums = db.GetAlbums()
    if (not albums):
	dialog = gui.Dialog()
	dialog.ok(addon.getLocalizedString(30240), addon.getLocalizedString(30241))
	return

    n = 0
    for (albumid, name, count) in albums:
	if (name == "Photos"):
	    continue

	if (not count and album_ign_empty == "true"):
	    continue

	thumbpath = ICONS_PATH+"/folder.png"
	item = gui.ListItem(name, thumbnailImage=thumbpath)
	commands = []
	generic_context_menu_items(commands)
	slideshow_context_menu_item_add(commands, 'album', albumid)
	slideshow_maint_context_menu_items(commands)
	item.addContextMenuItems(commands, True)
	plugin.addDirectoryItem(handle = int(sys.argv[1]), url=BASE_URL+"?action=albums&albumid=%s" % (albumid), listitem = item, isFolder = True, totalItems = count)
	n += 1

    if (n > 0):
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_UNSORTED)
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_LABEL)

    # default view for select skins
    if (SKIN_NAME != ""):
	if (addon.getSetting(SKIN_NAME + '_view_albums') == ""):
	    if (SKIN_NAME == "confluence"):
		view_mode = 51			# Big List
	    elif (SKIN_NAME == "metropolis"):
		view_mode = 0
	    addon.setSetting(SKIN_NAME + '_view_albums', str(view_mode))

    return n

def event_list(params):
    global db, BASE_URL, album_ign_empty, view_mode

    try:
	eventid = params['eventid']
	media = photo_list('event', eventid)
	return render_media(media)
    except:
	pass

    events = db.GetEvents()
    if (not events):
	dialog = gui.Dialog()
	dialog.ok(addon.getLocalizedString(30240), addon.getLocalizedString(30241))
	return

    sort_date = False
    n = 0
    for (eventid, name, thumbpath, eventdate, count) in events:
	if (not count and album_ign_empty == "true"):
	    continue

	item = gui.ListItem(name, thumbnailImage=thumbpath)
	commands = []
	generic_context_menu_items(commands)
	slideshow_context_menu_item_add(commands, 'event', eventid)
	slideshow_maint_context_menu_items(commands)
	item.addContextMenuItems(commands, True)

	try:
	    item_date = time.strftime("%d.%m.%Y", time.localtime(apple_epoch + float(eventdate)))
	    item.setInfo(type="pictures", infoLabels={ "date": item_date })
	    sort_date = True
	except:
	    pass

	plugin.addDirectoryItem(handle = int(sys.argv[1]), url=BASE_URL+"?action=events&eventid=%s" % (eventid), listitem = item, isFolder = True, totalItems = count)
	n += 1

    if (n > 0):
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_UNSORTED)
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_LABEL)
	if (sort_date == True):
	    plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_DATE)

    # default view for select skins
    if (SKIN_NAME != ""):
	if (addon.getSetting(SKIN_NAME + '_view_events') == ""):
	    if (SKIN_NAME == "confluence"):
		view_mode = 0
	    elif (SKIN_NAME == "metropolis"):
		view_mode = 0
	    addon.setSetting(SKIN_NAME + '_view_events', str(view_mode))

    return n

def face_list(params):
    global db, BASE_URL, album_ign_empty, view_mode

    try:
	faceid = params['faceid']
	media = photo_list('face', faceid)
	return render_media(media)
    except:
	pass

    faces = db.GetFaces()
    if (not faces):
	dialog = gui.Dialog()
	dialog.ok(addon.getLocalizedString(30240), addon.getLocalizedString(30241))
	return

    n = 0
    for (faceid, name, thumbpath, count) in faces:
	if (not count and album_ign_empty == "true"):
	    continue

	item = gui.ListItem(name, thumbnailImage=thumbpath)
	commands = []
	generic_context_menu_items(commands)
	slideshow_context_menu_item_add(commands, 'face', faceid)
	slideshow_maint_context_menu_items(commands)
	item.addContextMenuItems(commands, True)

	plugin.addDirectoryItem(handle = int(sys.argv[1]), url=BASE_URL+"?action=faces&faceid=%s" % (faceid), listitem = item, isFolder = True, totalItems = count)
	n += 1

    if (n > 0):
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_UNSORTED)
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_LABEL)

    # default view for select skins
    if (SKIN_NAME != ""):
	if (addon.getSetting(SKIN_NAME + '_view_faces') == ""):
	    if (SKIN_NAME == "confluence"):
		view_mode = 500			# Thumbnails
	    elif (SKIN_NAME == "metropolis"):
		view_mode = 59			# Gallary Fanart
	    addon.setSetting(SKIN_NAME + '_view_faces', str(view_mode))

    return n

def place_list(params):
    global db, BASE_URL, album_ign_empty, view_mode

    try:
	placeid = params['placeid']
	media = photo_list('place', placeid)
	return render_media(media)
    except:
	pass

    # how to display Places labels:
    # 0 = Addresses
    # 1 = Latitude/Longitude Pairs
    places_labels = addon.getSetting('places_labels')
    if (places_labels == ""):
	places_labels = "0"
	addon.setSetting('places_labels', places_labels)
    places_labels = int(places_labels)

    # show big map of Place as fanart for each item?
    show_fanart = True
    e = addon.getSetting('places_show_fanart')
    if (e == ""):
	addon.setSetting('places_show_fanart', "true")
    elif (e == "false"):
	show_fanart = False

    places = db.GetPlaces()
    if (not places):
	dialog = gui.Dialog()
	dialog.ok(addon.getLocalizedString(30240), addon.getLocalizedString(30241))
	return

    n = 0
    for (placeid, latlon, address, thumbpath, fanartpath, count) in places:
	if (not count and album_ign_empty == "true"):
	    continue

	latlon = latlon.replace("+", " ")

	if (places_labels == 1):
	    item = gui.ListItem(latlon, address)
	else:
	    item = gui.ListItem(address, latlon)
	if (thumbpath):
	    item.setThumbnailImage(thumbpath)
	if (show_fanart == True and fanartpath):
	    item.setProperty("Fanart_Image", fanartpath)

	commands = []
	generic_context_menu_items(commands)
	slideshow_context_menu_item_add(commands, 'place', placeid)
	slideshow_maint_context_menu_items(commands)
	item.addContextMenuItems(commands, True)

	plugin.addDirectoryItem(handle = int(sys.argv[1]), url=BASE_URL+"?action=places&placeid=%s" % (placeid), listitem = item, isFolder = True, totalItems = count)
	n += 1

    if (n > 0):
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_UNSORTED)
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_LABEL)

    # default view for select skins
    if (SKIN_NAME != ""):
	if (addon.getSetting(SKIN_NAME + '_view_places') == ""):
	    if (SKIN_NAME == "confluence"):
		view_mode = 500			# Thumbnails
	    elif (SKIN_NAME == "metropolis"):
		view_mode = 59			# Gallary Fanart
	    addon.setSetting(SKIN_NAME + '_view_places', str(view_mode))

    return n

def hide_keyword(keyword):
    try:
	hidden_keywords = addon.getSetting('hidden_keywords')
	if (hidden_keywords != ""):
	    hidden_keywords += ", "
	hidden_keywords += keyword
	addon.setSetting('hidden_keywords', hidden_keywords)
    except Exception, e:
	print to_str(e)
	pass

def keyword_list(params):
    global db, BASE_URL, ICONS_PATH, album_ign_empty, view_mode

    try:
	keyword = params['hide']
	hide_keyword(keyword);
	xbmc.executebuiltin("Container.Refresh")
	return 0
    except:
	pass

    try:
	keywordid = params['keywordid']
	media = photo_list('keyword', keywordid)
	return render_media(media)
    except:
	pass

    keywords = db.GetKeywords()
    if (not keywords):
	dialog = gui.Dialog()
	dialog.ok(addon.getLocalizedString(30240), addon.getLocalizedString(30241))
	return

    hidden_keywords = addon.getSetting('hidden_keywords')

    n = 0
    for (keywordid, keyword, count) in keywords:
	if (keyword in hidden_keywords):
	    continue

	if (not count and album_ign_empty == "true"):
	    continue

	thumbpath = ICONS_PATH+"/folder.png"
	item = gui.ListItem(keyword, thumbnailImage=thumbpath)
	commands = []
	generic_context_menu_items(commands)
	slideshow_context_menu_item_add(commands, 'keyword', keywordid)
	slideshow_maint_context_menu_items(commands)
	commands.append((addon.getLocalizedString(30214), "XBMC.RunPlugin(\""+BASE_URL+"?action=keywords&hide=%s\")" % (keyword),))
	item.addContextMenuItems(commands, True)
	plugin.addDirectoryItem(handle = int(sys.argv[1]), url=BASE_URL+"?action=keywords&keywordid=%s" % (keywordid), listitem = item, isFolder = True, totalItems = count)
	n += 1

    if (n > 0):
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_UNSORTED)
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_LABEL)

    # default view for select skins
    if (SKIN_NAME != ""):
	if (addon.getSetting(SKIN_NAME + '_view_keywords') == ""):
	    if (SKIN_NAME == "confluence"):
		view_mode = 51			# Big List
	    elif (SKIN_NAME == "metropolis"):
		view_mode = 0
	    addon.setSetting(SKIN_NAME + '_view_keywords', str(view_mode))

    return n

def rating_list(params):
    global db, BASE_URL, ICONS_PATH, view_mode

    try:
	ratingid = params['ratingid']
	media = photo_list('rating', ratingid)
	return render_media(media)
    except:
	pass

    n = 0
    for ratingid in range(1,6):
	thumbpath = ICONS_PATH+"/star%d.png" % (ratingid)
	item = gui.ListItem(addon.getLocalizedString(30200) % (ratingid), thumbnailImage=thumbpath)
	commands = []
	generic_context_menu_items(commands)
	slideshow_context_menu_item_add(commands, 'rating', ratingid)
	slideshow_maint_context_menu_items(commands)
	item.addContextMenuItems(commands, True)
	plugin.addDirectoryItem(handle = int(sys.argv[1]), url=BASE_URL+"?action=ratings&ratingid=%d" % (ratingid), listitem = item, isFolder = True)
	n += 1

    if (n > 0):
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_UNSORTED)
	plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_LABEL)

    # default view for select skins
    if (SKIN_NAME != ""):
	if (addon.getSetting(SKIN_NAME + '_view_ratings') == ""):
	    if (SKIN_NAME == "confluence"):
		view_mode = 51			# Big List
	    elif (SKIN_NAME == "metropolis"):
		view_mode = 0
	    addon.setSetting(SKIN_NAME + '_view_ratings', str(view_mode))

    return n

def slideshow_clear(show):
    print "XXX: Clearing slideshow '%s'." % (show)
    return 0

def slideshow_add(show, mediakind, mediaid):
    print "XXX: Adding to slideshow '%s':" % (show)
    media = photo_list(mediakind, mediaid)
    print media

def slideshow_del(show, mediakind, mediaid):
    print "XXX: Deleting from slideshow '%s':" % (show)
    media = photo_list(mediakind, mediaid)
    print media

def slideshow_list(params):
    try:
	show = params['show']
	command = params['cmd']
	if (command == 'clear'):
	    return slideshow_clear(show)
	mediakind = params['mediakind']
	mediaid = params['mediaid']
    except:
	pass
    else:
	if (command == 'add'):
	    slideshow_add(show, mediakind, mediaid)
	    return 0
	elif (command == 'del'):
	    slideshow_del(show, mediakind, mediaid)
	    xbmc.executebuiltin("Container.Refresh")
	    return 0

    media = photo_list('slideshow', 'onthego')
    return render_media(media, in_slideshow=True)

def import_progress_callback(progress_dialog, altinfo, nphotos, ntotal):
    if (not progress_dialog):
	return 0
    if (progress_dialog.iscanceled()):
	return

    percent = int(float(nphotos * 100) / ntotal)
    progress_dialog.update(percent, addon.getLocalizedString(30211) % (nphotos), altinfo)
    return nphotos

def import_library(xmlpath, xmlfile, masterspath, masters_realpath, enable_places):
    global db

    # crude locking to prevent multiple simultaneous library imports
    if (xbmc.getInfoLabel("Window(10000).Property(iphoto_scanning)") == "True"):
	print "iPhoto: Library import already in progress."
	return
    else:
	gui.Window(10000).setProperty("iphoto_scanning", "True")

    # always ignore Books and currently selected album
    album_ign = []
    album_ign.append("Book")
    album_ign.append("Selected Event Album")

    # ignore albums published to MobileMe if configured to do so
    album_ign_publ = addon.getSetting('album_ignore_published')
    if (album_ign_publ == ""):
	album_ign_publ = "true"
	addon.setSetting('album_ignore_published', album_ign_publ)
    if (album_ign_publ == "true"):
	album_ign.append("Published")

    # ignore flagged albums if configured to do so
    album_ign_flagged = addon.getSetting('album_ignore_flagged')
    if (album_ign_flagged == ""):
	album_ign_flagged = "true"
	addon.setSetting('album_ignore_flagged', album_ign_flagged)
    if (album_ign_flagged == "true"):
	album_ign.append("Shelf")

    # download maps from Google?
    enable_maps = True
    e = addon.getSetting('places_enable_maps')
    if (e == ""):
	addon.setSetting('places_enable_maps', "true")
    elif (e == "false"):
	enable_maps = False
    if (enable_maps == True):
	res_x = float(xbmc.getInfoLabel("System.ScreenWidth"))
	res_y = float(xbmc.getInfoLabel("System.ScreenHeight"))
	map_aspect = res_x / res_y
    else:
	map_aspect = 0.0

    try:
	# try to get progress dialog actually on-screen before we do work
	retries = 10
	progress_dialog = None
	while (gui.getCurrentWindowDialogId() != 10101 and retries):
	    if (not progress_dialog):
		progress_dialog = gui.DialogProgress()
		progress_dialog.create(addon.getLocalizedString(30210))
	    retries -= 1
	    xbmc.sleep(100)
    except:
	print traceback.print_exc()
    else:
	iparser = IPhotoParser(xmlpath, xmlfile, masterspath, masters_realpath, album_ign, enable_places, map_aspect, db.AddAlbumNew, db.AddEventNew, db.AddFaceNew, db.AddKeywordNew, db.AddMediaNew, import_progress_callback, progress_dialog)

	try:
	    progress_dialog.update(0, addon.getLocalizedString(30219))
	    db.ResetDB()

	    progress_dialog.update(0, addon.getLocalizedString(30212))
	    iparser.Parse()
	except:
	    print traceback.print_exc()
	    print "iPhoto: Library parse failed."
	    progress_dialog.close()
	    gui.Window(10000).setProperty("iphoto_scanning", "False")
	    xbmc.executebuiltin("XBMC.RunPlugin(%s?action=resetdb&corrupted=1)" % (BASE_URL))
	else:
	    print "iPhoto: Library imported successfully."
	    progress_dialog.close()
	    gui.Window(10000).setProperty("iphoto_scanning", "False")
	    try:
		# this is non-critical
		db.UpdateLastImport()
	    except:
		pass

def reset_db(params):
    try:
	if (params['noconfirm']):
	    confirm = False
    except:
	confirm = True

    try:
	if (params['corrupted']):
	    corrupted = True
    except:
	corrupted = False

    confirmed = True
    if (confirm):
	dialog = gui.Dialog()
	if (corrupted):
	    confirmed = dialog.yesno(addon.getLocalizedString(30230), addon.getLocalizedString(30231), addon.getLocalizedString(30232), addon.getLocalizedString(30233))
	else:
	    confirmed = dialog.yesno(addon.getLocalizedString(30230), addon.getLocalizedString(30232), addon.getLocalizedString(30233))

    if (confirmed):
	if (xbmc.getInfoLabel("Window(10000).Property(iphoto_scanning)") == "True"):
	    dialog = gui.Dialog()
	    dialog.ok(addon.getLocalizedString(30260), addon.getLocalizedString(30261))
	    print "iPhoto: Library import in progress; not resetting database."
	    return

	remove_tries = 3
	while (remove_tries and os.path.isfile(db_file)):
	    try:
		os.remove(db_file)
	    except:
		remove_tries -= 1
		xbmc.sleep(1000)
	    else:
		print "iPhoto addon database deleted."

def get_params(paramstring):
    params = {}
    paramstring = str(paramstring).strip()
    paramstring = paramstring.lstrip("?")
    if (not paramstring):
	return params
    paramlist = paramstring.split("&")
    for param in paramlist:
	(k,v) = param.split("=")
	params[k] = v
    print "iPhoto: called with parameters:"
    print params
    return params

if (__name__ == "__main__"):
    xmlpath = addon.getSetting('albumdata_xml_path')
    if (xmlpath == ""):
	try:
	    xmlpath = os.getenv("HOME") + "/Pictures/iPhoto Library/"
	    addon.setSetting('albumdata_xml_path', xmlpath)
	except:
	    pass
	addon.openSettings(BASE_URL)

    # we used to store the file path to the XML instead of the iPhoto Library directory.
    if (os.path.basename(xmlpath) == ALBUM_DATA_XML):
	xmlpath = os.path.dirname(xmlpath)
	addon.setSetting('albumdata_xml_path', xmlpath)

    origxml = os.path.join(xmlpath, ALBUM_DATA_XML)
    xmlfile = xbmc.translatePath(os.path.join(addon.getAddonInfo("Profile"), "iphoto.xml"))

    enable_managed_lib = True
    e = addon.getSetting('managed_lib_enable')
    if (e == ""):
	addon.setSetting('managed_lib_enable', "true")
    elif (e == "false"):
	enable_managed_lib = False

    masterspath = ""
    masters_realpath = ""
    if (enable_managed_lib == False):
	masterspath = addon.getSetting('masters_path')
	masters_realpath = addon.getSetting('masters_real_path')
	if (masterspath == "" or masters_realpath == ""):
	    addon.setSetting('managed_lib_enable', "true")
	    enable_managed_lib = True
	    masterspath = ""
	    masters_realpath = ""

    enable_places = True
    e = addon.getSetting('places_enable')
    if (e == ""):
	addon.setSetting('places_enable', "true")
    elif (e == "false"):
	enable_places = False

    try:
	params = get_params(sys.argv[2])
	action = params['action']
    except:
	# main menu
	try:
	    commands = []
	    generic_context_menu_items(commands)
	    slideshow_maint_context_menu_items(commands)
	    generic_maint_context_menu_items(commands)

	    item = gui.ListItem(addon.getLocalizedString(30100), thumbnailImage=ICONS_PATH+"/events.png")
	    item.addContextMenuItems(commands, True)
	    plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=events", item, True)

	    item = gui.ListItem(addon.getLocalizedString(30101), thumbnailImage=ICONS_PATH+"/albums.png")
	    item.addContextMenuItems(commands, True)
	    plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=albums", item, True)

	    item = gui.ListItem(addon.getLocalizedString(30105), thumbnailImage=ICONS_PATH+"/faces.png")
	    item.addContextMenuItems(commands, True)
	    plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=faces", item, True)

	    item = gui.ListItem(addon.getLocalizedString(30106), thumbnailImage=ICONS_PATH+"/places.png")
	    item.addContextMenuItems(commands, True)
	    plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=places", item, True)

	    item = gui.ListItem(addon.getLocalizedString(30104), thumbnailImage=ICONS_PATH+"/keywords.png")
	    item.addContextMenuItems(commands, True)
	    plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=keywords", item, True)

	    item = gui.ListItem(addon.getLocalizedString(30102), thumbnailImage=ICONS_PATH+"/star.png")
	    item.addContextMenuItems(commands, True)
	    plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=ratings", item, True)

	    item = gui.ListItem(addon.getLocalizedString(30108), thumbnailImage=ICONS_PATH+"/slideshow.png")
	    item.addContextMenuItems(commands, True)
	    plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=slideshows", item, True)

	    hide_item = addon.getSetting('hide_import_lib')
	    if (hide_item == ""):
		hide_item = "false"
		addon.setSetting('hide_import_lib', hide_item)
	    if (hide_item == "false"):
		item = gui.ListItem(addon.getLocalizedString(30103), thumbnailImage=ICONS_PATH+"/update.png")
		item.addContextMenuItems(commands, True)
		plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=rescan", item, False)

	    hide_item = addon.getSetting('hide_view_readme')
	    if (hide_item == ""):
		hide_item = "false"
		addon.setSetting('hide_view_readme', hide_item)
	    if (hide_item == "false"):
		item = gui.ListItem(addon.getLocalizedString(30107), thumbnailImage=ICONS_PATH+"/help.png")
		item.addContextMenuItems(commands, True)
		plugin.addDirectoryItem(int(sys.argv[1]), BASE_URL+"?action=textview&file=README.txt", item, False)
	except:
	    plugin.endOfDirectory(int(sys.argv[1]), False)
	else:
	    plugin.addSortMethod(int(sys.argv[1]), plugin.SORT_METHOD_NONE)
	    plugin.endOfDirectory(int(sys.argv[1]), True)

	# automatically update library if desired
	auto_update_lib = addon.getSetting('auto_update_lib')
	if (auto_update_lib == ""):
	    auto_update_lib = "false"
	    addon.setSetting('auto_update_lib', auto_update_lib)
	if (auto_update_lib == "true"):
	    tmpfile = xmlfile + ".new"
	    copyfile(origxml, tmpfile)
	    if (os.path.isfile(xmlfile) and md5sum(tmpfile) == md5sum(xmlfile)):
		os.remove(tmpfile)
	    else:
		os.rename(tmpfile, xmlfile)
		try:
		    db = IPhotoDB(db_file)
		except:
		    dialog = gui.Dialog()
		    dialog.ok(addon.getLocalizedString(30240), addon.getLocalizedString(30241))
		    xbmc.executebuiltin('XBMC.RunPlugin(%s?action=resetdb&noconfirm=1)' % BASE_URL)
		else:
		    import_library(xmlpath, xmlfile, masterspath, masters_realpath, enable_places)
    else:
	items = None

	# actions that don't require a database connection
	if (action == "resetdb"):
	    reset_db(params)
	elif (action == "rm_caches"):
	    progress_dialog = gui.DialogProgress()
	    try:
		progress_dialog.create(addon.getLocalizedString(30250))
		progress_dialog.update(0, addon.getLocalizedString(30252))
	    except:
		print traceback.print_exc()
	    else:
		r = glob.glob(os.path.join(os.path.dirname(db_file), "map_*"))
		ntotal = len(r)
		nfiles = 0
		for f in r:
		    if (progress_dialog.iscanceled()):
			break
		    nfiles += 1
		    percent = int(float(nfiles * 100) / ntotal)
		    progress_dialog.update(percent, addon.getLocalizedString(30251) % (nfiles), os.path.basename(f))
		    os.remove(f)
		progress_dialog.close()
		dialog = gui.Dialog()
		dialog.ok(addon.getLocalizedString(30250), addon.getLocalizedString(30251) % (nfiles))
		print "iPhoto: deleted %d cached map image files." % (nfiles)
	elif (action == "textview"):
	    try:
		file = params['file']
	    except Exception, e:
		print to_str(e)
	    else:
		textview(file)
	elif (action == "settings"):
	    addon.openSettings(BASE_URL)
	else:
	    # actions that do require a database connection
	    try:
		db = IPhotoDB(db_file)
	    except:
		dialog = gui.Dialog()
		dialog.ok(addon.getLocalizedString(30240), addon.getLocalizedString(30241))
		xbmc.executebuiltin('XBMC.RunPlugin(%s?action=resetdb&noconfirm=1)' % BASE_URL)
	    else:
		if (action == "rescan"):
		    copyfile(origxml, xmlfile)
		    import_library(xmlpath, xmlfile, masterspath, masters_realpath, enable_places)
		elif (action == "events"):
		    items = event_list(params)
		elif (action == "albums"):
		    items = album_list(params)
		elif (action == "faces"):
		    items = face_list(params)
		elif (action == "places"):
		    if (enable_places == True):
			items = place_list(params)
		    else:
			dialog = gui.Dialog()
			ret = dialog.yesno(addon.getLocalizedString(30220), addon.getLocalizedString(30221), addon.getLocalizedString(30222), addon.getLocalizedString(30223))
			if (ret == True):
			    enable_places = True
			    addon.setSetting('places_enable', "true")
		elif (action == "keywords"):
		    items = keyword_list(params)
		elif (action == "ratings"):
		    items = rating_list(params)
		elif (action == "slideshows"):
		    items = slideshow_list(params)

	if (items):
	    plugin.endOfDirectory(int(sys.argv[1]), True)
	    if (view_mode):
		xbmc.sleep(300)
		xbmc.executebuiltin("Container.SetViewMode(%d)" % (view_mode))

# vim: tabstop=8 softtabstop=4 shiftwidth=4 noexpandtab:
