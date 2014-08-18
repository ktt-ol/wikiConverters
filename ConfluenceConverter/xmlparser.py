#!/usr/bin/env python

"""
Confluence Wiki XML/XHTML syntax parsing.

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

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

#from MoinMoin import wikiutil
from common import *
from xmlread import Parser
import re
import sys
import operator
import htmlentitydefs
import codecs

# XML dialect syntax parsing.

tags = {
    # XHTML tag               MoinMoin syntax
    "strong"                : "'''%s'''",
    "em"                    : "''%s''",
    "u"                     : "__%s__",
    "del"                   : "--(%s)--",
    "sup"                   : "^%s^",
    "sub"                   : ",,%s,,",
    "code"                  : "`%s`",
    "tbody"                 : "%s",
    "tr"                    : "%s",
    "th"                    : "'''%s'''",
    "td"                    : "%s",
    "blockquote"            : " %s",
    "small"                 : "~-%s-~",
    "big"                   : "~+%s+~",
    "p"                     : "%s",
    "ol"                    : "%s",
    "ul"                    : "%s",
    "ac:link"               : "[[%s%s%s|%s]]",
    "ac:image"              : "{{%s%s%s|%s}}",
    "a"                     : "[[%s|%s]]",
    }

for tag, translation in blocktypes.items():
    tags[tag] = translation

simple_tags = {
    # XHTML tag               MoinMoin syntax
    "br"                    : "<<BR>>",
    }

simple_preformatted_tags = {
    # XHTML tag               MoinMoin syntax
    "br"                    : "\n",
    }

list_tags = {
    # XHTML list tag          MoinMoin list item syntax
    "ol"                    : "1. %s",
    "ul"                    : "* %s",
    }

preformatted_tags = ["pre", "ac:plain-text-body"]
single_level_tags = ["strong", "em", "u", "del", "sup", "sub", "code"]
formatted_tags    = ["ac:rich-text-body", "table"]

indented_tags = ["li", "p"] + preformatted_tags + formatted_tags
block_tags = indented_tags + blocktypes.keys() + list_tags.keys()
span_override_tags = ["ac:link"]

link_target_tags = {
    # Confluence element      Attributes providing the target
    "ri:page"               : ("ri:space-key", "ri:content-title"),
    "ri:attachment"         : ("ri:filename",),
    "ri:user"               : ("ri:username",),
    }

link_target_prefixes = {
    # Attribute with details  Prefix ensuring correct relative link
    "ri:space-key"          : "..",
    "ri:content-title"      : "..",
    }

link_label_attributes = "ri:content-title", "ac:link-body"

# NOTE: User links should support the intended user namespace prefix.

link_target_types = {
    # Confluence element      MoinMoin link prefix
    "ri:attachment"         : "attachment:",
    "ri:user"               : "",
    }

macro_rich_text_styles = {
    # Confluence style        MoinMoin admonition style
    "note"                  : "caution",
    "warning"               : "warning",
    "info"                  : "important",
    "tip"                   : "tip",
    "excerpt"               : "",
    }

macroargs = {
    # Confluence macro        Confluence and MoinMoin macro arguments
    "color"                 : ("color", "col"),
    }

macrotypes = {
    # Confluence macro        MoinMoin syntax
    "anchor"                : "<<Anchor(%(anchor)s)>>",
    "color"                 : "<<Color2(%(content)s, %(args)s)>>",
    "toc"                   : "<<TableOfContents>>",
    }

normalise_regexp_str = r"\s+"
normalise_regexp = re.compile(normalise_regexp_str)

class ConfluenceXMLParser(Parser):

    "Handle content from Confluence 4 page revisions."

    def __init__(self, out):
        Parser.__init__(self)
        self.out = out

        # Link target and label information.

        self.target = None
        self.target_type = None
        self.label = None

        # Macro information.

        self.macros = []
        self.macro_parameters = []
        self.held_anchors = []

        # Indentation and element nesting states.

        self.indents = [0]
        self.states = {}
        self.max_level = self.level = 0

        for name in preformatted_tags + single_level_tags:
            self.states[name] = 0

        # Table states.

        self.table_rows = 0
        self.table_columns = 0

        # Block states.

        self.have_block = False

    # ContentHandler-related methods.

    def startElement(self, name, attrs):

        # Track indentation for lists.

        if list_tags.has_key(name):
            self.indents.append(self.indents[-1] + 1)

        # Track element nesting.

        if self.states.has_key(name):
            self.states[name] += 1

        # Track cumulative element nesting in order to produce appropriate depth
        # indicators in the formatted output.

        if name in preformatted_tags or name in formatted_tags:
            self.level += 1
            self.max_level = max(self.level, self.max_level)

            # Reset indentation within regions.

            self.indents.append(0)

        if name in headings:
            self.held_anchors = []

        Parser.startElement(self, name, attrs)

        # Remember macro information for use within the element.

        if name == "ac:macro":
            self.macros.append(self.attributes[-1].get("ac:name"))
            self.macro_parameters.append({})

    def endElement(self, name):

        # Reset the indent for any preformatted/formatted region so that it may
        # itself be indented.

        if name in preformatted_tags or name in formatted_tags:
            self.indents.pop()

        Parser.endElement(self, name)

        if list_tags.has_key(name):
            self.indents.pop()

        if self.states.has_key(name):
            self.states[name] -= 1

        if name in preformatted_tags or name in formatted_tags:
            self.level -= 1
            if not self.level:
                self.max_level = 0

        # Discard macro state.

        if name == "ac:macro":
            self.macros.pop()
            self.macro_parameters.pop()

    def characters(self, content):
        if not self.is_preformatted():
            content = self.normalise(content, self.elements[-1])
        Parser.characters(self, content)

    def skippedEntity(self, name):
        ch = htmlentitydefs.name2codepoint.get(name)
        if ch:
            self.text[-1].append(unichr(ch))

    # Parser-related methods.

    def handleElement(self, name):

        """
        Handle the completion of the element with the given 'name'. Any content
        will either be recorded for later use (by an enclosing element, for
        example) or emitted in some form.
        """

        text = u"".join(self.text[-1])

        # Handle state.

        if name == "table":
            self.table_rows = 0
        elif name == "tr":
            self.table_columns = 0

        # Find conversions.

        conversion = None

        # Handle list elements.

        if name == "li" and len(self.elements) > 1:
            list_tag = self.elements[-2]
            conversion = list_tags.get(list_tag)

        # Remember link target information.

        elif link_target_tags.has_key(name):
            target_details = []

            # Get target details from the element's attributes.

            for attrname in link_target_tags[name]:
                attrvalue = self.attributes[-1].get(attrname)
                if attrvalue:

                    # Obtain a link label.

                    if attrname in link_label_attributes and not self.label:
                        self.label = attrvalue

                    # Validate any page title.

                    if attrname == "ri:content-title":
                        attrvalue = get_page_title(attrvalue)
                    target_details.append(attrvalue)

                    # Insert any prefix required for the link.

                    prefix = link_target_prefixes.get(attrname)
                    if prefix:
                        target_details.insert(0, prefix)

            # Make a link based on the details.

            self.target = u"/".join(target_details)
            self.target_type = name
            text = ""

        # For anchor links, just use the raw text and let Moin do the formatting.
        # Set an empty default target, overwriting it if enclosing elements
        # specify target details.

        elif name == "ac:link-body":
            self.target = self.target or ""
            self.label = text.strip()
            text = ""

        # For conventional links, remember the href attribute as the target.

        elif name == "a":
            self.target = self.attributes[-1].get("href")
            self.label = text.strip()
            text = ""

        # Remember macro information.

        elif name == "ac:parameter":
            self.macro_parameters[-1][self.attributes[-1].get("ac:name")] = text
            text = ""

        elif name == "ac:default-parameter":
            self.macro_parameters[-1][self.attributes[-2].get("ac:name")] = text
            text = ""

        # Handle single-level tags.

        elif name in single_level_tags and self.states[name] > 1:
            conversion = "%s"

        # Handle preformatted sections.

        elif name in preformatted_tags or name in formatted_tags:

            # Nest the section appropriately.

            level = 3 + self.max_level - self.level
            opening = "{" * level
            closing = "}" * level

            # Macro name information is used to style rich text body regions.

            if name != "table" and self.macros and macro_rich_text_styles.has_key(self.macros[-1]):
                details = macro_rich_text_styles[self.macros[-1]]
                title = self.macro_parameters[-1].get("title")
                if title:
                    details = "%s\n\n%s" % (details, title)

                conversion = "%s#!wiki %s\n\n%%s\n%s" % (opening, details, closing)

            elif name == "table":
                #conversion = "%s#!table\n%%s\n%s" % (opening, closing)
                conversion = "||%s||"

            else:
                # Preformatted sections containing newlines must contain an initial
                # newline.

                if text.find("\n") != -1 and not text.startswith("\n"):
                    opening += "\n"

                conversion = "%s%%s%s" % (opening, closing)

        # Handle the common case and simpler special cases.

        if not conversion:
            conversion = tags.get(name)



        # Attempt to convert the text.

        # Links require target information.

        if name in ("ac:link", "ac:image"):
            prefix = link_target_types.get(self.target_type, "")
            anchor = self.attributes[-1].get("ac:anchor") or ""
            label = self.label or text.strip() or self.target
            text = conversion % (prefix, self.target, anchor and ("#%s" % anchor) or "", label)
            self.target = self.target_type = self.label = None

        elif name == "a":
            text = conversion % (self.target, self.label or self.target)
            self.target = self.target_type = self.label = None

        # Macros require various kinds of information.
        # Some macros affect the formatting of their contents, whereas other
        # simpler macros are handled here.

        elif name == "ac:macro":
            # special handling for this macro, because sometimes some attributes are missing
            if self.macros[-1] == "status":
                parameters = {"content" : text}
                color = self.macro_parameters[-1].get("colour") or "grey"
                color = color.lower()
                title = self.macro_parameters[-1].get("title") or "-"
                text = "{{{#!wiki status/status-%s\n%s\n}}}" % (color, title)
            else:
                conversion = macrotypes.get(self.macros[-1])
                if conversion:
                    parameters = {"content" : text}
                    parameters.update(self.macro_parameters[-1])
                    argnames = macroargs.get(self.macros[-1])
                    if argnames:
                        confargname, moinargname = argnames
                        parameters["args"] = quote_macro_argument("%s=%s" % (moinargname, self.macro_parameters[-1][confargname]))
                    text = conversion % parameters
                    if self.macros[-1] == "anchor" and self.forbids_macros():
                        self.held_anchors.append(text)
                        text = ""

        # Handle the common cases for parameterised and unparameterised
        # substitutions.

        elif text and conversion:
            text = conversion % text
        elif simple_tags.has_key(name) and not self.is_preformatted():
            text = simple_tags[name]
        elif simple_preformatted_tags.has_key(name) and self.is_preformatted():
            text = simple_preformatted_tags[name]



        # Postprocess table columns and rows.

        if name in ("th", "td"):
            if self.table_columns:
                # text = "\n|| %s" % text
                text = "||%s" % text
            self.table_columns += 1
        elif name == "tr":
            if self.table_rows:
                # text = "\n==\n%s" % text
                text = "||\n||%s" % text
            self.table_rows += 1

        # Postprocess held anchor tags in headings.

        elif name in headings and self.held_anchors:
            text = "%s\n%s" % ("".join(self.held_anchors), text)



        # Normalise leading whitespace and indent the text if appropriate.

        if name in indented_tags:
            text = " " * self.indents[-1] + text.lstrip()

        # Add the converted text to the end of the parent element's text nodes.

        if len(self.text) > 1:
            nodes = self.text[-2]
            parent = self.elements[-2]

            # Where preceding text exists, add any blank line separators.

            if u"".join(nodes):

                # All top-level elements are separated with blank lines.

                if parent == "body":
                    nodes.append("\n")

                # Block elements always cause a new line to be started.

                if name in block_tags or self.have_block and name not in span_override_tags:
                    nodes.append("\n")

                self.have_block = False

            # Lists inside lists require separation.

            elif list_tags.has_key(name) and parent == "li":
                nodes.append("\n")

            # Without preceding text, save any block node state for non-block
            # elements so that newline separators can be added at another
            # level.

            elif name in block_tags and parent not in block_tags:
                self.have_block = True

            elif name not in block_tags and self.have_block and name not in span_override_tags:
                self.have_block = True

            else:
                self.have_block = False

            nodes.append(text)

        # Otherwise, emit the text (at the top level of the document).

        else:
            self.out.write(text)

    def is_preformatted(self):
        return reduce(operator.or_, [self.states[tag] for tag in preformatted_tags], False)

    def forbids_macros(self):
        return reduce(operator.or_, [(tag in headings or tag == "a") for tag in self.elements], False)

    # Whitespace normalisation.

    def get_replacement(self, name):
        if name in ("html", "body", "table", "tbody", "tr") or list_tags.has_key(name):
            return ""
        else:
            return " "

    def normalise(self, text, name):
        return normalise_regexp.sub(self.get_replacement(name), text)

def parse(s, out):

    "Parse the content in the string 's', writing a translation to 'out'."

    # NOTE: CDATA sections appear to have erroneous endings.
    s = s.replace("]] >", "]]>")
    s = u"""\
<?xml version="1.0"?>
<!DOCTYPE html 
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
%s
</body>
</html>""" % s

    f = StringIO(s.encode("utf-8"))
    try:
        parser = ConfluenceXMLParser(out)
        parser.parse(f)
    finally:
        f.close()

if __name__ == "__main__":
    s = codecs.getreader("utf-8")(sys.stdin).read()
    out = codecs.getwriter("utf-8")(sys.stdout)
    parse(s, out)

# vim: tabstop=4 expandtab shiftwidth=4
