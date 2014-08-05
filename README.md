# wikiConverters

Converting user and content from crowd and confluence to a moinmoin wiki.  

# Convert

You need the xml backup from crowd. You can get this through the admin interface ("backup").  

## Setup

Unzip the backup file. Open the ```config.py``` and update the settings as you like.  

## Converting users

Parses the backup file and creates moinmoin wiki compatible user files in the specified output directory. Example:

    ./convertCrowdUserToMoinMoin.py -convertUserTo output/users export/xmlexport-20140725-202414-6780/entities.xml

## List user for a group

Parses the backup file and lists every user that is member of the specified group. Example:

    ./convertCrowdUserToMoinMoin.py -group Member export/xmlexport-20140725-202414-6780/entities.xml    

## Converting pages & attachments

Parses the backup file and convert all pages and attachments to MoinMoin files. Example:

    ./convertData.py --xmlInputFile "export/xmlexport-20140725-202414-6780/entities.xml" --attachmentPath "export/xmlexport-20140725-202414-6780/attachments" --convertedUserPath  "output/users" --outputPath "output/pages"

# MoinMoin setup

The following settings are found to be useful, at least for us. Apply it before or after the conversion.

* Install the following two macros (download it into ```/var/lib/wiki/data/plugin/macro/```): 
** http://moinmo.in/MacroMarket/ChildPages 
** http://moinmo.in/MacroMarket/SiteIndex
* Install this theme http://moinmo.in/ThemeMarket/memodump to get a nice theme AND a working sidebar. 
** Edit the sidebar and insert the macro.

      ==== Spaces ====
      <<SiteIndex(count=False,subpages=False)>>
      
      ==== Unterseiten ====
      <<ChildPages(on=not:edit|AttachFile|LocalSiteMap, more_link=More..., max_pages=10, none_note=keine)>>
      

# Issues

* Internal links are broken
* No history will be converted. Only the most recent page and most recent attachment version is used. 
* No acls!


# Copyright and Licence Information

* To convert the Confluence marktup into MoinMoin syntax, we used the parser from http://hgweb.boddie.org.uk/ConfluenceConverter. The corresponding sources lay in the [ConfluenceConverter/] folder.
* The [wikiutil.py] is a stripped version of the MoinMoin wikiutil.py file.  