"""Validate JSONC and edit a root property without rewriting unrelated comments."""

import json
import re
from dataclasses import dataclass


_TOKEN = re.compile(
    r'(?P<space>\s+)|(?P<line>//[^\r\n]*)|(?P<block>/\*[\s\S]*?\*/)|'
    r'(?P<string>"(?:[^"\\\x00-\x1f]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*")|'
    r'(?P<number>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)|'
    r'(?P<literal>true|false|null)|(?P<punct>[{}\[\]:,])'
)


@dataclass(frozen=True)
class Token:
    value: str
    start: int
    end: int


def tokens(text):
    result = []
    offset = 0
    while offset < len(text):
        match = _TOKEN.match(text, offset)
        if match is None:
            raise ValueError(f'Invalid JSONC at character {offset + 1}')
        if match.lastgroup not in ('space', 'line', 'block'):
            result.append(Token(match.group(), offset, match.end()))
        offset = match.end()
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def loads(text):
    items = tokens(text)
    normalized = ' '.join(
        token.value for index, token in enumerate(items)
        if not (token.value == ',' and 0 < index < len(items) - 1
                and items[index - 1].value not in ('{', '[', ',', ':')
                and items[index + 1].value in (']', '}'))
    )
    return json.loads(normalized, object_pairs_hook=_unique_object)


def require_type(text, expected):
    value = loads(text)
    if not isinstance(value, expected):
        raise ValueError(f'Expected a JSONC {expected.__name__}')
    return value


def set_root_property(text, key, value):
    """Set a root property, or remove it when value is None."""
    original = require_type(text, dict)
    items = tokens(text)
    members = []
    index = 1
    while items[index].value != '}':
        key_token = items[index]
        start_value = index + 2
        index = start_value
        depth = 0
        while True:
            current = items[index].value
            if depth == 0 and current in (',', '}'):
                break
            if current in ('{', '['):
                depth += 1
            elif current in ('}', ']'):
                depth -= 1
            index += 1
        comma = items[index] if items[index].value == ',' else None
        members.append((json.loads(key_token.value), key_token, items[start_value],
                        items[index - 1], comma))
        if comma:
            index += 1
    replacement = json.dumps(value, ensure_ascii=False, indent=2)
    replacement = replacement.replace('\n', '\n  ')
    for position, (name, key_token, first, last, comma) in enumerate(members):
        if name != key:
            continue
        if value is not None:
            result = text[:first.start] + replacement + text[last.end:]
        else:
            start, end = key_token.start, last.end
            if comma:
                end = comma.end
                line_start = text.rfind('\n', 0, start) + 1
                line_end = text.find('\n', end)
                if (not text[line_start:start].strip() and line_end != -1
                        and not text[end:line_end].strip()):
                    start, end = line_start, line_end + 1
            elif position:
                start = members[position - 1][4].start
            result = text[:start] + text[end:]
        break
    else:
        if value is None:
            return text
        last = members[-1] if members else None
        insert_at = items[-1].start
        if last and last[4] is None:
            # NOTE: add the separator before any trailing line comment.
            text = text[:last[3].end] + ',' + text[last[3].end:]
            insert_at += 1
        entry = f'\n  {json.dumps(key)}: {replacement}\n'
        result = text[:insert_at] + entry + text[insert_at:]
    expected = dict(original)
    if value is None:
        expected.pop(key, None)
    else:
        expected[key] = value
    if require_type(result, dict) != expected:
        raise ValueError('JSONC edit did not preserve the original configuration')
    return result
