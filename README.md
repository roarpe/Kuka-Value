# Kuka-Value

Professional tool for analyzing KUKA robot backups and extracting valuable data for traceability and diagnostics.

## Overview

Kuka-Value is a desktop application built with Clean Architecture principles that analyzes KUKA robot backups (ZIP files or directories) to:

- **Detect robot configuration** (model, KSS version, controller type, serial number)
- **Parse LOAD_DATA** and extract payload information (mass, center of gravity, inertia)
- **Eliminate duplicate payloads** while preserving location information
- **Export analysis results** in multiple formats (CSV, Excel, JSON)

## Features

### Current Version (Planned)

- ✅ ZIP and folder backup support
- ✅ Automatic robot model detection
- ✅ LOAD_DATA parsing with generic KRL lexer/parser
- ✅ Payload duplicate detection and elimination
- ✅ Multiple export formats
- ✅ Professional logging and warnings
- ✅ 90%+ test coverage

### Future Roadmap

- TOOL_DATA and BASE_DATA parsing
- Program analysis and call tree visualization
- Backup comparison and diff tools
- Automatic diagnostics and recommendations
- PDF report generation
- Support for ABB, FANUC, COMAU robots

## Requirements

- Python 3.13+
- PySide6 6.6.0+
- See `pyproject.toml` for complete dependencies

## Installation

### From source

```bash
# Clone repository
git clone https://github.com/roarpe/Kuka-Value.git
cd Kuka-Value

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Verify installation
pytest --cov
```

## Usage

### Command Line

```bash
kuka-value
```

### From Python

```python
from kuka_value.engine import Engine

engine = Engine()
robot = engine.parse("/path/to/backup.zip")

print(f"Robot Model: {robot.model}")
print(f"KSS Version: {robot.kss_version}")
print(f"Unique Payloads: {len(robot.payloads)}")
```

## Architecture

The project follows **Clean Architecture** with strict separation of concerns:

```
src/kuka_value/
├── engine/          # Core orchestration layer
├── parser/          # KRL lexing, tokenizing, parsing
├── analyzers/       # Robot and payload analysis
├── exporters/       # CSV, Excel, JSON export
├── models/          # Domain models (dataclasses)
└── ui/              # PySide6 user interface
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design documentation.

## Development

### Testing

```bash
# Run all tests with coverage
pytest

# Run only unit tests
pytest -m unit

# Run specific test
pytest tests/unit/test_backup_reader.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/ --fix

# Type checking
mypy src/
```

### Git Workflow

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make changes with small, focused commits
3. Use Conventional Commits: `feat(parser): implement...`
4. Ensure tests pass and coverage ≥ 90%
5. Push and create pull request

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

MIT - See LICENSE file for details

## Contributing

This is a professional engineering project. Code must follow:

- Type hints on all public functions
- Minimum 90% test coverage
- Clean Architecture principles
- SOLID design principles
- Conventional Commits format

## Contact

- Author: roarpe
- Email: roarpre@gmail.com
- Repository: https://github.com/roarpe/Kuka-Value
