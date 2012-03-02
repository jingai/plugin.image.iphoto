"""
    Common utility functions
"""

__author__ = "jingai <jingai@floatingpenguins.com>"
__credits__ = "Anoop Menon, Nuka1195, JMarshal, jingai"
__url__ = "git://github.com/jingai/plugin.image.iphoto.git"

def to_unicode(text):
    if (isinstance(text, unicode)):
	return text

    if (hasattr(text, '__unicode__')):
	return text.__unicode__()

    text = str(text)

    try:
	return unicode(text, 'utf-8')
    except UnicodeError:
	pass

    try:
	return unicode(text, locale.getpreferredencoding())
    except UnicodeError:
	pass

    return unicode(text, 'latin1')

def to_str(text):
    if (isinstance(text, str)):
	return text

    if (hasattr(text, '__unicode__')):
	text = text.__unicode__()

    if (hasattr(text, '__str__')):
	return text.__str__()

    return text.encode('utf-8')

# vim: tabstop=8 softtabstop=4 shiftwidth=4 noexpandtab:
