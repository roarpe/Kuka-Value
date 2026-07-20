# Changelog

All notable changes to Kuka-Value will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-20

### Added

- Initial project scaffolding
- Professional Python project structure (src layout)
- Comprehensive pyproject.toml configuration
  - Python 3.13+ requirement
  - PySide6 dependency
  - Development tools: pytest, black, ruff, mypy
  - Test coverage configuration (90% minimum)
  - Type checking with mypy in strict mode
- .gitignore with Python and IDE exclusions
- Architecture documentation (ARCHITECTURE.md)
- Project roadmap (ROADMAP.md)
- Development guidelines in README.md
- pytest configuration with coverage reporting
- Clean Architecture module structure:
  - `engine/`: Core orchestration
  - `parser/`: KRL parsing (Lexer → Tokenizer → Parser)
  - `analyzers/`: Robot and payload analysis
  - `exporters/`: CSV, Excel, JSON export
  - `models/`: Domain model definitions
  - `ui/`: PySide6 user interface

### Standards Established

- Type hints on all public functions (mypy --strict)
- Dataclasses for all domain models
- Logging framework integration
- 90%+ test coverage requirement
- Conventional Commits format
- Single Responsibility Principle
- Dependency Inversion Principle
- No exceptions for incomplete data (warnings instead)

---

[Unreleased]: https://github.com/roarpe/Kuka-Value/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/roarpe/Kuka-Value/releases/tag/v0.1.0
