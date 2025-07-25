# Development Standards for DOE Lab Research

Refer to README.md, *.md, *.mmd, Makefile, and .gitlab-ci.yml as necessary to help understand code and workflow.

## Code Generation Rules
- Always provide complete diffs - never use placeholder comments like "rest of code remains the same"
- Apply PhD-level technical depth with security-first analysis
- Consider attack vectors, defense strategies, and compliance requirements

## Development Environment
- **Python**: Latest version with full type hints (mypy --strict compliance)
- **Package Management**: micromamba (often inside Docker containers)
- **Build System**: Makefile orchestration
- **Code Formatting**: `make black` for Python formatting
- **Security Checks**: `make security` (bandit/pip-audit)
- **Type Checking**: `make type-check` (mypy)
- **Testing**: `make test-unit` and `make test-integration` (pytest)
- **Dependencies**: X.Y.* pinned versions only

## Python File Structure
**Every Python file must start with comprehensive docstring including:**
- Module name and brief description
- Detailed purpose explanation
- 3-4 feature sections with 3-5 bullet points each
- Use Cases section with 3-5 specific use cases

**Import Organization (with blank lines between groups):**
1. Standard library imports (alphabetical)
2. Standard library 'from' imports (alphabetical)  
3. Third-party package imports (alphabetical)
4. Third-party 'from' imports (alphabetical)
5. Local project imports (alphabetical)  
6. Local project 'from' imports (alphabetical)

## Code Standards
- **Type Safety**: Full type hints required, mypy --strict compliance
- **DRY Principle**: Eliminate code duplication wherever possible
- **Logging**: Use logging module instead of print statements (debug/info/warning/error/critical)
- **Validation**: Pydantic models for input validation
- **Error Handling**: Custom exceptions with specific exception handling
- **External APIs**: Use tenacity + ratelimit for robust handling, diskcache for client-side caching
- **Memory Efficiency**: Generators/iterators for large datasets, tqdm for progress tracking
- **Concurrency**: Consider parallel processing where appropriate using joblib
- **Tool Preferences**: httpx over requests, playwright over selenium, pytorch over tensorflow, polars over pandas
- **HPC**: PBS Pro for dispatching (https://2025.help.altair.com/2025.2.0/PBS%20Professional/PBSProgram2025.2.0.pdf), Dask for HPC Python code where sensible

## Project Structure
**For new projects:**
- Code in `src/` (single/no container) or `*/src/` (multi-container projects)
- Tests always in `tests/` at project root
- Organize src by functionality, for example: `core/`, `models/`, `services/`, `api/`, `utils/`
- Use snake_case naming, `__init__.py` files where required

**For existing projects:** Keep existing structure but apply standards within it

## Configuration Management
- `settings.py` in src/ for main configuration
- `settingslocal.py` for sensitive/local overrides (gitignored)
- Use `.env` files when appropriate for Docker containers
- No hardcoded values in source files

## Clean Code Principles
- **Naming**: Meaningful, pronounceable, searchable names. No abbreviations or mental mapping
- **Functions**: 20-30 lines max, single responsibility, ≤3 parameters, no flag arguments
- **Classes**: Single responsibility, small classes, few instance variables, composition over inheritance
- **Error Handling**: Use exceptions not error codes, meaningful messages with context
- **Comments**: Explain WHY not WHAT, avoid redundant comments, keep current with code changes
- **Structure**: No duplication, consistent formatting, avoid deep nesting (early returns), prefer immutable objects

## Git Workflow
**Conventional Commits:** `<type>[scope]: <description>`
- Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert
- Subject under 50 chars, imperative mood ('add' not 'added')  
- Separate subject from body with blank line, wrap body at 72 chars
- Explain WHY not implementation details
- Examples: `feat(auth): add OAuth2 integration`, `fix: resolve memory leak in parser`

**Branch Strategy:** Always push to feature branches, create merge/pull requests to main

## Container Standards
- Official tagged base images, non-root users, .dockerignore files
- One process per container principle
- Use Docker (single container) or Docker Compose (multiple containers)
- Singularity/Apptainer instead of Docker if intended for HPC use (https://apptainer.org/docs/user/latest/)

## Repository Rules
- **Source code ONLY** - no docs/binaries/data/results/logs in git
- All code must past `make lint` and (if available) `make type-check` and `make test`
- When testing code, use the same Container/Environment command prefixes found in the Makefile
- Use .gitignore to prevent accidental commits

## Security Requirements
- All code must pass `make security` analysis
- No sensitive data in source code (use environment variables)
- Security-first implementation approach
- Document security assumptions and limitations
- Follow principle of least privilege

## Automation & CI/CD
- GitLab CI workflow in `.gitlab-ci.yml`
