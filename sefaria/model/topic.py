from . import abstract as abst
from .schema import AbstractTitledObject, TitleGroup


class Topic(abst.AbstractMongoRecord, AbstractTitledObject):
    collection = 'topics'
    slug_fields = ['slug']
    title_group = None
    required_attrs = [
        'slug',
        'titles',
    ]
    optional_attrs = [
        'alt_ids',
        'properties',
        'description',
        'isTopLevelDisplay',
        'displayOrder',
    ]

    def _set_derived_attributes(self):
        self.set_titles(getattr(self, "titles", None))

    def set_titles(self, titles):
        self.title_group = TitleGroup(titles)


class TopicSet(abst.AbstractMongoSet):
    recordClass = Topic


class TopicLinkHelper(object):
    """
    Used to collect attributes and functions that are useful for both IntraTopicLink and RefTopicLink
    Decided against superclass arch b/c instantiated objects will be of type super class.
    This is inconvenient when validating the attributes of object before saving (since subclasses have different required attributes)
    """
    collection = 'topic_links'
    required_attrs = [
        'toTopic',
        'linkType',
        'class',  # can be 'intraTopic' or 'refTopic'
    ]
    optional_attrs = [
        'dataSource',
        'generatedBy',
    ]

    @staticmethod
    def init_by_class(topic_link):
        """
        :param topic_link: dict from `topic_links` collection
        :return: either instance of IntraTopicLink or RefTopicLink based on 'class' field of `topic_link`
        """
        if topic_link['class'] == 'intraTopic':
            return IntraTopicLink().load_from_dict(topic_link, is_init=True)
        if topic_link['class'] == 'refTopic':
            return RefTopicLink().load_from_dict(topic_link, is_init=True)


class IntraTopicLink(abst.AbstractMongoRecord):
    """
    How to validate:
        <person link type>: make sure both sides are people (exceptions are has-role and member-of)
        has-role: target is role, source is independent continuant
        member-of: target is group, source is independent continuant
        has-cause: both sides are processes

    """
    collection = TopicLinkHelper.collection
    required_attrs = TopicLinkHelper.required_attrs + ['fromTopic']
    optional_attrs = TopicLinkHelper.optional_attrs


class RefTopicLink(abst.AbstractMongoRecord):
    collection = TopicLinkHelper.collection
    required_attrs = TopicLinkHelper.required_attrs + ['ref', 'expandedRefs', 'is_sheet']
    # magnitude is if a link can be given a number which signifies the link's strength (currently used for sheet-derived links)
    optional_attrs = TopicLinkHelper.optional_attrs + ['magnitude', 'order']


class TopicLinkSetHelper(object):

    @staticmethod
    def init_query(query, link_class):
        query = query or {}
        query['class'] = link_class
        return query

    @staticmethod
    def find(query=None, page=0, limit=0, sort=[("_id", 1)], proj=None):
        from sefaria.system.database import db
        raw_records = getattr(db, TopicLinkHelper.collection).find(query, proj).sort(sort).skip(page * limit).limit(limit)
        return [TopicLinkHelper.init_by_class(r) for r in raw_records]


class IntraTopicLinkSet(abst.AbstractMongoSet):
    recordClass = IntraTopicLink

    def __init__(self, query=None, *args, **kwargs):
        query = TopicLinkSetHelper.init_query(query, 'intraTopic')
        super().__init__(query=query, *args, **kwargs)


class RefTopicLinkSet(abst.AbstractMongoSet):
    recordClass = RefTopicLink

    def __init__(self, query=None, *args, **kwargs):
        query = TopicLinkSetHelper.init_query(query, 'refTopic')
        super().__init__(query=query, *args, **kwargs)


class TopicLinkType(abst.AbstractMongoRecord):
    collection = 'topic_link_types'
    slug_fields = ['slug', 'inverseSlug']
    required_attrs = [
        'slug',
        'inverseSlug',
        'displayName',
        'inverseDisplayName'
    ]
    optional_attrs = [
        'alt_ids',
        'inverse_alt_ids',
        'shouldDisplay',
        'devDescription'
    ]


class TopicLinkTypeSet(abst.AbstractMongoSet):
    recordClass = TopicLinkType


class TopicDataSource(abst.AbstractMongoRecord):
    collection = 'topic_data_sources'
    slug_fields = ['slug']
    required_attrs = [
        'slug',
        'displayName',
    ]
    optional_attrs = [
        'url',
        'description',
    ]