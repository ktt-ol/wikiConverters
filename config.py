# -*- coding: utf-8 -*-
__author__ = 'holger'

from time import gmtime, strftime

DEFAULT_USER = "unknown"

COMMENT = "Converted from Confluence"

PAGE_PREFIX = u"{i} This page was converted from Confluence at %s. The formatting may be broken. Internal links are most likely broken. If you have reviewed this page and the formatting & links are ok, you can remove this information.\n----\n" % strftime("%d.%m.%Y %H:%M:%S", gmtime())

# current key -> new key
SPACES = {
    "pub": "public",
    "mainframe": "mainframe",
    "intern": "intern",
    "minutes": "protokolle",
    "besch": "beschluesse",
    "tec": "technik"
}