#!/usr/bin/env python

import xml.etree.ElementTree as ET
from datetime import datetime
import time
import calendar
import re
import argparse
import common

__author__ = 'Holger Cremer'

TZ_REMOVE_RE = r"[+-]([0-9])+"
def parseDateToUnixTimestamp(date):
    """
    Parse time strings like this
        Sun Jan 15 16:20:13 +0000 2012
    and return the unix timestamp, that means seconds (not milli or micro seconds)
    """

    # the %z (for timezone) is not supported in python 2.x
    date = re.sub(TZ_REMOVE_RE, "", date)
    parsed = datetime.strptime(date, "%a %b %d %H:%M:%S %Y")
    return calendar.timegm(parsed.utctimetuple())

def timestamp_from_datetime(datetime_obj):
    return str(calendar.timegm(datetime_obj.utctimetuple())) + "." + str(datetime_obj.time().microsecond)


class User():
    USER_TEMPLATE = """# converted user, date: $conversionDate$
account_creation_date=$account_creation_date$
account_creation_host=127.0.0.1
aliasname=$aliasname$
email=$email$
enc_password={SSHA}brokenforconversion/broken==
last_saved=$conversionTs$
name=$name$
"""

    def __init__(self, id, name, email, displayName, createdDate=None):
        self.conversionDate = datetime.now()
        if createdDate is None:
            createTs = time.time()
        else:
            createTs = float(parseDateToUnixTimestamp(createdDate))

        self.itemId = id

        self.tplVars = {
            "name": name,
            "email": email,
            "aliasname": displayName,
            "account_creation_date": createTs,
            "conversionDate": self.conversionDate,
            "conversionTs": timestamp_from_datetime(self.conversionDate)
        }

    def getMoinMoinuserData(self):
        userData = self.USER_TEMPLATE
        for key, value in self.tplVars.items():
            userData = userData.replace("$" + key + "$", str(value))

        return userData

    def getFilename(self):
        """
        timestamp of conversion DOT internal user id in crowd.
         Example: 1406058695.752081.1223
        """
        return timestamp_from_datetime(self.conversionDate) + "." + str(self.itemId)

    def getName(self):
        return self.tplVars.get("name")


def convertUsers(input, outputDir):
    print("Converting users...")

    tree = ET.parse(input)
    root = tree.getroot()

    for user in root.iter('user'):
        isActive = user.find("active").text == "true"
        if not isActive:
            continue

        user = User(
            id=user.find('id').text,
            name=user.find('name').text.encode('utf-8'),
            email=user.find('email').text,
            displayName=user.find('displayName').text.encode('utf-8'),
            createdDate=user.find('createdDate').text,
        )
        # encoding='utf-8'
        with open(outputDir + "/" + user.getFilename(), "w") as file:
            file.write(user.getMoinMoinuserData())

        print("Converted: " + user.getName())

def add_default_user(outputDir):
    now = datetime.now()
    default_user = User(
        id="9999999",
        name=common.DEFAULT_USER,
        email=common.DEFAULT_USER,
        displayName="User " + common.DEFAULT_USER
    )

    #encoding='utf-8'
    with open(outputDir + "/" + default_user.getFilename(), "w") as file:
        file.write(default_user.getMoinMoinuserData())

    print("Default user created.")

def listUsersForGroup(input, groupName):
    print("Listing users for group " + groupName)

    tree = ET.parse(input)
    root = tree.getroot()

    for membership in root.findall("./memberships/membership"):
        if membership.find("parentName").text == groupName:
            print(membership.find("childName").text)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Parse user or groups')
    parser.add_argument('inputFile', type=str, help='The crowd backup file (xml)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-convertUserTo', dest="users", type=str, metavar="directory", help='Convert the user and store them into this directory')
    group.add_argument('-group', dest="group", type=str, metavar="groupname", help='The group to get the user names for')
    args = parser.parse_args()

    if args.users:
        convertUsers(args.inputFile, args.users)
        add_default_user(args.users)
    elif args.group:
        listUsersForGroup(args.inputFile, args.group)

    print("\ndone")
