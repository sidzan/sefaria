from collections import defaultdict
from typing import List
from enum import Enum
from . import abstract as abst
from . import text
from . import schema
from spacy.tokens import Span
from spacy.language import Language

class RefPartType(Enum):
    NAMED = "named"
    NUMBERED = "numbered"
    DH = "dibur_hamatchil"

    label_to_enum_attr = {
        "כותרת": 'NAMED',
        "מספר": "NUMBERED",
        "דה": "DH",
    }

    @classmethod
    def span_label_to_enum(cls, span_label: str) -> 'RefPartType':
        return getattr(cls, cls.label_to_enum_attr[span_label])

# TODO consider that we may not need raw ref part source
class RefPartSource(Enum):
    INPUT = "input"

class NonUniqueTerm(abst.AbstractMongoRecord, schema.AbstractTitledObject):
    collection = "non_unique_terms"
    required_attrs = [
        "slug",
        "titles"
    ]
    slug_fields = ['slug']

    title_group = None
    
    def _normalize(self):
        super()._normalize()
        self.titles = self.title_group.titles

    def set_titles(self, titles):
        self.title_group = schema.TitleGroup(titles)

    def _set_derived_attributes(self):
        self.set_titles(getattr(self, "titles", None))

class NonUniqueTermSet(abst.AbstractMongoSet):
    recordClass = NonUniqueTerm

class RawRefPart:
    
    def __init__(self, source: str, type: 'RefPartType', span: Span, potential_dh_continuation: str=None) -> None:
        self.source = source
        self.span = span
        self.type = type
        self.potential_dh_continuation = potential_dh_continuation

    def __str__(self):
        return f"{self.__class__.__name__}: {self.span}, Source = {self.source}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.source}, {self.span}, {self.potential_dh_continuation})"

    def __eq__(self, other):
        return isinstance(other, RawRefPart) and self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash(f"{self.source}|{self.span.__hash__()}|{self.potential_dh_continuation}")

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_text(self):
        return self.span.text

    text = property(get_text)

class RawRef:
    
    def __init__(self, raw_ref_parts: list, span: Span) -> None:
        self.raw_ref_parts = raw_ref_parts
        self.span = span

    def get_text(self):
        return self.span.text

    text = property(get_text)

class ResolvedRawRef:

    def __init__(self, raw_ref: 'RawRef', resolved_ref_parts: List['RawRefPart'], node, ref: text.Ref) -> None:
        self.raw_ref = raw_ref
        self.resolved_ref_parts = resolved_ref_parts
        self.node = node
        self.ref = ref
        self.ambiguous = False

    def get_unused_ref_parts(self, raw_ref: 'RawRef'):
        return [ref_part for ref_part in raw_ref.raw_ref_parts if ref_part not in self.resolved_ref_parts]

    def _get_refined_match_for_dh_part(self, raw_ref_part: 'RawRefPart', refined_ref_parts: List['RawRefPart'], node: schema.DiburHamatchilNodeSet):
        max_node, max_score = node.best_fuzzy_match_score(raw_ref_part)
        if max_score == 1.0:
            return ResolvedRawRef(self.raw_ref, refined_ref_parts, max_node, text.Ref(max_node.ref))

    def get_refined_matches(self, raw_ref_part: 'RawRefPart', node, lang: str) -> List['ResolvedRawRef']:
        refined_ref_parts = self.resolved_ref_parts + [raw_ref_part]
        matches = []
        if raw_ref_part.type == RefPartType.NUMBERED and isinstance(node, schema.JaggedArrayNode):
            possible_sections, possible_to_sections = node.address_class(0).get_all_possible_sections_from_string(lang, raw_ref_part.text)
            for sec, toSec in zip(possible_sections, possible_to_sections):
                refined_ref = self.ref.subref(sec)
                if toSec != sec:
                    to_ref = self.ref.subref(toSec)
                    refined_ref = refined_ref.to(to_ref)
                matches += [ResolvedRawRef(self.raw_ref, refined_ref_parts, node, refined_ref)]
        elif raw_ref_part.type == RefPartType.NAMED and isinstance(node, schema.TitledTreeNode):
            if node.ref_part_title_trie(lang).has_continuations(raw_ref_part.text):
                matches += [ResolvedRawRef(self.raw_ref, refined_ref_parts, node, node.ref())]
        elif raw_ref_part.type == RefPartType.DH:
            if isinstance(node, schema.JaggedArrayNode):
                # jagged array node can be skipped entirely if it has a dh child
                # technically doesn't work if there is a referenceable child in between ja and dh node
                node = node.get_referenceable_child(self.ref)
            if isinstance(node, schema.DiburHamatchilNodeSet):
                dh_match = self._get_refined_match_for_dh_part(raw_ref_part, refined_ref_parts, node)
                if dh_match is not None:
                    matches += [dh_match]
        # TODO sham and directional cases
        return matches


class RefPartTitleTrie:

    PREFIXES = {'ב'}

    def __init__(self, lang, nodes=None, sub_trie=None, context=None) -> None:
        """
        :param lang:
        :param nodes:
        :param sub_trie:
        :param context: str. context of the trie. if 'root', take into account 'aloneRefPartTermPrefixes'.
        """
        self.lang = lang
        self.context = context
        if nodes is not None:
            self.__init_with_nodes(nodes)
        else:
            self._trie = sub_trie

    def __init_with_nodes(self, nodes):
        self._trie = {}
        for node in nodes:
            is_index_level = getattr(node, 'index', False) and node == node.index.nodes
            ref_part_terms = node.ref_part_terms[:]
            optional_terms = getattr(node, 'ref_parts_optional', [False]*len(node.ref_part_terms))[:]
            if not is_index_level and self.context == 'root':
                alone_prefixes = getattr(node, "aloneRefPartTermPrefixes", [])
                ref_part_terms = alone_prefixes + ref_part_terms
                optional_terms = [False]*len(alone_prefixes) + optional_terms

            curr_dict_queue = [self._trie]
            for term_slug, optional in zip(ref_part_terms, optional_terms):
                term = NonUniqueTerm.init(term_slug)
                len_curr_dict_queue = len(curr_dict_queue)
                for _ in range(len_curr_dict_queue):
                    curr_dict = curr_dict_queue[0] if optional else curr_dict_queue.pop(0)  # dont remove curr_dict if optional. leave it for next level to add to.
                    for title in term.get_titles(self.lang):
                        if title in curr_dict:
                            temp_dict = curr_dict[title]
                        else:
                            temp_dict = {}
                            curr_dict[title] = temp_dict
                        curr_dict_queue += [temp_dict]
            # add nodes to leaves
            # None key indicates this is a leaf                            
            for curr_dict in curr_dict_queue:
                leaf_node = node.index if is_index_level else node
                if None in curr_dict:
                    curr_dict[None] += [leaf_node]
                else:
                    curr_dict[None] = [leaf_node]

    def __getitem__(self, key):
        return self.get(key)        

    def get(self, key, default=None):
        sub_trie = self._trie.get(key, default)
        if sub_trie is None: return
        return RefPartTitleTrie(self.lang, sub_trie=sub_trie)

    def has_continuations(self, key):
        return self.get_continuations(key, default=None) is not None

    def _merge_two_tries(self, a, b):
        "merges b into a"
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self._merge_two_tries(a[key], b[key])
                elif a[key] == b[key]:
                    pass  # same leaf value
                elif isinstance(a[key], list) and isinstance(b[key], list):
                    a[key] += b[key]
                else:
                    raise Exception('Conflict in _merge_two_tries')
            else:
                a[key] = b[key]
        return a

    def _merge_n_tries(self, *tries):
        from functools import reduce
        if len(tries) == 1:
            return tries[0]
        return reduce(self._merge_two_tries, tries)

    def get_continuations(self, key, default=None):
        continuations = self._get_continuations_recursive(key)
        if len(continuations) == 0:
            return default
        merged = self._merge_n_tries(*continuations)
        return RefPartTitleTrie(self.lang, sub_trie=merged)

    def _get_continuations_recursive(self, key: str, prev_sub_tries=None):
        is_first = prev_sub_tries is None
        prev_sub_tries = prev_sub_tries or self._trie
        next_sub_tries = []
        key = key.strip()
        starti_list = [0]
        if self.lang == 'he' and is_first:
            for prefix in self.PREFIXES:
                if not key.startswith(prefix): continue
                starti_list += [len(prefix)]
        for starti in starti_list:
            for endi in reversed(range(len(key)+1)):
                sub_key = key[starti:endi]
                if sub_key not in prev_sub_tries: continue
                if endi == len(key):
                    next_sub_tries += [prev_sub_tries[sub_key]]
                    continue
                temp_sub_tries = self._get_continuations_recursive(key[endi:], prev_sub_tries[sub_key])
                next_sub_tries += temp_sub_tries
        return next_sub_tries

    def __contains__(self, key):
        return key in self._trie

    def __iter__(self):
        for item in self._trie:
            yield item


class RefResolver:

    def __init__(self, lang, raw_ref_model: Language, raw_ref_part_model: Language) -> None:
        self.lang = lang
        self.raw_ref_model = raw_ref_model
        self.raw_ref_part_model = raw_ref_part_model
    
    def resolve_refs_in_string(self, context_ref: text.Ref, st: str) -> List['ResolvedRawRef']:
        raw_refs = self._get_raw_refs_in_string(st)
        resolved = []
        for raw_ref in raw_refs:
            resolved += self.resolve_raw_ref(context_ref, raw_ref)
        return resolved

    def _get_raw_refs_in_string(self, st: str) -> List['RawRef']:
        """
        ml_raw_ref_out
        ml_raw_ref_part_out
        parse ml out
        """
        raw_refs: List['RawRef'] = []
        raw_ref_spans = self._get_raw_ref_spans_in_string(st)
        for span in raw_ref_spans:
            raw_ref_part_spans = self._get_raw_ref_part_spans_in_string(span.text)
            raw_ref_parts = []
            for part_span in raw_ref_part_spans:
                part_type = RefPartType.span_label_to_enum(part_span.label_)
                dh_cont = None
                if part_type == RefPartType.DH:
                    dh_cont = None  # TODO FILL IN
                raw_ref_parts += [RawRefPart(RefPartSource.INPUT, part_type, part_span, dh_cont)]
            raw_refs += [RawRef(raw_ref_parts, span)]
        return raw_refs

    def _get_raw_ref_spans_in_string(self, st: str) -> List[Span]:
        doc = self.raw_ref_model(st)
        spans = []
        for ent in doc.ents:
            spans += [doc[ent.start:ent.end]]
        return spans

    def _get_raw_ref_part_spans_in_string(self, st: str) -> List[Span]:
        doc = self.raw_ref_part_model(st)
        spans = []
        for ent in doc.ents:
            spans += [doc[ent.start:ent.end]]
        return spans

    def resolve_raw_ref(self, context_ref: text.Ref, raw_ref: 'RawRef') -> List['ResolvedRawRef']:
        unrefined_matches = self.get_unrefined_ref_part_matches(context_ref, raw_ref)
        resolved_list = self.refine_ref_part_matches(unrefined_matches, raw_ref)
        if len(resolved_list) > 1:
            for resolved in resolved_list:
                resolved.ambiguous = True
        return resolved_list

    def get_unrefined_ref_part_matches(self, context_ref: text.Ref, raw_ref: 'RawRef') -> list:
        from .text import library
        return self._get_unrefined_ref_part_matches_recursive(raw_ref, library.get_root_ref_part_title_trie(self.lang))

    def _get_unrefined_ref_part_matches_recursive(self, raw_ref: RawRef, title_trie: RefPartTitleTrie, prev_ref_parts: list=None) -> list:
        ref_parts = raw_ref.raw_ref_parts
        prev_ref_parts = prev_ref_parts or []
        matches = []
        for i, ref_part in enumerate(ref_parts):
            # no need to consider other types at root level
            if ref_part.type != RefPartType.NAMED: continue
            temp_prev_ref_parts = prev_ref_parts + [ref_part]
            temp_title_trie = title_trie.get_continuations(ref_part.text)
            if temp_title_trie is None: continue
            if None in temp_title_trie:
                matches += [ResolvedRawRef(raw_ref, temp_prev_ref_parts, node, (node.nodes if isinstance(node, text.Index) else node).ref()) for node in temp_title_trie[None]]
            temp_ref_parts = [ref_parts[j] for j in range(len(ref_parts)) if j != i]
            matches += self._get_unrefined_ref_part_matches_recursive(RawRef(temp_ref_parts, raw_ref.span), temp_title_trie, temp_prev_ref_parts)
        return self._prune_unrefined_ref_part_matches(matches)

    def refine_ref_part_matches(self, ref_part_matches: list, raw_ref: 'RawRef') -> list:
        fully_refined = []
        match_queue = ref_part_matches[:]
        while len(match_queue) > 0:
            match = match_queue.pop(0)
            unused_ref_parts = match.get_unused_ref_parts(raw_ref)
            has_match = False
            if isinstance(match.node, schema.NumberedTitledTreeNode):
                child = match.node.get_referenceable_child(match.ref)
                children = [] if child is None else [child]
            elif isinstance(match.node, schema.DiburHamatchilNode):
                children = []
            else:
                children = match.node.all_children()
            for child in children:
                for ref_part in unused_ref_parts:
                    temp_matches = match.get_refined_matches(ref_part, child, self.lang)
                    match_queue += temp_matches
                    if len(temp_matches) > 0: has_match = True
            if not has_match:
                fully_refined += [match]
        
        return self._prune_refined_ref_part_matches(fully_refined)

    def _prune_unrefined_ref_part_matches(self, ref_part_matches: List['ResolvedRawRef']) -> List['ResolvedRawRef']:
        index_match_map = defaultdict(list)
        for match in ref_part_matches:
            key = match.node.title if isinstance(match.node, text.Index) else match.node.ref().normal()
            index_match_map[key] += [match]
        pruned_matches = []
        for match_list in index_match_map.values():
            pruned_matches += [max(match_list, key=lambda m: len(m.resolved_ref_parts))]
        return pruned_matches

    def _prune_refined_ref_part_matches(self, ref_part_matches: List['ResolvedRawRef']) -> List['ResolvedRawRef']:
        """
        So far simply returns all matches with the maximum number of resolved_ref_parts
        """
        max_ref_parts = 0
        max_ref_part_matches = []
        for match in ref_part_matches:
            if len(match.resolved_ref_parts) > max_ref_parts:
                max_ref_parts = len(match.resolved_ref_parts)
                max_ref_part_matches = [match]
            elif len(match.resolved_ref_parts) == max_ref_parts:
                max_ref_part_matches += [match]
        return max_ref_part_matches

