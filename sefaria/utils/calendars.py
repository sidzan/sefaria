# -*- coding: utf-8 -*-
"""
calendar.py - functions for looking up information relating texts to dates.

Uses MongoDB collections: dafyomi, parshiot
"""
import sefaria.model as model
from sefaria.system.database import db
import p929
from sefaria.utils.hebrew import encode_hebrew_numeral, hebrew_parasha_name
import datetime

"""
Calendar items:
calendar title
hebrew calendar title
display value
hebrew display value
ref
"""

def daily_929(datetime_obj):
    #datetime should just be a date, like datetime.today()
    p = p929.Perek(datetime_obj.date())
    rf = model.Ref("{} {}".format(p.book_name, p.book_chapter))
    display_en = "{} ({})".format(rf.normal(), p.number)
    display_he = u"{} ({})".format(rf.he_normal(), p.number)
    return [{
        'title' : {'en':'929', 'he': u'929'},
        'displayValue': {'en':display_en, 'he': display_he},
        'url': rf.url(),
        'order': 4,
        'category': rf.index.get_primary_category()
    }]


def daf_yomi(datetime_obj):
    """
    Returns the daf yomi for date
    """
    date_str = datetime_obj.strftime(" %m/ %d/%Y").replace(" 0", "").replace(" ", "")
    daf = db.dafyomi.find_one({"date": date_str})
    rf = model.Ref(daf["daf"] + "a")
    name =  daf["daf"]
    daf_num = int(daf["daf"].split(" ")[-1])
    daf_num_he = encode_hebrew_numeral(daf_num)
    name_he = u"{} {}".format(rf.he_book(), daf_num_he)

    return [{
        'title': {'en': 'Daf Yomi', 'he': u'דף יומי'},
        'displayValue': {'en': name, 'he': name_he},
        'url': rf.url(),
        'order': 3,
        'category': rf.index.get_primary_category()
    }]


def daily_mishnayot(datetime_obj):
    mishnah_items = []
    datetime_obj = datetime.datetime(datetime_obj.year,datetime_obj.month,datetime_obj.day)
    daily_mishnahs = db.daily_mishnayot.find({"date": {"$eq": datetime_obj}}).sort([("date", 1)])
    for dm in daily_mishnahs:
        rf = model.Ref(dm["ref"])
        mishnah_items.append({
        'title': {'en': 'Daily Mishnah', 'he': u'משנה יומית'},
        'displayValue': {'en': rf.normal(), 'he': rf.he_normal()},
        'url': rf.url(),
        'order': 5,
        'category': rf.index.get_primary_category()
    })
    return mishnah_items


def daily_rambam(datetime_obj):
    datetime_obj = datetime.datetime(datetime_obj.year,datetime_obj.month,datetime_obj.day)
    daily_rambam = db.daily_rambam.find_one({"date": {"$eq": datetime_obj}})
    if not daily_rambam:
        return None
    rf = model.Ref(daily_rambam["ref"])
    display_value_en = rf.normal().replace("Mishneh Torah, ","")
    display_value_he = rf.he_normal().replace(u"משנה תורה, ", u"")
    return [{
        'title': {'en': 'Daily Rambam', 'he': u'הרמב"ם היומי'},
        'displayValue': {'en': display_value_en, 'he': display_value_he},
        'url': rf.url(),
        'order': 6,
        'category': rf.index.get_primary_category()
    }]


def this_weeks_parasha(datetime_obj, diaspora=True):
    """
    Returns the upcoming Parasha for datetime.
    """
    p = db.parshiot.find({"date": {"$gt": datetime_obj}, "diaspora": {'$in': [diaspora, None]}}, limit=1).sort([("date", 1)])
    p = p.next()

    return p

def make_parashah_response_from_calendar_entry(db_parasha):
    rf = model.Ref(db_parasha["ref"])
    parasha = {
        'title': {'en': 'Parashat Hashavua', 'he': u'פרשת השבוע'},
        'displayValue': {'en': db_parasha["parasha"], 'he': hebrew_parasha_name(db_parasha["parasha"])},
        'url': rf.url(),
        'order': 1,
        'category': rf.index.get_primary_category()
    }
    return [parasha]

def make_haftarah_response_from_calendar_entry(db_parasha, custom=None):
    haftarah_objs = []
    if len(db_parasha["haftara"].keys()) == 1:
        haftarah_objs += make_haftarah_by_custom_response_from_calendar_entry(db_parasha, "ashkenazi", False)
    elif custom:
        haftarah_objs += make_haftarah_by_custom_response_from_calendar_entry(db_parasha, custom, True)
    else:
        for key in db_parasha["haftara"]:
            haftarah_objs += make_haftarah_by_custom_response_from_calendar_entry(db_parasha, key, True)
    return haftarah_objs

def make_haftarah_by_custom_response_from_calendar_entry(db_parasha, custom, add_custom_to_display):
    shorthands = {
        "ashkenazi" : {"en": 'A', "he": u'א'},
        "sephardi": {"en": 'S', "he": u'ס'},
        "edot hamizrach": {"en": 'EM', "he": u'עמ'}
    }
    haftarah_objs = []
    for h in db_parasha["haftara"][custom]:
        rf = model.Ref(h)
        haftara = {
            'title': {'en': 'Haftarah', 'he': u'הפטרה'},
            'displayValue': {'en': rf.normal(), 'he': rf.he_normal()},
            'url': rf.url(),
            'order': 2,
            'category': rf.index.get_primary_category(),
        }
        if add_custom_to_display:
            for lang in haftara['title']:
                haftara['title'][lang] = '{} ({})'.format(haftara['title'][lang], shorthands[custom][lang])
        haftarah_objs.append(haftara)
    return haftarah_objs

def parashat_hashavua_and_haftara(datetime_obj, diaspora=True, custom=None):
    parasha_items = []
    db_parasha = this_weeks_parasha(datetime_obj, diaspora=diaspora)

    parasha_items += make_parashah_response_from_calendar_entry(db_parasha)
    parasha_items += make_haftarah_response_from_calendar_entry(db_parasha, custom)
    return parasha_items


def get_all_calendar_items(datetime_obj, diaspora=True, custom="sephardi"):
    cal_items  = []
    cal_items += parashat_hashavua_and_haftara(datetime_obj, diaspora=diaspora)
    cal_items += daf_yomi(datetime_obj)
    cal_items += daily_929(datetime_obj)
    cal_items += daily_mishnayot(datetime_obj)
    cal_items += daily_rambam(datetime_obj)
    cal_items = [item for item in cal_items if item]
    return cal_items


def get_todays_calendar_items(diaspora=True):
    return get_all_calendar_items(datetime.datetime.now(), diaspora=diaspora, custom="sephardi")

def get_keyed_calendar_items(diaspora=True):
    cal_items = get_todays_calendar_items(diaspora=diaspora)
    cal_dict = {}
    for cal_item in cal_items:
        cal_dict[cal_item["title"]["en"]] = cal_item
    return cal_dict