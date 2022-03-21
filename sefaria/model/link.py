"""
link.py
Writes to MongoDB Collection: links
"""

import regex as re
from bson.objectid import ObjectId
from sefaria.model.text import AbstractTextRecord, VersionSet
from sefaria.system.exceptions import DuplicateRecordError, InputError, BookNameError
from sefaria.system.database import db
from . import abstract as abst
from . import text

import structlog
logger = structlog.get_logger(__name__)


class Link(abst.AbstractMongoRecord):
    """
    A link between two texts (or more specifically, two references)
    """
    collection = 'links'
    history_noun = 'link'

    required_attrs = [
        "type",             # string of connection type
        "refs",             # list of refs connected
    ]

    optional_attrs = [
        "expandedRefs0",    # list of refs corresponding to `refs.0`, but breaking ranging refs down into individual segments
        "expandedRefs1",    # list of refs corresponding to `refs.1`, but breaking ranging refs down into individual segments
        "anchorText",       # string of dibbur hamatchil (largely depcrated) 
        "availableLangs",   # list of lists corresponding to `refs` showing languages available, e.g. [["he"], ["he", "en"]]  
        "highlightedWords", # list of strings to be highlighted when presenting a text as a connection
        "auto",             # bool whether generated by automatic process
        "generated_by",     # string in ("add_commentary_links", "add_links_from_text", "mishnah_map")
        "source_text_oid",  # oid of text from which link was generated
        "is_first_comment", # set this flag to denote its the first comment link between the two texts in the link
        "first_comment_indexes", # Used when is_first_comment is True. List of the two indexes of the refs.
        "first_comment_section_ref", # Used when is_first_comment is True. First comment section ref.
        "inline_reference",  # dict with keys "data-commentator" and "data-order" to match an inline reference (itag)
        "charLevelData",     # list of length 2. Containing 2 dicts coresponding to the refs list, each dict consists of the following keys: ["startChar","endChar","versionTitle","language"]. *if one of the refs is a Pasuk the startChar and endChar keys are startWord and endWord. This attribute was created for the quotation finder
        "score",             # int. represents how "good"/accurate the link is. introduced for quotations finder
        "inline_citation",    # bool acts as a flag for wrapped refs logic to run on the segments where this citation is inline.
        "versions",          # only for cases when type is `essay`: list of versionTitles corresponding to `refs`, where first versionTitle corresponds to Index of first ref, and each value is a dictionary of language and title of version
        "displayedText"       # only for cases when type is `essay`: dictionary of en and he strings to be displayed
    ]

    def _normalize(self):
        self.auto = getattr(self, 'auto', False)
        self.generated_by = getattr(self, "generated_by", None)
        self.source_text_oid = getattr(self, "source_text_oid", None)
        self.type = getattr(self, "type", "").lower()
        self.refs = [text.Ref(self.refs[0]).normal(), text.Ref(self.refs[1]).normal()]

        if getattr(self, "_id", None):
            self._id = ObjectId(self._id)

    def _validate(self):
        assert super(Link, self)._validate()

        if self.type == "essay":   # when type is 'essay', versionTitles should correspond to indices referred to in self.refs
            assert hasattr(self, "versions") and hasattr(self, "displayedText"), "You must set versions and displayedText fields for type 'essay'."
            assert "en" in self.displayedText[0] and "he" in self.displayedText[0] and "en" in self.displayedText[1] and "he" in self.displayedText[1], \
                "displayedText field must be a list of dictionaries with 'he' and 'en' fields."
            for ref, version in zip(self.refs, self.versions):
                versionTitle = version["title"]
                versionLanguage = version["language"] if "language" in version else None
                index_title = text.Ref(ref).index.title
                if versionTitle not in ["ALL", "NONE"]:
                    assert VersionSet({"title": index_title, "versionTitle": versionTitle, "language": versionLanguage}).count() > 0, \
                        f"No version found for book '{index_title}', with versionTitle '{versionTitle}', and language '{versionLanguage}'"


        if False in self.refs:
            return False

        if hasattr(self, "charLevelData"):
            try:
                assert type(self.charLevelData) is list
                assert len(self.charLevelData) == 2
                assert type(self.charLevelData[0]) is dict
                assert type(self.charLevelData[1]) is dict
            except AssertionError:
                raise InputError(f'Structure of the charLevelData in Link is wrong. link refs: {self.refs[0]} - {self.refs[1]}. charLevelData should be a list of length 2 containing 2 dicts coresponding to the refs list, each dict consists of the following keys: ["startChar","endChar","versionTitle","language"]')
            assert self.charLevelData[0]['versionTitle'] in [v['versionTitle'] for v in text.Ref(self.refs[0]).version_list()], 'Dictionaries in charLevelData should be in correspondence to the "refs" list'
        return True

    def _pre_save(self):
        if getattr(self, "_id", None) is None:
            # Don't bother saving a connection that already exists, or that has a more precise link already
            if self.refs != sorted(self.refs):
                if hasattr(self, 'charLevelData'):
                    self.charLevelData.reverse()
                if getattr(self, "versions", False) and getattr(self, "displayedText", False):
                    # if reversed self.refs, make sure to reverse self.versions and self.displayedText
                    self.versions = self.versions[::-1]
                    self.displayedText = self.displayedText[::-1]
            self.refs = sorted(self.refs)  # make sure ref order is deterministic
            samelink = Link().load({"refs": self.refs})

            if not samelink:
                #check for samelink section level vs ranged ref
                oref0 = text.Ref(self.refs[0])
                oref1 = text.Ref(self.refs[1])
                section0 = oref0.section_ref()
                section1 = oref1.section_ref()
                if oref0.is_range() and oref0.all_segment_refs() == section0.all_segment_refs():
                    samelink = Link.load({"$and": [{"refs": section0}, {"refs": self.refs[1]}]})
                elif oref0.is_section_level():
                    ranged0 = text.Ref(f"{oref0.all_segment_refs()[0]}-{oref0.all_segment_refs()[-1]}")
                    samelink = Link.load({"$and": [{"refs": ranged0}, {"refs": self.refs[1]}]})
                elif oref1.is_range() and oref1.all_segment_refs() == section1.all_segment_refs(): # this is an elif since it anyway overrides the samelink see note in 4 lines
                    samelink = Link.load({"$and": [{"refs": section1}, {"refs": self.refs[0]}]})
                elif oref1.is_section_level():
                    ranged1 = text.Ref(f"{oref1.all_segment_refs()[0]}-{oref1.all_segment_refs()[-1]}")
                    samelink = Link.load({"$and": [{"refs": ranged1}, {"refs": self.refs[0]}]})
                #note: The above code neglects the case where both refs in the link are section or ranged and there is a ranged/section link in the db with the opposite situation on both refs.

            if samelink:
                if hasattr(self, 'score') and hasattr(self, 'charLevelData'):
                    samelink.score = self.score
                    samelink.charLevelData = self.charLevelData
                    samelink.save()
                    raise DuplicateRecordError("Updated existing link with the new score and charLevelData data")

                elif not self.auto and self.type and not samelink.type:
                    samelink.type = self.type
                    samelink.save()
                    raise DuplicateRecordError("Updated existing link with new type: {}".format(self.type))

                elif self.auto and not samelink.auto:
                    samelink.auto = self.auto
                    samelink.generated_by = self.generated_by
                    samelink.source_text_oid = self.source_text_oid
                    samelink.type = self.type
                    samelink.refs = self.refs  #in case the refs are reversed. switch them around
                    samelink.save()
                    raise DuplicateRecordError("Updated existing link with auto generation data {} - {}".format(self.refs[0], self.refs[1]))
                else:
                    raise DuplicateRecordError("Link already exists {} - {}. Try editing instead.".format(self.refs[0], self.refs[1]))

            else:
                #find a potential link that already has a more precise ref of either of this link's refs.
                preciselink = Link().load(
                    {'$and':[text.Ref(self.refs[0]).ref_regex_query(), text.Ref(self.refs[1]).ref_regex_query()]}
                )

                if preciselink:
                    # logger.debug("save_link: More specific link exists: " + link["refs"][1] + " and " + preciselink["refs"][1])
                    if getattr(self, "_override_preciselink", False):
                        preciselink.delete()
                        self.generated_by = self.generated_by+'_preciselink_override'
                        #and the new link will be posted (supposedly)
                    else:
                        raise DuplicateRecordError("A more precise link already exists: {} - {}".format(preciselink.refs[0], preciselink.refs[1]))
                # else: # this is a good new link

        if not getattr(self, "_skip_lang_check", False):
            self._set_available_langs()

        if not getattr(self, "_skip_expanded_refs_set", False):
            self._set_expanded_refs()

    def _sanitize(self):
        """
        bleach all input to protect against security risks
        """
        all_attrs = self.required_attrs + self.optional_attrs
        for attr in all_attrs:
            val = getattr(self, attr, None)
            if isinstance(val, str):
                setattr(self, attr, AbstractTextRecord.remove_html(val))

    def _set_available_langs(self):
        LANGS_CHECKED = ["he", "en"]
        
        def lang_list(ref):
            return [lang for lang in LANGS_CHECKED if text.Ref(ref).is_text_fully_available(lang)]
        self.availableLangs = [lang_list(ref) for ref in self.refs]

    def _set_expanded_refs(self):
        self.expandedRefs0 = [oref.normal() for oref in text.Ref(self.refs[0]).all_segment_refs()]
        self.expandedRefs1 = [oref.normal() for oref in text.Ref(self.refs[1]).all_segment_refs()]

    def ref_opposite(self, from_ref, as_tuple=False):
        """
        Return the Ref in this link that is opposite the one matched by `from_ref`.
        The matching of from_ref uses Ref.regex().  Matches are to the specific ref, or below.
        If neither Ref matches from_ref, None is returned.
        :param from_ref: A Ref object
        :param as_tuple: If true, return a tuple (Ref,Ref), where the first Ref is the given from_ref,
        or one more specific, and the second Ref is the opposing Ref in the link.
        :return:
        """
        reg = re.compile(from_ref.regex())
        if reg.match(self.refs[1]):
            from_tref = self.refs[1]
            opposite_tref = self.refs[0]
        elif reg.match(self.refs[0]):
            from_tref = self.refs[0]
            opposite_tref = self.refs[1]
        else:
            return None

        if opposite_tref:
            try:
                if as_tuple:
                    return text.Ref(from_tref), text.Ref(opposite_tref)
                return text.Ref(opposite_tref)
            except InputError:
                return None


class LinkSet(abst.AbstractMongoSet):
    recordClass = Link

    def __init__(self, query_or_ref={}, page=0, limit=0):
        '''
        LinkSet can be initialized with a query dictionary, as any other MongoSet.
        It can also be initialized with a :py:class: `sefaria.text.Ref` object,
        and will use the :py:meth: `sefaria.text.Ref.regex()` method to return the set of Links that refer to that Ref or below.
        :param query_or_ref: A query dict, or a :py:class: `sefaria.text.Ref` object
        '''
        try:
            regex_list = query_or_ref.regex(as_list=True)
            ref_clauses = [{"expandedRefs0": {"$regex": r}} for r in regex_list]
            ref_clauses += [{"expandedRefs1": {"$regex": r}} for r in regex_list]
            super(LinkSet, self).__init__({"$or": ref_clauses}, page, limit)
        except AttributeError:
            super(LinkSet, self).__init__(query_or_ref, page, limit)

    def filter(self, sources):
        """
        Filter LinkSet according to 'sources' which may be either
        - a string, naming a text or category to include
        - an array of strings, naming multiple texts or categories to include

        ! Returns a list of Links, not a LinkSet
        """
        if isinstance(sources, str):
            return self.filter([sources])

        # Expand Categories
        categories = text.library.get_text_categories()
        expanded_sources = []
        for source in sources:
            expanded_sources += [source] if source not in categories else text.library.get_indexes_in_category(source)

        regexes = [text.Ref(source).regex() for source in expanded_sources]
        filtered = []
        for source in self:
            if any([re.match(regex, source.refs[0]) for regex in regexes] + [re.match(regex, source.refs[1]) for regex in regexes]):
                filtered.append(source)

        return filtered

    # This could be implemented with Link.ref_opposite, but we should speed test it first.
    def refs_from(self, from_ref, as_tuple=False, as_link=False):
        """
        Get a collection of Refs that are opposite the given Ref, or a more specific Ref, in this link set.
        Note that if from_ref is more specific than the criterion that created the linkSet,
        then the results of this function will implicitly be filtered according to from_ref.
        :param from_ref: A Ref object
        :param as_tuple: If true, return a collection of tuples (Ref,Ref), where the first Ref is the given from_ref,
        or one more specific, and the second Ref is the opposing Ref in the link.
        :return: List of Ref objects
        """
        reg = re.compile(from_ref.regex())
        refs = []
        for link in self:
            if reg.match(link.refs[1]):
                from_tref = link.refs[1]
                opposite_tref = link.refs[0]
            elif reg.match(link.refs[0]):
                from_tref = link.refs[0]
                opposite_tref = link.refs[1]
            else:
                opposite_tref = False

            if opposite_tref:
                try:
                    if as_link:
                        refs.append((link, text.Ref(opposite_tref)))
                    elif as_tuple:
                        refs.append((text.Ref(from_tref), text.Ref(opposite_tref)))
                    else:
                        refs.append(text.Ref(opposite_tref))
                except:
                    pass
        return refs

    @classmethod
    def get_first_ref_in_linkset(cls, base_text, dependant_text):
        """
        Given a linkset
        :param from_ref: A Ref object
        :param as_tuple: If true, return a collection of tuples (Ref,Ref), where the first Ref is the given from_ref,
        or one more specific, and the second Ref is the opposing Ref in the link.
        :return: List of Ref objects
        """
        retlink = None
        orig_ref = text.Ref(dependant_text)
        base_text_ref = text.Ref(base_text)
        ls = cls(
            {'$and': [orig_ref.ref_regex_query(), base_text_ref.ref_regex_query()],
             "generated_by": {"$ne": "add_links_from_text"}}
        )
        refs_from = ls.refs_from(base_text_ref, as_link=True)
        sorted_refs_from = sorted(refs_from, key=lambda r: r[1].order_id())
        if len(sorted_refs_from):
            retlink = sorted_refs_from[0][0]
        return retlink

    def summary(self, relative_ref):
        """
        Returns a summary of the counts and categories in this link set,
        relative to 'relative_ref'.
        """
        results = {}
        for link in self:
            ref = link.refs[0] if link.refs[1] == relative_ref.normal() else link.refs[1]
            try:
                oref = text.Ref(ref)
            except:
                continue
            cat  = oref.primary_category
            if (cat not in results):
                results[cat] = {"count": 0, "books": {}}
            results[cat]["count"] += 1
            if (oref.book not in results[cat]["books"]):
                results[cat]["books"][oref.book] = 0
            results[cat]["books"][oref.book] += 1

        return [{"name": key, "count": results[key]["count"], "books": results[key]["books"] } for key in list(results.keys())]


def process_index_title_change_in_links(indx, **kwargs):
    print("Cascading Links {} to {}".format(kwargs['old'], kwargs['new']))

    # ensure that the regex library we're using here is the same regex library being used in `Ref.regex`
    from .text import re as reg_reg
    patterns = [pattern.replace(reg_reg.escape(indx.title), reg_reg.escape(kwargs["old"]))
                for pattern in text.Ref(indx.title).regex(as_list=True)]
    queries = [{'refs': {'$regex': pattern}} for pattern in patterns]
    links = LinkSet({"$or": queries})
    for l in links:
        l.refs = [r.replace(kwargs["old"], kwargs["new"], 1) if re.search('|'.join(patterns), r) else r for r in l.refs]
        l.expandedRefs0 = [r.replace(kwargs["old"], kwargs["new"], 1) if re.search('|'.join(patterns), r) else r for r in l.expandedRefs0]
        l.expandedRefs1 = [r.replace(kwargs["old"], kwargs["new"], 1) if re.search('|'.join(patterns), r) else r for r in l.expandedRefs1]
        try:
            l._skip_lang_check = True
            l._skip_expanded_refs_set = True
            l.save()
        except InputError: #todo: this belongs in a better place - perhaps in abstract
            logger.warning("Deleting link that failed to save: {} - {}".format(l.refs[0], l.refs[1]))
            l.delete()


def process_index_delete_in_links(indx, **kwargs):
    from sefaria.model.text import prepare_index_regex_for_dependency_process
    pattern = prepare_index_regex_for_dependency_process(indx)
    LinkSet({"refs": {"$regex": pattern}}).delete()


def update_link_language_availabiliy(oref, lang=None, available=None):
    """
    Updates langauge availibility tags in links connected to `oref`.
    If `lang` and `available` a present set the values provided.
    If not, re-save the links, triggering a lookup of content availability. 
    """
    links = oref.linkset()
    
    if lang and available is not None:
        for link in links:
            if not getattr(link, "availableLangs", None):
                link.save()
                continue
            pos = 0 if oref.overlaps(text.Ref(link.refs[0])) else 1

            if available:
                link.availableLangs[pos].append(lang)
                link.availableLangs[pos] = list(set(link.availableLangs[pos]))
            else:
                link.availableLangs[pos] = [alang for alang in link.availableLangs[pos] if alang != lang]
            link._skip_lang_check = True
            link.save()
    else:
        links.save()


#get_link_counts() and get_book_link_collection() are used in Link Explorer.
#They have some client formatting code in them; it may make sense to move them up to sefaria.client or sefaria.helper
def get_link_counts(cat1, cat2):
    """
    Returns a list of book to book link counts for books within `cat1` and `cat2`
    Parameters may name either a category or a individual book
    """
    titles = []
    for c in [cat1, cat2]:
        ts = text.library.get_indexes_in_category(c)
        if len(ts) == 0:
            try:
                text.library.get_index(c)
                ts.append(c)
            except BookNameError:
                return {"error": "No results for {}".format(c)}
        titles.append(ts)

    result = []
    for title1 in titles[0]:
        for title2 in titles[1]:
            re1 = r"^{} \d".format(title1)
            re2 = r"^{} \d".format(title2)
            links = LinkSet({"$and": [{"refs": {"$regex": re1}}, {"refs": {"$regex": re2}}]})
            count = links.count()
            if count:
                result.append({"book1": title1, "book2": title2, "count": count})

    return result


# todo: check vis-a-vis commentary refactor
def get_category_commentator_linkset(cat, commentator):
    return LinkSet({"$or": [
                        {"$and": [{"refs": {"$regex": r"{} \d".format(t)}},
                                  {"refs": {"$regex": "^{} on {}".format(commentator, t)}}
                                  ]
                         }
                        for t in text.library.get_indexes_in_category(cat)]
                    })


def get_category_category_linkset(cat1, cat2):
    """
    Return LinkSet of links between the given book and category.
    :param book: String
    :param cat: String
    :return:
    """
    queries = []
    titles = []
    regexes = []
    clauses = []

    for i, cat in enumerate([cat1, cat2]):
        queries += [{"$and": [{"categories": cat}, {'dependence': {'$in': [False, None]}}]}]
        titles += [text.library.get_indexes_in_category(cat)]
        if len(titles[i]) == 0:
            raise IndexError("No results for {}".format(queries[i]))

        regexes += [[]]
        for t in titles[i]:
            regexes[i] += text.Ref(t).regex(as_list=True)

        clauses += [[]]
        for rgx in regexes[i]:
            if cat1 == cat2:
                clauses[i] += [{"refs.{}".format(i): {"$regex": rgx}}]
            else:
                clauses[i] += [{"refs": {"$regex": rgx}}]

    return LinkSet({"$and": [{"$or": clauses[0]}, {"$or": clauses[1]}]})


def get_book_category_linkset(book, cat):
    """
    Return LinkSet of links between the given book and category, or between two books.
    :param book: String
    :param cat: String
    :return:
    """
    titles = text.library.get_indexes_in_category(cat)
    if len(titles) == 0:
        try:
            text.library.get_index(cat)
            titles = [cat]
        except BookNameError:
            return {"error": "No results for {}".format(cat)}

    book_re = text.Ref(book).regex()
    cat_re = r'^({}) \d'.format('|'.join(titles)) #todo: generalize this regex

    cat_re = r'^({})'.format('|'.join([text.Ref(title).regex() for title in titles]))

    return LinkSet({"$and": [{"refs": {"$regex": book_re}}, {"refs": {"$regex": cat_re}}]})


def get_book_link_collection(book, cat):
    """
    Format results of get_book_category_linkset for front end use by the Explorer.
    :param book: String
    :param cat: String
    :return:
    """
    links = get_book_category_linkset(book, cat)

    link_re = r'^(?P<title>.+) (?P<loc>\d.*)$'
    ret = []

    for link in links:
        l1 = re.match(link_re, link.refs[0])
        l2 = re.match(link_re, link.refs[1])
        if not l1 or not l2:
            continue
        ret.append({
            "r1": {"title": l1.group("title"), "loc": l1.group("loc")},
            "r2": {"title": l2.group("title"), "loc": l2.group("loc")}
        })
    return ret
