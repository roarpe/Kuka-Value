# Roadmap

## Version 1.0 (Current Development)

### Core Features

- [x] Project scaffolding and configuration
- [ ] BackupReader (ZIP and folder support)
- [ ] Generic KRL Parser (Lexer → Tokenizer → Parser)
- [ ] RobotAnalyzer (model detection, normalization)
- [ ] PayloadAnalyzer (extraction, deduplication)
- [ ] CSV/Excel/JSON exporters
- [ ] PySide6 UI (basic workflow)
- [ ] Professional logging and warnings
- [ ] 90%+ test coverage

### Estimated Completion

Q3 2026

## Version 1.1 (Q4 2026)

### Data Integrity

- Extended LOAD_DATA validation
- Payload consistency checks
- Inertia value verification
- Historical tracking of payload changes

### User Experience

- Backup comparison (what changed between versions)
- Search and filter capabilities
- Payload history and trends
- Visual payload reports

### Export Enhancements

- PDF report generation
- Template-based custom exports
- Batch processing multiple backups
- Report scheduling

## Version 1.2 (Q1 2027)

### Program Analysis

- Program parsing and indexing
- Call tree visualization
- Program dependency graph
- Search programs by name/number
- Identify unused programs

### Advanced Diagnostics

- Automatic issue detection
- Configuration warnings
- Performance recommendations
- Compatibility matrix (programs ↔ payloads)

## Version 2.0 (Q3 2027)

### Multi-Robot Support

- TOOL_DATA parsing and analysis
- BASE_DATA parsing
- Kinematics configuration verification
- Tool payload verification

### Backup Tools

- Backup diff and merge
- Configuration migration tools
- Incremental backup analysis
- Backup compression ratio analysis

### Web Interface

- Remote backup analysis
- Cloud storage integration
- Team collaboration features
- Audit logging

## Version 2.1+ (Q4 2027+)

### Multi-Manufacturer Support

- ABB robot support
  - RAPID program language
  - ABB backup formats
  - ABB-specific analyzers

- FANUC robot support
  - KAREL language
  - FANUC backup formats
  - FANUC diagnostics

- COMAU robot support
  - C4G/C5G support
  - COMAU backup parsing

### Industrial Features

- Integration with MES systems
- Real-time robot monitoring
- Predictive maintenance
- Failure analysis tools
- Robot lifecycle management

### Enterprise Features

- Multi-site management
- Fleet analytics
- Compliance reporting
- Disaster recovery planning

## Architectural Milestones

### 1.0 Release
- Clean Architecture fully implemented
- Single-threaded engine sufficient
- No database backend

### 1.1 Release
- Async operations for UI responsiveness
- In-memory caching layer
- Incremental parsing

### 1.2 Release
- Plugin system for analyzers
- Custom exporter framework
- Configuration file support

### 2.0 Release
- Database backend for historical data
- Multi-process worker pool
- Distributed analysis (multiple machines)

### 2.1+ Releases
- Microservices architecture
- Kubernetes deployment
- Real-time streaming analysis

## Known Limitations (Versions 1.0-1.1)

1. **Single-file limitation**: Only analyzes one backup at a time
2. **No persistence**: Analysis results not saved between sessions
3. **Limited export**: Basic formats only (CSV, Excel, JSON)
4. **No networking**: Local files only (no remote backups)
5. **Single-threaded**: UI blocks during analysis (< 2 sec so acceptable)

These will be addressed in later versions as needed.

## Breaking Changes Policy

- v1.x: API stability not guaranteed (pre-release)
- v2.0+: Semantic versioning (MAJOR.MINOR.PATCH)
  - MAJOR: Breaking changes to public Engine API
  - MINOR: New features, backward compatible
  - PATCH: Bug fixes only

## Community Feedback

Issues and feature requests tracked at:
https://github.com/roarpe/Kuka-Value/issues

Priority based on:
1. Impact on engineering workflow
2. Community demand
3. Architectural fit (no hacks)
4. Testing feasibility
