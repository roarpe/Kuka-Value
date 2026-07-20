"""Unit tests for KRL structure parser."""

from kuka_value.parser.krl_parser import (
    KrlAssignment,
    parse_assignments,
    parse_line,
)


class TestParseSimpleAssignment:
    """Test parsing simple variable assignments."""

    def test_string_assignment(self) -> None:
        result = parse_line('$TRAFONAME[]="KR240R2900"')
        assert isinstance(result, KrlAssignment)
        assert result.name == "$TRAFONAME"
        assert result.index is None
        assert result.value.as_string() == "KR240R2900"

    def test_indexed_string_assignment(self) -> None:
        result = parse_line('$ROBCOR_NAME[1]="KR 240 R2900"')
        assert isinstance(result, KrlAssignment)
        assert result.name == "$ROBCOR_NAME"
        assert result.index == 1
        assert result.value.as_string() == "KR 240 R2900"

    def test_enum_assignment(self) -> None:
        result = parse_line("$ROBOT_TYPE=#KR_240_R2900")
        assert isinstance(result, KrlAssignment)
        assert result.value.as_enum() == "KR_240_R2900"

    def test_integer_assignment(self) -> None:
        result = parse_line("$AXIS_NUM=6")
        assert isinstance(result, KrlAssignment)
        assert result.value.as_int() == 6

    def test_float_assignment(self) -> None:
        result = parse_line("$MAX_SPEED=250.0")
        assert isinstance(result, KrlAssignment)
        assert result.value.as_float() == 250.0

    def test_boolean_assignment(self) -> None:
        result = parse_line("$FLAG[1]=TRUE")
        assert isinstance(result, KrlAssignment)
        assert result.value.as_bool() is True

    def test_negative_value(self) -> None:
        result = parse_line("$OFFSET=-100.5")
        assert isinstance(result, KrlAssignment)
        assert result.value.as_float() == -100.5


class TestParseStructAssignment:
    """Test parsing struct literal assignments."""

    def test_flat_struct(self) -> None:
        result = parse_line("$TOOL_DATA[1]={X 0.0,Y 0.0,Z 100.0,A 0.0,B 0.0,C 0.0}")
        assert isinstance(result, KrlAssignment)
        assert result.name == "$TOOL_DATA"
        assert result.index == 1

        struct = result.value.as_struct()
        assert struct.get_float("X") == 0.0
        assert struct.get_float("Z") == 100.0

    def test_nested_struct(self) -> None:
        line = (
            "$LOAD_DATA[1]={M 10.5,"
            "CM {X 100.0,Y 0.0,Z 50.0,A 0.0,B 0.0,C 0.0},"
            "J {X 0.5,Y 0.5,Z 0.3}}"
        )
        result = parse_line(line)
        assert isinstance(result, KrlAssignment)

        struct = result.value.as_struct()
        assert struct.get_float("M") == 10.5

        cm = struct.get_struct("CM")
        assert cm is not None
        assert cm.get_float("X") == 100.0
        assert cm.get_float("Z") == 50.0

        j = struct.get_struct("J")
        assert j is not None
        assert j.get_float("X") == 0.5

    def test_struct_with_negative_values(self) -> None:
        result = parse_line(
            "$LOAD_DATA[3]={M -1.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}"
        )
        struct = result.value.as_struct()
        assert struct.get_float("M") == -1.0


class TestParseDeclStatement:
    """Test parsing DECL statements."""

    def test_decl_with_struct(self) -> None:
        line = "DECL LOAD_DATA LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}"
        result = parse_line(line)
        assert isinstance(result, KrlAssignment)
        assert result.name == "LOAD_DATA"
        assert result.type_name == "LOAD_DATA"
        assert result.index == 1

    def test_decl_with_simple_value(self) -> None:
        line = "DECL INT MY_VAR=42"
        result = parse_line(line)
        assert isinstance(result, KrlAssignment)
        assert result.name == "MY_VAR"
        assert result.type_name == "INT"
        assert result.value.as_int() == 42

    def test_global_decl(self) -> None:
        line = "GLOBAL DECL REAL SPEED=100.0"
        result = parse_line(line)
        assert isinstance(result, KrlAssignment)
        assert result.name == "SPEED"
        assert result.is_global is True


class TestKrlStruct:
    """Test KrlStruct access methods."""

    def test_get_float_missing_returns_none(self) -> None:
        result = parse_line("$DATA[1]={X 1.0,Y 2.0}")
        struct = result.value.as_struct()
        assert struct.get_float("Z") is None

    def test_get_string(self) -> None:
        result = parse_line('$INFO[1]={NAME "robot1",ID 5}')
        struct = result.value.as_struct()
        assert struct.get_string("NAME") == "robot1"

    def test_fields_property(self) -> None:
        result = parse_line("$DATA[1]={X 1.0,Y 2.0,Z 3.0}")
        struct = result.value.as_struct()
        assert set(struct.fields()) == {"X", "Y", "Z"}

    def test_get_int(self) -> None:
        result = parse_line("$DATA[1]={COUNT 5,OFFSET 10}")
        struct = result.value.as_struct()
        assert struct.get_int("COUNT") == 5


class TestParseAssignments:
    """Test parsing multiple assignments from text."""

    def test_parse_multiple_lines(self) -> None:
        text = """\
; Header
$LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}
$LOAD_DATA[2]={M 25.0,CM {X 50.0,Y 0.0,Z 100.0,A 0.0,B 0.0,C 0.0},J {X 0.5,Y 0.5,Z 0.3}}
; Footer
"""
        assignments = parse_assignments(text)
        assert len(assignments) == 2
        assert assignments[0].index == 1
        assert assignments[1].index == 2

    def test_parse_filters_by_name(self) -> None:
        text = """\
$LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}
$TOOL_DATA[1]={X 0.0,Y 0.0,Z 100.0,A 0.0,B 0.0,C 0.0}
$LOAD_DATA[2]={M 20.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}
"""
        load_data = parse_assignments(text, name_filter="$LOAD_DATA")
        assert len(load_data) == 2

        tool_data = parse_assignments(text, name_filter="$TOOL_DATA")
        assert len(tool_data) == 1

    def test_parse_skips_unparseable_lines(self) -> None:
        text = """\
$LOAD_DATA[1]={M 10.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}
SOME RANDOM TEXT THAT IS NOT AN ASSIGNMENT
$LOAD_DATA[2]={M 20.0,CM {X 0.0,Y 0.0,Z 0.0,A 0.0,B 0.0,C 0.0},J {X 0.0,Y 0.0,Z 0.0}}
"""
        assignments = parse_assignments(text)
        assert len(assignments) == 2

    def test_parse_empty_text(self) -> None:
        assignments = parse_assignments("")
        assert len(assignments) == 0

    def test_parse_comments_only(self) -> None:
        text = """\
; comment 1
; comment 2
"""
        assignments = parse_assignments(text)
        assert len(assignments) == 0


class TestKrlValue:
    """Test KrlValue type conversions."""

    def test_as_string_on_non_string_returns_none(self) -> None:
        result = parse_line("$VAR=42")
        assert result.value.as_string() is None

    def test_as_int_on_float_returns_none(self) -> None:
        result = parse_line("$VAR=42.5")
        assert result.value.as_int() is None

    def test_as_float_on_string_returns_none(self) -> None:
        result = parse_line('$VAR="hello"')
        assert result.value.as_float() is None

    def test_as_struct_on_non_struct_returns_none(self) -> None:
        result = parse_line("$VAR=42")
        assert result.value.as_struct() is None

    def test_as_bool_on_non_bool_returns_none(self) -> None:
        result = parse_line("$VAR=42")
        assert result.value.as_bool() is None

    def test_as_enum_on_non_enum_returns_none(self) -> None:
        result = parse_line("$VAR=42")
        assert result.value.as_enum() is None

    def test_raw_value(self) -> None:
        result = parse_line("$VAR=42")
        assert result.value.raw == "42"
