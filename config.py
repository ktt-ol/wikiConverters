# -*- coding: utf-8 -*-
__author__ = 'holger'

from time import gmtime, strftime

DEFAULT_USER = "unknown"

COMMENT = "Converted from Confluence"

PAGE_PREFIX = u"{i} This page was converted from Confluence at %s. The formatting may be broken. If you have reviewed this page and the formatting is ok, you can remove this information.\n----\n" % strftime("%d.%m.%Y %H:%M:%S", gmtime())

