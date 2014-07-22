# wikiConverters

Converting user and content from crowd and confluence to a moinmoin wiki

You need the xml backup from crowd. You can get this through the admin interface ("backup"). 

## Converting users

Parses the backup file and creates moinmoin wiki compatible user files in the specified output directory. Example:

    ./convertCrowdUserToMoinMoin.py -convertUserTo output testdata/atlassian-crowd-2.6.4-backup-2014-07-22-175735.xml

## List user for a group

Parses the backup file and lists every user that is member of the specified group. Example:

    ./convertCrowdUserToMoinMoin.py -group Member testdata/atlassian-crowd-2.6.4-backup-2014-07-22-175735.xml    

