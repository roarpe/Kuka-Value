"""Unit tests for KRL lexer/tokenizer."""

from kuka_value.parser.krl_lexer import TokenType, tokenize


class TestTokenType:
    """Test token classification."""

    def test_simple_assignment(self) -> None:
        tokens = tokenize('$TRAFONAME[]="KR240R2900"')
        types = [t.type for t in tokens]
        assert types == [
            TokenType.SYSTEM_VAR,
            TokenType.LBRACKET,
            TokenType.RBRACKET,
            TokenType.EQUALS,
            TokenType.STRING,
            TokenType.EOF,
        ]

    def test_numeric_values(self) -> None:
        tokens = tokenize("M 10.5")
        types = [t.type for t in tokens]
        assert types == [TokenType.IDENTIFIER, TokenType.FLOAT, TokenType.EOF]

    def test_negative_number(self) -> None:
        tokens = tokenize("M -1.0")
        types = [t.type for t in tokens]
        assert types == [TokenType.IDENTIFIER, TokenType.FLOAT, TokenType.EOF]

    def test_integer(self) -> None:
        tokens = tokenize("A1 90")
        types = [t.type for t in tokens]
        assert types == [TokenType.IDENTIFIER, TokenType.INTEGER, TokenType.EOF]

    def test_negative_integer(self) -> None:
        tokens = tokenize("A2 -90")
        types = [t.type for t in tokens]
        assert types == [TokenType.IDENTIFIER, TokenType.INTEGER, TokenType.EOF]

    def test_struct_literal(self) -> None:
        tokens = tokenize("{X 1.0,Y 2.0,Z 3.0}")
        types = [t.type for t in tokens]
        assert types == [
            TokenType.LBRACE,
            TokenType.IDENTIFIER,
            TokenType.FLOAT,
            TokenType.COMMA,
            TokenType.IDENTIFIER,
            TokenType.FLOAT,
            TokenType.COMMA,
            TokenType.IDENTIFIER,
            TokenType.FLOAT,
            TokenType.RBRACE,
            TokenType.EOF,
        ]

    def test_enum_value(self) -> None:
        tokens = tokenize("$ROBOT_TYPE=#KR_240_R2900")
        types = [t.type for t in tokens]
        assert types == [
            TokenType.SYSTEM_VAR,
            TokenType.EQUALS,
            TokenType.ENUM_VALUE,
            TokenType.EOF,
        ]

    def test_decl_keyword(self) -> None:
        tokens = tokenize("DECL LOAD_DATA LOAD_DATA[1]={M 10.0}")
        types = [t.type for t in tokens]
        assert types == [
            TokenType.KEYWORD,
            TokenType.IDENTIFIER,
            TokenType.IDENTIFIER,
            TokenType.LBRACKET,
            TokenType.INTEGER,
            TokenType.RBRACKET,
            TokenType.EQUALS,
            TokenType.LBRACE,
            TokenType.IDENTIFIER,
            TokenType.FLOAT,
            TokenType.RBRACE,
            TokenType.EOF,
        ]

    def test_comment_ignored(self) -> None:
        tokens = tokenize("M 10.0 ; this is mass")
        types = [t.type for t in tokens]
        assert types == [TokenType.IDENTIFIER, TokenType.FLOAT, TokenType.EOF]

    def test_full_line_comment(self) -> None:
        tokens = tokenize("; full comment line")
        types = [t.type for t in tokens]
        assert types == [TokenType.EOF]

    def test_boolean_true(self) -> None:
        tokens = tokenize("$FLAG[1]=TRUE")
        bool_tokens = [t for t in tokens if t.type == TokenType.BOOLEAN]
        assert len(bool_tokens) == 1
        assert bool_tokens[0].value == "TRUE"

    def test_boolean_false(self) -> None:
        tokens = tokenize("$FLAG[1]=FALSE")
        bool_tokens = [t for t in tokens if t.type == TokenType.BOOLEAN]
        assert len(bool_tokens) == 1
        assert bool_tokens[0].value == "FALSE"


class TestTokenValues:
    """Test that token values are correctly extracted."""

    def test_string_value_unquoted(self) -> None:
        tokens = tokenize('$NAME[]="Hello World"')
        string_token = [t for t in tokens if t.type == TokenType.STRING][0]
        assert string_token.value == "Hello World"

    def test_float_value(self) -> None:
        tokens = tokenize("M 10.500")
        float_token = [t for t in tokens if t.type == TokenType.FLOAT][0]
        assert float_token.value == "10.500"

    def test_negative_float_value(self) -> None:
        tokens = tokenize("M -3.14")
        float_token = [t for t in tokens if t.type == TokenType.FLOAT][0]
        assert float_token.value == "-3.14"

    def test_integer_value(self) -> None:
        tokens = tokenize("[15]")
        int_token = [t for t in tokens if t.type == TokenType.INTEGER][0]
        assert int_token.value == "15"

    def test_system_var_value(self) -> None:
        tokens = tokenize("$LOAD_DATA[1]")
        sysvar = [t for t in tokens if t.type == TokenType.SYSTEM_VAR][0]
        assert sysvar.value == "$LOAD_DATA"

    def test_enum_value_content(self) -> None:
        tokens = tokenize("#MY_ENUM_VAL")
        enum_tok = [t for t in tokens if t.type == TokenType.ENUM_VALUE][0]
        assert enum_tok.value == "MY_ENUM_VAL"

    def test_identifier_value(self) -> None:
        tokens = tokenize("LOAD_DATA")
        ident = [t for t in tokens if t.type == TokenType.IDENTIFIER][0]
        assert ident.value == "LOAD_DATA"


class TestTokenPosition:
    """Test line/column tracking."""

    def test_single_line_positions(self) -> None:
        tokens = tokenize("M 10.0")
        assert tokens[0].line == 1
        assert tokens[0].column == 1
        assert tokens[1].line == 1
        assert tokens[1].column == 3

    def test_token_repr(self) -> None:
        tokens = tokenize("M 10.0")
        assert "IDENTIFIER" in repr(tokens[0])
        assert "M" in repr(tokens[0])


class TestMultilineTokenization:
    """Test tokenizing multiple lines."""

    def test_multiline_input(self) -> None:
        text = """\
$LOAD_DATA[1]={M 10.0}
$LOAD_DATA[2]={M 20.0}
"""
        tokens = tokenize(text)
        sys_vars = [t for t in tokens if t.type == TokenType.SYSTEM_VAR]
        assert len(sys_vars) == 2

    def test_mixed_comments_and_code(self) -> None:
        text = """\
; Header comment
$LOAD_DATA[1]={M 10.0}
; Another comment
$LOAD_DATA[2]={M 20.0}
"""
        tokens = tokenize(text)
        sys_vars = [t for t in tokens if t.type == TokenType.SYSTEM_VAR]
        assert len(sys_vars) == 2

    def test_real_load_data_line(self) -> None:
        """Test a realistic LOAD_DATA line from a KUKA backup."""
        line = (
            "DECL LOAD_DATA LOAD_DATA[1]="
            "{M 10.500,CM {X 100.0,Y 0.0,Z 50.0,A 0.0,B 0.0,C 0.0},"
            "J {X 0.500,Y 0.500,Z 0.300}}"
        )
        tokens = tokenize(line)
        # Should not raise and should produce valid tokens
        assert tokens[-1].type == TokenType.EOF
        identifiers = [t for t in tokens if t.type == TokenType.IDENTIFIER]
        assert any(t.value == "LOAD_DATA" for t in identifiers)
        assert any(t.value == "M" for t in identifiers)
        assert any(t.value == "CM" for t in identifiers)
        assert any(t.value == "J" for t in identifiers)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self) -> None:
        tokens = tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_whitespace_only(self) -> None:
        tokens = tokenize("   \t  ")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_scientific_notation(self) -> None:
        tokens = tokenize("M 1.5E-3")
        float_token = [t for t in tokens if t.type == TokenType.FLOAT][0]
        assert float_token.value == "1.5E-3"

    def test_global_keyword(self) -> None:
        tokens = tokenize("GLOBAL DECL INT MY_VAR=5")
        types = [t.type for t in tokens]
        assert types[0] == TokenType.KEYWORD
        assert tokens[0].value == "GLOBAL"
