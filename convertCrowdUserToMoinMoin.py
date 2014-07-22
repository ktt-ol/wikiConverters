#!env python3

import xml.etree.ElementTree as ET
from _datetime import datetime
import argparse

__author__ = 'Holger Cremer'

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

    def __init__(self, id, name, email, displayName, createdDate):
        self.conversionDate = datetime.now()
        self.createTs = self.parseDate(createdDate)
        self.itemId = id

        self.tplVars = {
            "name": name,
            "email": email,
            "aliasname": displayName,
            "account_creation_date": self.createTs,
            "conversionDate": self.conversionDate,
            "conversionTs": self.conversionDate.timestamp()
        }

    def parseDate(self, date):
        """Parse time strings like this Sun Jan 15 16:20:13 +0000 2012 """
        return datetime.strptime(date, "%a %b %d %H:%M:%S %z %Y").timestamp()

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
        return str(self.conversionDate.timestamp()) + "." + str(self.itemId)

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
            name=user.find('name').text,
            email=user.find('email').text,
            displayName=user.find('displayName').text,
            createdDate=user.find('createdDate').text,
        )

        with open(outputDir + "/" + user.getFilename(), "w", encoding='utf-8') as file:
            file.write(user.getMoinMoinuserData())

        print("Converted: " + user.getName())


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
    elif args.group:
        listUsersForGroup(args.inputFile, args.group)

    print("\ndone")
