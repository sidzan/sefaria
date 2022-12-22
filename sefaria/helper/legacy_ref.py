# encoding=utf-8

from sefaria.model.abstract import AbstractMongoRecord
from sefaria.model.text import Ref
from django.utils.module_loading import import_string


class LegacyRefParsingData(AbstractMongoRecord):
    """
    This class is a mongo backed data store for data to aid legacy ref parsing. 
    It can contain ref mapping or any other data we think of down the line to help in future cases.
    Imagine a structure for e.g. 
    ```
    {
        "index_title" : "Zohar",
        "data": {
            "mapping": { "old_ref 1" : "mapped_ref 1" ...}
        }
    }
    ```
    To be used with LegacyRefParser classes in this module.
    """
    collection = 'legacy_ref_data'
    criteria_field = 'title'
    pkeys = ["index_title"]
    required_attrs = [
        "index_title",
        "data",
    ]


class MappingLegacyRefParser:
    """
    Parses legacy refs using a mapping from old ref -> new ref
    """
    
    def __init__(self, index_title: str):
        self._load_mapping(index_title)
    
    def _load_mapping(self, index_title):
        """
        Load mapping from the DB
        @return:
        """
        lrpd = LegacyRefParsingData().load({"index_title": index_title})
        if lrpd is None:
            raise NoLegacyRefParserError(f"No MappingLegacyRefParser for index title '{index_title}'")
        self._mapping = lrpd.data['mapping']
    
    def is_ranged_ref(self):
        pass
    
    def parse(self, ref):
        converted_ref = self._mapping[ref]
        converted_ref = Ref(converted_ref)
        converted_ref.legacy_tref = ref
        return converted_ref


class NoLegacyRefParserError(Exception):
    pass


class NonExistantLegacyRefParser:
    pass


NON_EXISTANT_LEGACY_REF_PARSER = NonExistantLegacyRefParser()
    

class LegacyRefParserHandler(object):
    """
    pattern copied from django.core.cache.CacheHandler
    This just makes sure to load the correct legacy ref parser class given an index title
    """
    def __init__(self):
        self._parsers = {}

    def __getitem__(self, index_title: str):
        parser = self._get_parser(index_title)
        if isinstance(parser, NonExistantLegacyRefParser):
            raise NoLegacyRefParserError(f"Could not find proper legacy parser matching index title '{index_title}'")
        return parser

    def _get_parser(self, index_title: str):
        try:
            return self._parsers[index_title]
        except KeyError:
            pass
        try:
            parser = self._create_legacy_parser(index_title)
        except NoLegacyRefParserError as e:
            parser = NON_EXISTANT_LEGACY_REF_PARSER
        self._parsers[index_title] = parser
        return parser

    def parse(self, index_title: str, tref: str):
        parser = self[index_title]
        return parser.parse(tref)

    @staticmethod
    def _create_legacy_parser(index_title, **kwargs):
        """
        Currently, only returns one type of LegacyRefParser but in the future can load the ref parsing data and
        determine the type from the data
        """

        return MappingLegacyRefParser(index_title)


legacy_ref_parser_handler = LegacyRefParserHandler()
