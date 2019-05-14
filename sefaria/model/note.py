"""
note.py
Writes to MongoDB Collection: notes
"""

import regex as re
import bleach

from . import abstract as abst
from sefaria.model.text import Ref, IndexSet
from sefaria.system.exceptions import InputError


class Note(abst.AbstractMongoRecord):
    """
    A note on a specific place in a text.  May be public or private.
    """
    collection    = 'notes'
    history_noun  = 'note'
    ALLOWED_TAGS  = ("i", "b", "br", "u", "strong", "em", "big", "small", "span", "div", "img", "a")
    ALLOWED_ATTRS = {
                        '*': ['class'],
                        'a': ['href', 'rel'],
                        'img': ['src', 'alt'],
                    }

    required_attrs = [
        "owner",
        "public",
        "text",
        "type",
        "ref"
    ]
    optional_attrs = [
        "title",
        "anchorText"
    ]

    def contents(self, **kwargs):
        d = super(Note, self).contents(**kwargs)
        if kwargs.get("with_ref_text", False):
            try:
                oref = Ref(self.ref)
                en_text = oref.text("en").as_string()
                he_text = oref.text("he").as_string()
                d["ref_text"] = {
                    "en": en_text,
                    "he": he_text
                }
            except InputError:
                pass
        return d

    def _normalize(self):
        self.ref = Ref(self.ref).normal()


class NoteSet(abst.AbstractMongoSet):
    recordClass = Note


def process_index_title_change_in_notes(indx, **kwargs):
    print "Cascading Notes {} to {}".format(kwargs['old'], kwargs['new'])
    pattern = Ref(indx.title).regex()
    pattern = pattern.replace(re.escape(indx.title), re.escape(kwargs["old"]))
    notes = NoteSet({"ref": {"$regex": pattern}})
    for n in notes:
        try:
            n.ref = n.ref.replace(kwargs["old"], kwargs["new"], 1)
            n.save()
        except Exception:
            logger.warning("Deleting note that failed to save: {}".format(n.ref))
            n.delete()

def process_index_delete_in_notes(indx, **kwargs):
    from sefaria.model.text import prepare_index_regex_for_dependency_process
    pattern = prepare_index_regex_for_dependency_process(indx)
    NoteSet({"ref": {"$regex": pattern}}).delete()
