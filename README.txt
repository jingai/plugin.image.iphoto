iPhoto plugin for XBMC
======================
This plugin imports an iPhoto library into XBMC.  After importing, you will
see categories that correspond with their iPhoto counterparts:

* Events
* Albums
* Faces
* Places
* Keywords
* Ratings

Configuration
=============
The plugin needs to know where your AlbumData.xml file is.  If you haven't
explicitly pointed iPhoto to a non-standard library location, the default of
"~/Pictures/iPhoto Library/AlbumData.xml" should work fine.  Otherwise,
please enter in the correct path in the plugin's settings dialog.

The iPhoto plugin can also be configured to ignore certain album types.
It is currently hard-coded to ignore albums of type "Book" and
"Selected Event Album," but you can choose to ignore also:

* Empty -- albums with no pictures.
* Published -- MobileMe Gallery albums.
* Flagged -- albums flagged in iPhoto's interface.

All of these album types are ignored by default.

If you select "Auto update library", the plugin will compare the modification
time of your AlbumData.xml with its current database and update the database
automatically on start.  This is disabled by default, but is probably what
you want after testing the plugin.

You can also choose the view style for albums if you're using the Confluence
skin.  You may set this to "Image Wrap," "Pic Thumbs," or "Default".  If you
choose "Default," it will preserve whatever view mode you have chosen in XBMC
for each album; otherwise, it will force the view style to the one selected
here.

About Places support
====================
If the plugin is configured to support the Places feature of iPhoto, it will
parse the latitude/longitude pairs in iPhoto's database and look up the
corresponding addresses using Google.

If Google reports one or more businesses near the coordinates, the plugin
will use the name of the nearest business for the address to show in the
Places category.  Otherwise, the street address will be used.  In both cases,
the post code and country identifier are appended to the result.

For example, coordinates near Walt Disney World in Florida, USA will return:
    Walt Disney World, 32830, US

Addresses without a nearby business will look something like this:
    1234 Somewhere Ave, 90210, US

If there are several businesses near the latitude/longitude pair found in
iPhoto, it's possible that it may choose a location that is not what you were
expecting.  If this happens, try changing the location of the photo(s) in
iPhoto to a pair that is closer to the business or address you really wanted.

To verify that the latitude/longitude pair you are using will give the correct
results within the plugin, you can check the pair by using this URL:

    http://maps.google.com/maps?q=latitude+longitude

Substitute the actual latitude and longitude, of course.  For example:

    http://maps.google.com/maps?q=28.41889954+-81.58080292

The business name that will be used is the first entry listed under Places.
If no business name is listed, the street address will be used.

The Places feature also downloads map images to display while you're browsing
the Places category.  Normally, you won't need to do anything to get this
feature, besides enabling it in the plugin configuration.  But, if you import
your library many times within one day, Google may block you from retrieving
map images.  If you receive a map image with a red X over it, the plugin won't
re-download the map until you clear the map image caches.  You can do so by
selecting "Remove cached maps" from the context menu of the Places category.

Translations
============
If you'd like to help translate this plugin to another language, please send
a patch to jingai at floatingpenguins dot com.

If possible, patch against the most recent version at:

  http://github.com/jingai/plugin.image.iphoto

Known Issues
============
* Sorting by Date sorts on the file date, not the EXIF date.
  See http://trac.xbmc.org/ticket/10519
* Need icons for Faces, Places, and Keywords.
