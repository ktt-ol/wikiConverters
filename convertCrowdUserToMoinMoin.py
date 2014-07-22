import xml.etree.ElementTree as ET
from _datetime import datetime

__author__ = 'Holger Cremer'

# config
INPUT_XML = "testdata/atlassian-crowd-2.6.4-backup-2014-07-22-175735.xml"
OUTPUT_FOLDER = "output"
# config end


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

if __name__ == '__main__':

    tree = ET.parse(INPUT_XML)
    root = tree.getroot()
    for user in root.iter('user'):
        user = User(
            id=user.find('id').text,
            name=user.find('name').text,
            email=user.find('email').text,
            displayName=user.find('displayName').text,
            createdDate=user.find('createdDate').text,
        )

        with open(OUTPUT_FOLDER + "/" +  user.getFilename(), "w", encoding='utf-8') as file:
            file.write(user.getMoinMoinuserData())

        print("Crated: " + user.getName())

    print("done")
