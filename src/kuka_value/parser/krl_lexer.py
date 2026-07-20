"""KRL lexer: tokenizes KUKA Robot Language source text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """KRL token types."""

    KEYWORD = auto()
    IDENTIFIER = auto()
    SYSTEM_VAR = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    BOOLEAN = auto()
    ENUM_VALUE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    EQUALS = auto()
    COMMA = auto()
    EOF = auto()


KRL_KEYWORDS = frozenset({"DECL", "GLOBAL", "CONST", "SIGNAL", "ENUM", "STRUC"})

_SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "=": TokenType.EQUALS,
    ",": TokenType.COMMA,
}

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


@dataclass
class Token:
    """A single token from KRL source."""

    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


def tokenize(text: str) -> list[Token]:
    """Tokenize KRL source text into a list of tokens.

    Comments (starting with ;) are stripped.
    Whitespace is consumed but not emitted.

    Args:
        text: KRL source text (single or multiple lines)

    Returns:
        List of tokens, always ending with EOF
    """
    tokens: list[Token] = []
    line_num = 0

    for raw_line in text.splitlines():
        line_num += 1
        _tokenize_line(raw_line, line_num, tokens)

    tokens.append(Token(type=TokenType.EOF, value="", line=line_num or 1, column=1))
    return tokens


def _scan_word(line: str, pos: int, length: int) -> int:
    """Advance past an alphanumeric+underscore word, return end position."""
    end = pos + 1
    while end < length and (line[end].isalnum() or line[end] == "_"):
        end += 1
    return end


def _emit_number(line: str, pos: int, line_num: int, col: int, tokens: list[Token]) -> int:
    """Match and emit a number token, return new position."""
    match = _NUMBER_RE.match(line, pos)
    if not match:
        return pos + 1
    val = match.group()
    tt = TokenType.FLOAT if ("." in val or "e" in val.lower()) else TokenType.INTEGER
    tokens.append(Token(tt, val, line_num, col))
    return match.end()


def _tokenize_line(line: str, line_num: int, tokens: list[Token]) -> None:
    """Tokenize a single line, appending results to tokens list."""
    pos = 0
    length = len(line)

    while pos < length:
        char = line[pos]

        if char in " \t\r":
            pos += 1
            continue

        if char == ";":
            return

        col = pos + 1

        if char == '"':
            end = line.index('"', pos + 1)
            tokens.append(Token(TokenType.STRING, line[pos + 1 : end], line_num, col))
            pos = end + 1
        elif char == "#":
            end = _scan_word(line, pos, length)
            tokens.append(Token(TokenType.ENUM_VALUE, line[pos + 1 : end], line_num, col))
            pos = end
        elif char == "$":
            end = _scan_word(line, pos, length)
            tokens.append(Token(TokenType.SYSTEM_VAR, line[pos:end], line_num, col))
            pos = end
        elif char in _SINGLE_CHAR_TOKENS:
            tokens.append(Token(_SINGLE_CHAR_TOKENS[char], char, line_num, col))
            pos += 1
        elif char.isdigit() or (
            char == "-" and pos + 1 < length and line[pos + 1].isdigit()
        ):
            pos = _emit_number(line, pos, line_num, col, tokens)
        elif char.isalpha() or char == "_":
            end = _scan_word(line, pos, length)
            word = line[pos:end]
            if word in ("TRUE", "FALSE"):
                tokens.append(Token(TokenType.BOOLEAN, word, line_num, col))
            elif word in KRL_KEYWORDS:
                tokens.append(Token(TokenType.KEYWORD, word, line_num, col))
            else:
                tokens.append(Token(TokenType.IDENTIFIER, word, line_num, col))
            pos = end
        else:
            pos += 1
