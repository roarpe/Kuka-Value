# Architecture

## Design Principles

Kuka-Value is built on **Clean Architecture** with strict layer separation:

### Layer Organization

```
UI Layer (PySide6)
    ↓
Engine Layer (Orchestration)
    ↓
Business Logic (Analyzers, Parsers)
    ↓
Data Models (Dataclasses)
```

### Key Principles

1. **Dependency Inversion**: High-level modules never depend on low-level modules
2. **Separation of Concerns**: Each module has a single responsibility
3. **Testability**: Business logic independent from UI and I/O
4. **Extensibility**: Adding new features (analyzers, exporters) requires minimal changes
5. **No Mixed Responsibilities**: Never couple UI logic with file I/O or data processing

## Module Breakdown

### `engine/`

**Responsibility**: Core orchestration and API

- `Engine` class: Main entry point
- Coordinates parser, analyzers, exporters
- Handles workflow: parse → analyze → export
- Never touches UI directly
- Returns domain models only

**Public Interface**:
```python
class Engine:
    def parse(self, backup_path: Path) -> RobotInfo: ...
    def export(self, robot: RobotInfo, exporter: Exporter) -> None: ...
```

### `parser/`

**Responsibility**: Reading and parsing KRL structures

Components:
- `BackupReader`: Handles ZIP and folder inputs
- `Lexer`: Tokenizes KRL syntax
- `Tokenizer`: Produces token stream
- `Parser`: Builds AST from tokens
- `KrlStructureParser`: Generic structure parsing

**Design Pattern**: Lexer → Tokenizer → Parser

This ensures:
- Reusability across LOAD_DATA, TOOL_DATA, BASE_DATA, etc.
- Clear error reporting with line/column info
- No regex-only parsing (prone to edge cases)

### `analyzers/`

**Responsibility**: Domain-specific analysis

- `RobotAnalyzer`: Detects robot model, KSS version, controller type
  - Strategy: TRAFONAME → MACHINE.DAT → ROBCOR → fallback
  - Normalizes names: "KR240R2900" → "KR 240 R2900"

- `PayloadAnalyzer`: Extracts and deduplicates payload data
  - Finds all LOAD_DATA structures
  - Extracts: mass, center of gravity, inertia
  - Removes duplicates (preserves indices)
  - Ignores empty payloads (M=-1, M=0)

- Each analyzer is independent and testable
- Takes parsed data, returns domain models

### `exporters/`

**Responsibility**: Multi-format output

- `CsvExporter`: Comma-separated values
- `ExcelExporter`: .xlsx with formatting
- `JsonExporter`: Hierarchical JSON
- `PdfExporter` (future): Professional reports

**Design Pattern**: Each exporter implements `Exporter` interface

### `models/`

**Responsibility**: Domain model definitions

Dataclasses (immutable where possible):
- `RobotInfo`: Complete robot configuration
- `PayloadInfo`: Single payload data
- `ControllerInfo`: Controller details
- `GeneralInfo`: Backup metadata
- `WarningLog`: Errors/warnings during analysis

**Rules**:
- Never return dictionaries from public API
- Type hints on all fields
- Use `frozen=True` when semantically immutable
- No default mutable values (use field factories)

### `ui/`

**Responsibility**: User interface (PySide6)

- Never calls parsers or file I/O directly
- Only uses `Engine` public interface
- Passes results to exporters via dependency injection
- Implements async loading with progress feedback

## Data Flow

```
User selects backup file
    ↓
UI calls engine.parse(path)
    ↓
BackupReader extracts/indexes files
    ↓
Parser converts text → AST
    ↓
RobotAnalyzer identifies robot
    ↓
PayloadAnalyzer extracts payloads
    ↓
Models assembled into RobotInfo
    ↓
UI displays results
    ↓
User exports via engine.export()
    ↓
Exporter writes file
```

## Error Handling

### No Exceptions for Incomplete Data

- Backups may be missing files or have corrupt structures
- **Never throw exceptions** for incomplete data
- Instead: Record warnings in `WarningLog`
- Continue analysis with available data
- User sees partial results + warnings

**Example**:
```python
if machine_dat_missing:
    robot.warnings.append(WarningType.MACHINE_DAT_NOT_FOUND)
    # Continue with other analysis methods
```

### Exception Types

Only throw exceptions for:
- File not found (path validation)
- ZIP corruption (I/O layer)
- Invalid configuration (engine setup)

## Type System

- All public functions have complete type hints
- `mypy --strict` must pass
- No `Any` types without justification
- Use Union/Optional carefully
- Protocols for dependency injection

## Testing Strategy

### Unit Tests

- Test each module independently
- Mock external dependencies
- Focus on business logic
- Target: 90%+ coverage per module

**Structure**:
```
tests/unit/
├── test_backup_reader.py      # I/O layer
├── test_lexer.py              # Parser components
├── test_tokenizer.py
├── test_parser.py
├── test_robot_analyzer.py     # Analyzers
├── test_payload_analyzer.py
├── test_models.py             # Data models
└── ...
```

### Integration Tests

- Test module interactions
- Use real backup files (fixtures)
- Verify end-to-end workflows
- Cover error recovery

**Structure**:
```
tests/integration/
├── test_full_analysis.py      # Complete pipeline
├── test_robot_detection.py
├── test_payload_extraction.py
└── test_export_formats.py
```

## Extensibility

### Adding a New Analyzer

1. Create `NewAnalyzer` in `analyzers/`
2. Implement: `def analyze(data: ParsedData) -> AnalysisResult`
3. Add test in `tests/unit/test_new_analyzer.py`
4. Register in `Engine.analyze()` method
5. Update `RobotInfo` if needed

### Adding a New Exporter

1. Create `NewExporter(Exporter)` in `exporters/`
2. Implement: `def export(robot: RobotInfo) -> bytes`
3. Add to UI export menu
4. Test with real `RobotInfo` data

### Adding Support for New Structure (TOOL_DATA, etc.)

1. Extend `Parser` to recognize new structure
2. Add parsing tests
3. Create specific analyzer if needed
4. Add to model definitions
5. Update exporters to include new data

## Performance Considerations

### Target: < 2 seconds for 1 GB backup

Optimization strategies:
1. **Single-pass file indexing**: Build index on first read
2. **Lazy parsing**: Don't parse files until needed
3. **Streaming tokenization**: Don't load entire file in memory
4. **Cache**: Store parsed structures for repeated access

### Monitoring

- Logging includes timing info
- Profile with `cProfile` for bottlenecks
- Never optimize prematurely

## Configuration

### Logging Levels

```python
import logging

# User can set:
# DEBUG: Full parsing details, all files indexed
# INFO: High-level analysis progress
# WARNING: Missing files, incomplete data
# ERROR: Fatal parsing errors
```

## Documentation

Keep updated:
- `README.md`: User-facing overview
- `ARCHITECTURE.md` (this file): Design decisions
- `CHANGELOG.md`: Version history
- `ROADMAP.md`: Future features
- Inline docstrings: Why (not what) the code exists
