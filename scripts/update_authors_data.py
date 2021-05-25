# -*- coding: utf-8 -*-
import django
django.setup()

import re
import csv
import requests
from io import StringIO

from sefaria.system.database import db
from sefaria.model import *

"""
0 key
1 'Primary English Name'
2 'Secondary English Names'
3 'Primary Hebrew Name'
4 'Secondary Hebrew Names'
5 'Birth Year '
6 'Birth Place'
7 'Death Year'
8 'Death Place'
9 'Halachic Era'
10'English Biography'
11'Hebrew Biography'
12'English Wikipedia Link'
13'Hebrew Wikipedia Link'
14'Jewish Encyclopedia Link'
...
24 'Sex'"
"""

eras = {
    "Gaonim": "GN",
    "Rishonim": "RI",
    "Achronim": "AH",
    "Contemporary": "CO"
}

url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSx60DLNs8Dp0l2xpsPjrxD3dBpIKASXSBiE-zjq74SvUIc-hD-mHwCxsuJpQYNVHIh7FDBwx7Pp9zR/pub?gid=0&single=true&output=csv'
response = requests.get(url)
data = response.content.decode("utf-8")
cr = csv.reader(StringIO(data))
rows = list(cr)[4:]


print("*** Deleting old authorTopic records ***")
for foo, symbol in eras.items():
    people = AuthorTopicSet({"properties.era.value": symbol}).distinct("slug")
    db.topic_links.delete_many({"generatedBy": "update_authors_data", "toTopic": {"$in": people}})
    db.topic_links.delete_many({"generatedBy": "update_authors_data", "fromTopic": {"$in": people}})
    db.topics.delete_many({"properties.era.value": symbol})
    # Dependencies take too long here.  Getting rid of relationship dependencies above.  Assumption is that we'll import works right after to handle those dependencies.
    #PersonSet({"era": symbol}).delete()


def _(p: Topic, attr, value):
    if value:
        p.set_property(attr, value, "sefaria")

print("\n*** Adding authorTopic records ***\n")
for l in rows:
    slug = l[0].encode('ascii', errors='ignore').decode()
    if not slug:
        continue
    print(slug)
    p = AuthorTopic.init(slug) or AuthorTopic()
    p.slug = slug
    p.title_group.add_title(l[1].strip(), "en", primary=True, replace_primary=True)
    p.title_group.add_title(l[3].strip(), "he", primary=True, replace_primary=True)
    for x in l[2].split(","):
        x = x.strip()
        if len(x):
            p.title_group.add_title(x, "en")
    for x in l[4].split(","):
        x = x.strip()
        if len(x):
            p.title_group.add_title(x, "he")
    if len(l[5]) > 0:
        if "c" in l[5]:
            _(p, 'birthYearIsApprox', True)
        else:
            _(p, 'birthYearIsApprox', False)
        m = re.search(r"\d+", l[5])
        if m:
            _(p, 'birthYear', m.group(0))
    if len(l[7]) > 0:
        if "c" in l[7]:
            _(p, 'deathYearIsApprox', True)
        else:
            _(p, 'deathYearIsApprox', False)
        m = re.search(r"\d+", l[7])
        if m:
            _(p, 'deathYear', m.group(0))
    _(p, "birthPlace", l[6])
    _(p, "deathPlace", l[8])
    _(p, "era", eras.get(l[9]))
    _(p, "enBio", l[10])
    _(p, "heBio", l[11])
    _(p, "enWikiLink", l[12])
    _(p, "heWikiLink", l[13])
    _(p, "jeLink", l[14])
    _(p, "sex", l[24])
    p.save()

#Second Pass
rowmap = {
    16: 'child-of',
    17: 'grandchild-of',
    18: 'child-in-law-of',
    19: 'taught',
    20: 'member-of',
    21: 'corresponded-with',
    22: 'opposed',
    23: 'cousin-of',
}
flip_link_dir = {'taught'}
print("\n*** Adding relationships ***\n")
for l in rows:
    from_slug = l[0].encode('ascii', errors='ignore').decode()
    p = AuthorTopic.init(from_slug)
    for i, link_type_slug in rowmap.items():
        if l[i]:
            for pkey in l[i].split(","):
                to_slug = pkey.strip().encode('ascii', errors='ignore').decode()
                to_slug, from_slug = (from_slug, to_slug) if link_type_slug in flip_link_dir else (to_slug, from_slug)
                print("{} - {}".format(from_slug, pkey))
                if AuthorTopic.init(to_slug):
                    IntraTopicLink({
                        "toTopic": to_slug,
                        "fromTopic": from_slug,
                        "linkType": link_type_slug,
                        "dataSource": "sefaria",
                        "generatedBy" : "update_authors_data",
                    }).save()
