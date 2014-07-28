# copied from MoinMoin 1.9.7 sources

import re

class config():
    charset = 'utf-8'

    clean_input_translation_map = {
        # these chars will be replaced by blanks
        ord(u'\t'): u' ',
        ord(u'\r'): u' ',
        ord(u'\n'): u' ',
        }
    for c in u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f' \
             '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f':
        # these chars will be removed
        clean_input_translation_map[ord(c)] = None
    del c


def taintfilename(basename):

    """
    Make a filename that is supposed to be a plain name secure, i.e.
    remove any possible path components that compromise our system.

    @param basename: (possibly unsafe) filename
    @rtype: string
    @return: (safer) filename
    """
    # note: filenames containing ../ (or ..\) are made safe by replacing
    # the / (or the \). the .. will be kept, but is harmless then.
    basename = re.sub('[\x00-\x1f:/\\\\<>"*?%|]', '_', basename)
    return basename


# Precompiled patterns for file name [un]quoting
UNSAFE = re.compile(r'[^a-zA-Z0-9_]+')
QUOTED = re.compile(r'\(([a-fA-F0-9]+)\)')


def quoteWikinameFS(wikiname, charset=config.charset):
    """ Return file system representation of a Unicode WikiName.

    Warning: will raise UnicodeError if wikiname can not be encoded using
    charset. The default value of config.charset, 'utf-8' can encode any
    character.

    @param wikiname: Unicode string possibly containing non-ascii characters
    @param charset: charset to encode string
    @rtype: string
    @return: quoted name, safe for any file system
    """
    filename = wikiname.encode(charset)

    quoted = []
    location = 0
    for needle in UNSAFE.finditer(filename):
        # append leading safe stuff
        quoted.append(filename[location:needle.start()])
        location = needle.end()
        # Quote and append unsafe stuff
        quoted.append('(')
        for character in needle.group():
            quoted.append('%02x' % ord(character))
        quoted.append(')')

    # append rest of string
    quoted.append(filename[location:])
    return ''.join(quoted)


def clean_input(text, max_len=201):
    """ Clean input:
        replace CR, LF, TAB by whitespace
        delete control chars

        @param text: unicode text to clean (if we get str, we decode)
        @rtype: unicode
        @return: cleaned text
    """
    # we only have input fields with max 200 chars, but spammers send us more
    length = len(text)
    if length == 0 or length > max_len:
        return u''
    else:
        if isinstance(text, str):
            # the translate() below can ONLY process unicode, thus, if we get
            # str, we try to decode it using the usual coding:
            text = text.decode(config.charset)
        return text.translate(config.clean_input_translation_map)

