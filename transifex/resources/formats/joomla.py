# -*- coding: utf-8 -*-

"""
Joomla INI file handler/compiler
"""
import os, re
import codecs

from transifex.txcommon.log import logger
from transifex.resources.models import SourceEntity
from transifex.resources.formats.utils.decorators import *
from transifex.resources.formats.utils.hash_tag import hash_tag
from transifex.resources.formats.core import GenericTranslation, Handler, \
        STRICT, StringSet


class JoomlaINIHandler(Handler):
    """
    Handler for Joomla's INI translation files.

    See http://docs.joomla.org/Specification_of_language_files
    and http://docs.joomla.org/Creating_a_language_definition_file.
    """
    name = "Joomla *.INI file handler"
    format = "Joomla INI (*.ini)"
    method_name = 'INI'
    comment_chars = ('#', ';', ) # '#' is for 1.5 and ';' for >1.6

    @classmethod
    def is_content_valid(cls, filename):
        pass

    def __init__(self, filename=None, resource= None, language = None):
        super(JoomlaINIHandler, self).__init__(filename, resource, language)
        self._version = 0

    @need_language
    @need_file
    def parse_file(self, is_source=False, lang_rules=None):
        """
        Parse an INI file and create a stringset with all entries in the file.
        """
        stringset = StringSet()
        suggestions = StringSet()

        fh = codecs.open(self.filename, "r", "utf-8")
        try:
            buf = u""
            self.find_linesep(fh)
            for line in fh:
                line = self._prepare_line(line)
                # Skip empty lines and comments
                if not line or line.startswith(self.comment_chars):
                    if is_source:
                        buf += line + self._linesep
                    continue

                try:
                    source, trans = line.split('=', 1)
                except ValueError:
                    # Maybe abort instead of skipping?
                    logger.error('Could not parse line "%s". Skipping...' % line)
                    continue

                # In versions >=1.6 translations are surrounded by double quotes. So remove them
                # Normally, if the translation starts with '"', it is a 1.6-file and must
                # end with '"', since translations starting with '"' are not allowed in 1.5.
                # But, let's check both the first and last character of the translation to be safe.
                if trans.startswith('"') and trans.endswith('"'):
                    trans = trans[1:-1]

                # We use empty context
                context = ""

                if is_source:
                    if not trans.strip():
                        buf += line + self._linesep
                        continue
                    source_len = len(source)
                    new_line = line[:source_len] + re.sub(
                        re.escape(trans),
                        "%(hash)s_tr" % {'hash': hash_tag(source, context)},
                        line[source_len:]
                    )
                    # this looks fishy
                    buf += new_line + self._linesep

                elif not SourceEntity.objects.filter(resource=self.resource, string=source).exists() or not trans.strip():
                    #ignore keys with no translation
                    continue

                stringset.strings.append(GenericTranslation(source,
                    trans, rule=5, context=context,
                    pluralized=False, fuzzy=False,
                    obsolete=False))
        finally:
            fh.close()

        self.stringset=stringset
        self.suggestions=suggestions

        if is_source:
            self.template = str(buf.encode('utf-8'))

    def _examine_content(self, content):
        """
        If the first line begins with ';', mark the version of the
        ini file as 1 (>=1.6), else as 0 (==1.5).
        """
        if content.startswith(';'):
            self._version = 1
        else:
            self._version = 0

    def _escape(self, s):
        return s.replace('\\', '\\\\')
