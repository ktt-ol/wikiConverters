#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Converts the pages and attachments. No revisions or comments.
"""

__author__ = 'holger'

import xml.etree.ElementTree as ET
import time
import calendar
from os import makedirs, listdir
from os.path import join, exists
import re
import StringIO
import codecs

import wikiutil
import config
from ConfluenceConverter.xmlparser import parse





# from "convert.py"
def date_to_seconds(s):
    return calendar.timegm(time.strptime(s.split(".", 1)[0], "%Y-%m-%d %H:%M:%S"))


def getId(node):
    return node.find("./id").text


def getProp(node, name):
    return node.find("./property[@name='" + name + "']")


def getPropText(node, name):
    propNode = getProp(node, name)
    if propNode is None or propNode.text is None:
        return None

    return propNode.text


def print_safe(obj):
    if type(obj) is unicode:
        return obj.encode("utf-8")
    else:
        return str(obj)


def toString(obj, attributes):
    buffer = ""
    for val in attributes:
        s = print_safe(getattr(obj, val, "null"))
        buffer = buffer + val + ": " + s + ", "

    return buffer


class Space():
    all = {}

    def __init__(self, spaceNode):
        self.id = getId(spaceNode)
        self.name = getPropText(spaceNode, "name")
        self.key = getPropText(spaceNode, "key").lower()

        Space.all[self.id] = self

    @classmethod
    def getSpaceByKey(cls, spaceKey):
        spaceKey = spaceKey.lower()
        for id, space in cls.all.items():
            if space.key == spaceKey:
                return space

        raise StandardError("No Space found for key " + spaceKey)

    def __str__(self):
        return toString(self, ['id', 'key', 'name'])

    @classmethod
    def renameSpaces(cls, newSpaceKeyDic):
        for space in cls.all.values():
            space.key = newSpaceKeyDic[space.key]


class Page():
    all = {}
    topPages = {}

    def __init__(self, node):
        spaceProp = getProp(node, "space")
        if spaceProp is None:
            # only an old page
            return

        if getPropText(node, "contentStatus") != "current":
            # page may be deleted
            return

        self.id = getId(node)
        self.spaceId = getId(spaceProp)
        parent = getProp(node, "parent")
        if parent is not None:
            self.parentId = getId(parent)
        else:
            self.parentId = None
        self.title = getPropText(node, "title")
        self.contentId = self._readBody(node)
        name = getPropText(node, "lastModifierName")
        self.lastModifierId = MoinMoinUsers.all.get(name)
        if self.lastModifierId is None:
            self.lastModifierId = MoinMoinUsers.all.get(config.DEFAULT_USER)
        self.lastModificationDate = date_to_seconds(getPropText(node, "lastModificationDate"))

        Page.all[self.id] = self
        if self.parentId is None:
            # this page is a "Home" page
            Page.topPages[self.id] = self


    def _readBody(self, node):
        collection = node.find("./collection[@name='bodyContents']")
        if collection is None: raise BaseException("Page without body! " + self.id)
        element = collection.find("./element[@class='BodyContent']")
        if element is None: raise BaseException("Page without body! " + self.id)
        return getId(element)

    def __str__(self):
        return toString(self, ['id', 'title', 'spaceId', 'parent', 'contentId'])

    @classmethod
    def renameHomePages(cls):
        """
        rename all "Home" pages to their space key
        """
        for page in cls.topPages.values():
            if not page.title == "Home":
                continue
            # find space
            space = Space.all.get(page.spaceId)
            if space is None: raise StandardError("No space found for 'Home' page id " + page.spaceId)
            page.title = space.key


class Attachment():
    all = {}

    def __init__(self, node):
        self.id = getId(node)
        self.filename = getPropText(node, "fileName")

        Attachment.all[self.id] = self

    def __str__(self):
        return self.id + "//" + print_safe(self.filename)


class BodyContent():
    all = {}

    def __init__(self, node):
        self.id = getId(node)
        body = getPropText(node, "body")
        if body is None:
            body = ""
        self.body = body.strip()

        BodyContent.all[self.id] = self

    def __str__(self):
        return self.id + "//" + self.body[0:10] + "..."


class MoinMoinWriter():
    def __init__(self, outputFolder):
        self.outputFolder = outputFolder

    def writePage(self, pageId):
        page = Page.all.get(pageId)
        if page is None:
            raise BaseException("No page found: " + pageId)
        content = BodyContent.all.get(page.contentId)
        if content is None: raise BaseException("No Body content (id %s) found for page %s" % (page.contentId, pageId))

        space = Space.all.get(page.spaceId)
        if space is None: raise BaseException("No Space %s found for page %s" % (page.spaceId, pageId))

        pageName = self._makeFullPageName(page)
        pageNamePath = join(self.outputFolder, pageName)
        if exists(pageNamePath): raise StandardError("Page %s already exists in output folder. Will not overwrite anything." % pageName)

        moinmoinMarkup = StringIO.StringIO()
        parse(content.body, moinmoinMarkup)

        makedirs(pageNamePath)

        self._write(join(pageNamePath, "current"), "00000001")
        # http://moinmo.in/MoinDev/Storage
        self._write(join(pageNamePath, "edit-log"), "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
            page.lastModificationDate * 1000000,
            "00000001",
            "SAVENEW",
            pageName,
            "127.0.0.1",
            "127.0.0.1",
            page.lastModifierId,
            "",  # extra currently unused
            wikiutil.clean_input(config.COMMENT)
        ))

        revisionsPath = join(pageNamePath, "revisions")
        makedirs(revisionsPath)

        pageContent = moinmoinMarkup = self._addConvertPrefix(moinmoinMarkup.getvalue())
        self._write(join(revisionsPath, "00000001"), pageContent)

        # TODO: attachments

    def _addConvertPrefix(self, text):
        return config.PAGE_PREFIX + text


    def _write(self, filename, content):
        # encoding='utf-8'
        # with open(filename, "w") as file:
        # file.write(content)
        with codecs.open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

    def _makeFullPageName(self, page):
        path = ""
        currentPage = page
        while True:
            path = currentPage.title + "/" + path
            if currentPage.parentId is None:
                break

            nextPage = Page.all.get(currentPage.parentId)
            if nextPage is None: raise StandardError("No parent page %s found for page %s" % (currentPage.parentId, currentPage.id))
            currentPage = nextPage

        # remove last /
        path = path[0:-1]

        return wikiutil.quoteWikinameFS(path)

    def writePageForSpaces(self, spaceKeys):
        # find space ids
        validSpaceIds = {}
        for key in spaceKeys:
            id = Space.getSpaceByKey(key).id
            validSpaceIds[id] = True

        for page in Page.all.values():
            if not validSpaceIds.has_key(page.spaceId):
                continue

            self.writePage(page.id)


class MoinMoinUsers():
    USER_FILE_RE = re.compile(r'^[0-9\.]+$')

    # name -> id (= filename)
    all = {}

    def __init__(self, folder):
        self.folder = folder
        self._readUserFromFolder()

        if MoinMoinUsers.all.has_key(config.DEFAULT_USER) is False:
            raise RuntimeError("no default user (%s) found." % config.DEFAULT_USER)

    def _readUserFromFolder(self):
        MoinMoinUsers.all = {}
        for file in listdir(self.folder):
            if MoinMoinUsers.USER_FILE_RE.match(file) is None: continue
            name = self._getNameFromUserFile(join(self.folder, file))
            MoinMoinUsers.all[name] = file


    def _getNameFromUserFile(self, file):
        lookingFor = "name="
        with open(file, "r") as file:
            for line in file:
                if line.startswith(lookingFor):
                    # remove the newline also
                    return line[len(lookingFor):len(line) - 1]

        raise BaseException("No name= entry found!")


if __name__ == '__main__':
    # XML_FILE = "testdata/full/xmlexport-20140725-202414-6780/entities.xml"
    XML_FILE = "testdata/simple-confluence.xml"
    # current key -> new key
    SPACES = {
        "pub": "public",
        "mainframe": "mainframe",
        "intern": "intern",
        "minutes": "protokolle",
        "besch": "beschluesse",
        "tec": "technik"
    }

    MoinMoinUsers("/Users/holger/Dropbox/Proj/mainframe/wikiConverters/output/users")

    print("loading...")
    tree = ET.parse(XML_FILE)
    print("done")

    for obj in tree.findall("./object"):
        className = obj.attrib["class"]

        if className == "Space":
            Space(obj)
        elif className == "Page":
            Page(obj)
        elif className == "Attachment":
            Attachment(obj)
        elif className == "BodyContent":
            BodyContent(obj)

    Space.renameSpaces(SPACES)
    Page.renameHomePages()

    print("Spaces:")
    for space in Space.all.values():
        print(space)

    # print("Top Pages")
    # for topPage in Page.topPages.values():
    # print(topPage)

    # print("Pages:")
    # for page in Page.all.values():
    # print(page)

    # print("Contents:")
    # for content in BodyContent.all.values():
    # print(content)

    # print("Attachments")
    # for att in Attachment.all.values():
    #     print(att)


    writer = MoinMoinWriter("/Users/holger/Dropbox/Proj/mainframe/wikiConverters/output/pages")
    # writer.writePageForSpaces(SPACES.values())
    writer.writePage("13697061")
