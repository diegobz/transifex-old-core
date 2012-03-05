# -*- coding: utf-8 -*-

"""
Generic properties format super class.
"""
from __future__ import absolute_import
import os, re
from django.utils.hashcompat import md5_constructor

from transifex.txcommon.log import logger
from transifex.resources.models import SourceEntity
from transifex.resources.formats.utils.decorators import *
from transifex.resources.formats.utils.hash_tag import hash_tag
from transifex.resources.formats.core import Handler, ParseError, CompileError
from transifex.resources.formats.resource_collections import StringSet, \
        GenericTranslation
from .compilation import Compiler, MarkedSourceCompilerFactory


class PropertiesParseError(ParseError):
    pass


class PropertiesCompileError(CompileError):
    pass


class PropertiesCompiler(Compiler):
    """Compiler for .properties formats."""

    def _post_compile(self):
        """Comment out source strings."""
        pattern = r'(?P<actual>.*)_txss'
        regex = re.compile(pattern)
        self.compiled_template = regex.sub(
            lambda m: '# '+ m.group('actual'), self.compiled_template
        )


class PropertiesHandler(MarkedSourceCompilerFactory, Handler):
    """
    Handler for PROPERTIES translation files.
    """

    HandlerParseError = PropertiesParseError
    HandlerCompileError = PropertiesCompileError

    SEPARATORS = [' ', '\t', '\f', '=', ':', ]
    comment_chars = ('#', '!', )

    def _escape(self, s):
        """Escape special characters in properties files.

        Java escapes the '=' and ':' in the value
        string with backslashes in the store method.
        So let us do the same.
        """
        return (
            s.replace(':', '\:')
            .replace('=', '\=')
            .replace('\\', '\\\\')
        )

    def _is_escaped(self, line, index):
        """Returns True, if the character at index is escaped by backslashes.

        There has to be an even number of backslashes before the character for
        it to be escaped.
        """
        nbackslashes = 0
        for c in reversed(line[:index]):
            if c == '\\':
                nbackslashes += 1
            else:
                break
        return nbackslashes % 2 == 1

    def _split(self, line):
        """
        Split a line in (key, value).

        The separator is the first non-escaped charcter of (\s,=,:).
        If no such character exists, the wholi line is a key with no value.
        """
        for i, c in enumerate(line):
            if c in self.SEPARATORS and not self._is_escaped(line, i):
                # Seperator found
                key = line[:i].lstrip()
                value = self._strip_separators(line[i+1:])
                return (key, value)
        return (line, None)

    def _strip_separators(self, s):
        """Strip separators from the front of the string s."""
        return s.lstrip(''.join(self.SEPARATORS))

    def _unescape(self, value):
        """Reverse the escape of special characters."""
        return (value.replace('\:', ':')
                     .replace('\=', '=')
                     .replace('\\\\', '\\')
        )

    def _visit_value(self, value):
        """Give a chance to check the value from the file before using it."""
        return value

    def _parse(self, is_source, lang_rules):
        """Parse a .properties content and create a stringset with
        all entries in it.
        """
        resource = self.resource

        context = ""
        self._find_linesep(self.content)
        template = u""
        lines = self._iter_by_line(self.content)
        for line in lines:
            line = self._prepare_line(line)
            # Skip empty lines and comments
            if not line or line.startswith(self.comment_chars):
                if is_source:
                    template += line + self.linesep
                continue
            # If the last character is a backslash
            # it has to be preceded by a space in which
            # case the next line is read as part of the
            # same property
            while line[-1] == '\\' and not self._is_escaped(line, -1):
                # Read next line
                nextline = self._prepare_line(lines.next())
                # This line will become part of the value
                line = line[:-1] + self._prepare_line(nextline)

            key, value, old_value = self._key_value_from_line(line)
            if is_source:
                if not value:
                    template += line + self.linesep
                    # Keys with no values should not be shown to translator
                    continue
                else:
                    key_len = len(key)
                    template += line[:key_len] + re.sub(
                        re.escape(old_value),
                        "%(hash)s_tr" % {'hash': hash_tag(key, context)},
                        line[key_len:]
                    ) + self.linesep
            elif not SourceEntity.objects.filter(resource=resource, string=key).exists():
                # ignore keys with no translation
                continue

            self.stringset.add(GenericTranslation(
                    key, self._unescape(value), context=context
            ))
        return template

    def _key_value_from_line(self, line):
        """Get the key and the value from a line of the file."""
        key, value = self._split(line)
        return (key, self._visit_value(value), value)

