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
from os.path import join, exists, dirname
import shutil
import re
import StringIO
import urllib
import argparse

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

def replace_non_ascii_chars(input):
    return re.sub(r'[^\x00-\x7F]+','_', input)

def toString(obj, attributes):
    buffer = ""
    for val in attributes:
        s = print_safe(getattr(obj, val, "null"))
        buffer = buffer + val + ": " + s + ", "

    return buffer


class IncompleteData(Exception):
    pass


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
            newKey = newSpaceKeyDic.get(space.key)
            if newKey is None:
                continue
            space.key = newKey


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
        # remove / from the page title
        self.title = re.sub(r'/','-', self.title)
        self.contentId = self._readBody(node)
        name = getPropText(node, "lastModifierName")
        self.lastModifierId = MoinMoinUsers.getUserIdForName(name)
        self.lastModificationDate = date_to_seconds(getPropText(node, "lastModificationDate"))

        self._readAttachments(node)

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

    def _readAttachments(self, node):
        self.attachments = []
        collection = node.find("./collection[@name='attachments']")
        if collection is None:
            return

        for attElement in collection.findall("./element[@class='Attachment']"):
            id = getId(attElement)
            self.attachments.append(id)


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
        self.lastModificationDate = date_to_seconds(getPropText(node, "lastModificationDate"))
        name = getPropText(node, "creatorName")
        self.creatorNameId = MoinMoinUsers.getUserIdForName(name)
        self.version = getPropText(node, "attachmentVersion")
        original = getProp(node, "originalVersion")
        if original is None:
            # this means that this is the most recent version
            self.originalVersion = None
        else:
            self.originalVersion = getId(node)

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
    def __init__(self, attachmentFolder, outputFolder):
        self.attachmentFolder = attachmentFolder
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

        editLogData = []
        editLogData.append("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
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

        for attachmentId in page.attachments:
            line = self._addAttachment(page, pageName, pageNamePath, attachmentId)
            if line is not None: editLogData.append(line)

        self._write(join(pageNamePath, "edit-log"), "".join(editLogData))

        revisionsPath = join(pageNamePath, "revisions")
        makedirs(revisionsPath)

        pageContent = self._addConvertPrefix(moinmoinMarkup.getvalue())
        self._write(join(revisionsPath, "00000001"), pageContent)


    def _addAttachment(self, page, pageName, pageNamePath, attachmentId):
        attachment = Attachment.all.get(attachmentId)
        if attachment is None: raise IncompleteData("No attachment found for id %s and page id %s" % (attachmentId, page.id))
        if attachment.originalVersion is not None:
            # we only want to have the most recent version
            return

        sourceFilePath = join(self.attachmentFolder, page.id, attachmentId, attachment.version)
        if not exists(sourceFilePath):
            raise IncompleteData(
                "Attachment with id %s for page id %s not found. I've expected it here '%s'" % (attachmentId, page.id, sourceFilePath))

        attachmentPath = join(pageNamePath, "attachments")
        if not exists(attachmentPath):
            makedirs(attachmentPath)

        filename = wikiutil.taintfilename(attachment.filename)
        filename = replace_non_ascii_chars(filename)
        targetFilePath = join(attachmentPath, filename)

        shutil.copy(sourceFilePath, targetFilePath)

        if attachment.lastModificationDate < page.lastModificationDate:
            attachmentTime = attachment.lastModificationDate
        else:
            attachmentTime = page.lastModificationDate

        # 1407004115054438        99999999        ATTNEW  attTest 192.168.56.1    192.168.56.1    1406319234.36.47302     1.txt
        return "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
            attachmentTime * 1000000,
            "99999999",
            "ATTNEW",
            pageName,
            "127.0.0.1",
            "127.0.0.1",
            attachment.creatorNameId,
            "",  # extra currently unused
            urllib.quote(print_safe(filename))
        )

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
    defaultUserId = None

    def __init__(self, folder):
        self.folder = folder
        self._readUserFromFolder()

        if MoinMoinUsers.all.has_key(config.DEFAULT_USER) is False:
            raise RuntimeError("no default user (%s) found." % config.DEFAULT_USER)
        MoinMoinUsers.defaultUserId = MoinMoinUsers.all.get(config.DEFAULT_USER)

    @classmethod
    def getUserIdForName(clz, name):
        """
        :param name:
        :return: the user for the given id or the default user else
        """
        userId = clz.all.get(name)
        if userId is None:
            return clz.defaultUserId
        return userId


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

    parser = argparse.ArgumentParser(description='Convert pages')
    parser.add_argument('--xmlInputFile', type=str, required=True, help='The crowd backup file (xml)')
    parser.add_argument('--attachmentPath', type=str, required=True, help='The path to the folder containing the confluence attachments.')
    parser.add_argument('--convertedUserPath', type=str, required=True, help='The path to the folder containing the converted users.')
    parser.add_argument('--outputPath', type=str, required=True, help='The output path. The pages will be created here.')
    args = parser.parse_args()

    MoinMoinUsers(args.convertedUserPath)

    print("loading & parse xml file...")
    tree = ET.parse(args.xmlInputFile)
    print("create MoinMoin pages & attachments...")

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

    Space.renameSpaces(config.SPACES)
    Page.renameHomePages()

    # debug

    # print("Spaces:")
    # for space in Space.all.values():
    #     print(space)

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
    # print(att)


    writer = MoinMoinWriter(attachmentFolder=args.attachmentPath, outputFolder=args.outputPath)
    writer.writePageForSpaces(config.SPACES.values())

    print("Finished.")