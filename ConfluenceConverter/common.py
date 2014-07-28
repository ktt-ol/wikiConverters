#!/usr/bin/env python

"""
Common parsing data.

Copyright (C) 2012, 2013 Paul Boddie <paul@boddie.org.uk>

This software is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 2 of
the License, or (at your option) any later version.

This software is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public
License along with this library; see the file LICENCE.txt
If not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
"""

MAX_TITLE_LENGTH = 120

URL_SCHEMES = ("http", "https", "ftp", "mailto")

# Translation helpers.

blocktypes = {
    "h1" : "= %s =",
    "h2" : "== %s ==",
    "h3" : "=== %s ===",
    "h4" : "==== %s ====",
    "h5" : "===== %s =====",
    "h6" : "====== %s ======",
    "bq" : "{{{%s}}}",
    }

headings = list(blocktypes.keys())
headings.remove("bq")

def get_page_title(title):
    return title[:MAX_TITLE_LENGTH].strip()

def quote_macro_argument(arg):
    if arg.find('"') != -1:
        return '"%s"' % arg.replace('"', '""')
    else:
        return arg

# vim: tabstop=4 expandtab shiftwidth=4
