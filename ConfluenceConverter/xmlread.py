#!/usr/bin/env python

"""
A SAX-based parser framework.

Copyright (C) 2012 Paul Boddie <paul@boddie.org.uk>

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation; either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
details.

You should have received a copy of the GNU Lesser General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__version__ = "0.1"

import xml.sax

class Parser(xml.sax.handler.ContentHandler):

    "A basic parser, tracking elements and attributes."

    def __init__(self):
        self.elements = []
        self.attributes = []
        self.text = []

    def startElement(self, name, attrs):
        self.elements.append(name)
        self.attributes.append(attrs)
        self.text.append([])

    def characters(self, content):
        self.text[-1].append(content)

    def endElement(self, name):
        self.handleElement(name)
        self.elements.pop()
        self.attributes.pop()
        self.text.pop()

    def handleElement(self, name):

        "Handle a completed element having the given 'name'."

        pass

    def parse(self, f):

        "Parse content from the file object 'f' using reasonable defaults."

        try:
            parser = xml.sax.make_parser()
            parser.setContentHandler(self)
            parser.setErrorHandler(xml.sax.handler.ErrorHandler())
            parser.setFeature(xml.sax.handler.feature_external_ges, 0)
            parser.parse(f)
        finally:
            f.close()

class ConfigurableParser(Parser):

    "A parser which can be configured to handle elements individually."

    def __init__(self, handlers=None):
        Parser.__init__(self)
        self.handlers = handlers or {}

    def __setitem__(self, name, handler):
        self.handlers[name] = handler

    def update(self, handlers):
        self.handlers.update(handlers)

    def handleElement(self, name):

        """
        Handle a completed element having the given 'name'. If a handler has
        been registered for the name on this object, the handler will be invoked
        with...

          * 'name' (the current element name)
          * the path to and including the current element (a list of names)
          * the attributes for elements in the path (a list of dictionaries, one
            for each element)
          * the text fragments for elements in the path (a list of lists, one
            list of fragments for each element)
          * the final textual content for the current element

        Where a handler has been registered for None, it will be called for any
        element without a specific handler.
        """

        for n in (name, None):
            handler = self.handlers.get(n)
            if handler:
                handler(name, self.elements, self.attributes, self.text, "".join(self.text[-1]))
                break

# vim: tabstop=4 expandtab shiftwidth=4
