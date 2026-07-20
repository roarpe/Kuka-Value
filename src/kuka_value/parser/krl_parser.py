"""KRL parser: builds structured objects from token streams."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from kuka_value.parser.krl_lexer import Token, TokenType, tokenize

logger = logging.getLogger(__name__)


class KrlStruct:
    """Parsed KRL struct literal: {FIELD value, FIELD value, ...}."""

    def __init__(self, entries: dict[str, KrlValue]) -> None:
        self._entries = entries

    def get_float(self, name: str) -> float | None:
        val = self._entries.get(name)
        if val is None:
            return None
        return val.as_float()

    def get_int(self, name: str) -> int | None:
        val = self._entries.get(name)
        if val is None:
            return None
        return val.as_int()

    def get_string(self, name: str) -> str | None:
        val = self._entries.get(name)
        if val is None:
            return None
        return val.as_string()

    def get_struct(self, name: str) -> KrlStruct | None:
        val = self._entries.get(name)
        if val is None:
            return None
        return val.as_struct()

    def fields(self) -> list[str]:
        return list(self._entries.keys())


@dataclass
class KrlValue:
    """A parsed KRL value (number, string, enum, bool, or struct)."""

    raw: str
    _type: str
    _struct: KrlStruct | None = field(default=None, repr=False)

    def as_string(self) -> str | None:
        if self._type != "string":
            return None
        return self.raw

    def as_int(self) -> int | None:
        if self._type != "integer":
            return None
        return int(self.raw)

    def as_float(self) -> float | None:
        if self._type not in ("float", "integer"):
            return None
        return float(self.raw)

    def as_bool(self) -> bool | None:
        if self._type != "boolean":
            return None
        return self.raw == "TRUE"

    def as_enum(self) -> str | None:
        if self._type != "enum":
            return None
        return self.raw

    def as_struct(self) -> KrlStruct | None:
        return self._struct


@dataclass
class KrlAssignment:
    """A parsed KRL assignment: [DECL type] name[index] = value."""

    name: str
    value: KrlValue
    index: int | None = None
    type_name: str | None = None
    is_global: bool = False


class _TokenStream:
    """Cursor over a token list for recursive-descent parsing."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def peek(self) -> Token:
        return self._tokens[self._pos]

    def advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def expect(self, tt: TokenType) -> Token:
        tok = self.advance()
        if tok.type != tt:
            raise ValueError(
                f"Expected {tt.name}, got {tok.type.name} ({tok.value!r}) at {tok.line}:{tok.column}"
            )
        return tok

    def at_end(self) -> bool:
        return self._tokens[self._pos].type == TokenType.EOF

    def match(self, tt: TokenType) -> Token | None:
        if self.peek().type == tt:
            return self.advance()
        return None


def parse_line(text: str) -> KrlAssignment:
    """Parse a single KRL assignment line.

    Supports:
        $VAR = value
        $VAR[index] = value
        DECL TYPE NAME[index] = value
        GLOBAL DECL TYPE NAME[index] = value

    Args:
        text: Single line of KRL

    Returns:
        Parsed assignment

    Raises:
        ValueError: If line cannot be parsed
    """
    tokens = tokenize(text)
    stream = _TokenStream(tokens)
    return _parse_assignment(stream)


def parse_assignments(text: str, *, name_filter: str | None = None) -> list[KrlAssignment]:
    """Parse all assignments from multi-line KRL text.

    Skips comment lines and lines that cannot be parsed.

    Args:
        text: Multi-line KRL source
        name_filter: If set, only return assignments matching this variable name

    Returns:
        List of parsed assignments
    """
    results: list[KrlAssignment] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue

        try:
            assignment = parse_line(stripped)
        except (ValueError, IndexError):
            logger.debug("Skipping unparseable line: %s", stripped[:80])
            continue

        if name_filter is not None and assignment.name != name_filter:
            continue

        results.append(assignment)

    return results


def _parse_assignment(stream: _TokenStream) -> KrlAssignment:
    """Parse a single assignment from token stream."""
    is_global = False
    type_name: str | None = None

    # Optional GLOBAL prefix
    if stream.peek().type == TokenType.KEYWORD and stream.peek().value == "GLOBAL":
        stream.advance()
        is_global = True

    # Optional DECL type_name
    if stream.peek().type == TokenType.KEYWORD and stream.peek().value == "DECL":
        stream.advance()
        type_name = stream.expect(TokenType.IDENTIFIER).value

    # Variable name (IDENTIFIER or SYSTEM_VAR)
    tok = stream.peek()
    if tok.type in (TokenType.SYSTEM_VAR, TokenType.IDENTIFIER):
        name = stream.advance().value
    else:
        raise ValueError(f"Expected variable name, got {tok.type.name} at {tok.line}:{tok.column}")

    # Optional [index]
    index: int | None = None
    if stream.peek().type == TokenType.LBRACKET:
        stream.advance()
        if stream.peek().type == TokenType.INTEGER:
            index = int(stream.advance().value)
        stream.expect(TokenType.RBRACKET)

    # = value
    stream.expect(TokenType.EQUALS)
    value = _parse_value(stream)

    return KrlAssignment(
        name=name,
        value=value,
        index=index,
        type_name=type_name,
        is_global=is_global,
    )


def _parse_value(stream: _TokenStream) -> KrlValue:
    """Parse a KRL value: number, string, enum, bool, or struct."""
    tok = stream.peek()

    if tok.type == TokenType.LBRACE:
        return _parse_struct_value(stream)

    if tok.type == TokenType.STRING:
        stream.advance()
        return KrlValue(raw=tok.value, _type="string")

    if tok.type == TokenType.INTEGER:
        stream.advance()
        return KrlValue(raw=tok.value, _type="integer")

    if tok.type == TokenType.FLOAT:
        stream.advance()
        return KrlValue(raw=tok.value, _type="float")

    if tok.type == TokenType.BOOLEAN:
        stream.advance()
        return KrlValue(raw=tok.value, _type="boolean")

    if tok.type == TokenType.ENUM_VALUE:
        stream.advance()
        return KrlValue(raw=tok.value, _type="enum")

    raise ValueError(
        f"Unexpected token for value: {tok.type.name} ({tok.value!r}) at {tok.line}:{tok.column}"
    )


def _parse_struct_value(stream: _TokenStream) -> KrlValue:
    """Parse a struct literal: {FIELD value, FIELD value, ...}."""
    stream.expect(TokenType.LBRACE)
    entries: dict[str, KrlValue] = {}

    while stream.peek().type != TokenType.RBRACE:
        field_name = stream.expect(TokenType.IDENTIFIER).value
        field_value = _parse_value(stream)
        entries[field_name] = field_value

        if stream.peek().type == TokenType.COMMA:
            stream.advance()

    stream.expect(TokenType.RBRACE)
    struct = KrlStruct(entries)
    return KrlValue(raw="{...}", _type="struct", _struct=struct)
