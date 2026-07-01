# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated testing, documentation deployment, and package publishing.

## Overview

The workflow system has been optimized to eliminate redundancy while maintaining comprehensive test coverage. The main test suite now includes dependency isolation testing, eliminating the need for separate specialized workflows.

## Workflows

### 1. Complete Test Suite (`tests.yml`)
**Triggers:** Push to main, Pull requests to main
**Purpose:** Runs the complete test suite including dependency isolation tests

**Key Features:**
- Tests on Python 3.12, matching `.github/workflows/tests.yml`
- Includes dependency isolation tests (37 tests)
- CLI doctor tool testing
- System stability verification
- Generates coverage reports
- Uploads test artifacts

### 2. Documentation Build (`docs.yml`)
**Triggers:** Manual dispatch
**Purpose:** Build documentation locally for testing

**Key Features:**
- Sphinx documentation build
- Warnings as errors
- Artifact upload for review

### 3. Documentation Deployment (`deploy-docs.yml`)
**Triggers:** Push to main (when docs/src/pyproject.toml change)
**Purpose:** Deploy documentation to GitHub Pages

**Key Features:**
- Multi-language support (English/Chinese)
- Optimized build with caching
- GitHub Pages deployment
- Deployment status reporting

### 4. PyPI Publishing (`publish-pypi.yml`)
**Triggers:** Push to main (when version changes)
**Purpose:** Publish package to PyPI

**Key Features:**
- Version change detection
- Package building and validation
- PyPI publishing with trusted publishing
- GitHub release creation

## What Gets Tested

### Core Functionality
- ✅ Error tracking and recording
- ✅ Missing package detection
- ✅ Tool health monitoring
- ✅ CLI doctor tool functionality
- ✅ Integration with real tool loading
- ✅ Concurrent access safety
- ✅ Error recovery mechanisms

### System Protection
- 🛡️ **System Stability**: Tools with missing dependencies won't crash the system
- 📊 **Health Monitoring**: `get_tool_health()` API works correctly
- 🔧 **CLI Diagnostics**: `tooluniverse-doctor` provides helpful output
- 🔄 **Error Recovery**: System can recover from dependency issues
- ⚡ **Performance**: No significant overhead for working tools

## File Triggers

The workflows are triggered when these files are modified:
- `src/tooluniverse/tool_registry.py`
- `src/tooluniverse/execute_function.py`
- `src/tooluniverse/doctor.py`
- `tests/unit/test_dependency_isolation.py`
- `tests/integration/test_dependency_isolation_integration.py`
- `tests/unit/test_error_handling_recovery.py`

## Test Results

### Success Indicators
- All 37 dependency isolation tests pass
- Doctor CLI tool runs successfully
- System remains stable with simulated failures
- Error tracking works correctly
- Health monitoring provides accurate status

### Failure Indicators
- Any test fails
- System crashes with missing dependencies
- Error tracking doesn't work
- Health monitoring returns incorrect data
- CLI tool doesn't function properly

## Local Testing

To run the same tests locally:

```bash
# Create/sync the standard ToolUniverse development environment
uv python install 3.12
uv venv --python 3.12
uv sync

# Run all dependency isolation tests
uv run pytest tests/unit/test_dependency_isolation.py \
              tests/integration/test_dependency_isolation_integration.py \
              tests/unit/test_error_handling_recovery.py \
              -v

# Test doctor CLI
uv run python -m src.tooluniverse.doctor

# Test error tracking
uv run python -c "
from src.tooluniverse.tool_registry import mark_tool_unavailable, get_tool_errors
mark_tool_unavailable('TestTool', ImportError('No module named \"test\"'))
print('Errors:', get_tool_errors())
"
```

Use the project-supported Python version for local test runs. CPython 3.14 is not
currently recommended for the full dependency set because pinned packages such as
`torch==2.8.0` may not publish CPython 3.14 wheels. Do not create feature-specific
lightweight environments for subsets of tests unless the project dependency model
adds such a pattern.

## Benefits

1. **Automatic Verification**: Every PR automatically tests dependency isolation
2. **Multi-Version Testing**: Tests across multiple Python versions
3. **Comprehensive Coverage**: Unit, integration, and smoke tests
4. **Clear Feedback**: Automatic PR comments with test results
5. **Fast Feedback**: Quick checks for PR authors
6. **System Protection**: Ensures the system remains stable

The dependency isolation system protects ToolUniverse from tool dependency failures, ensuring that one problematic tool doesn't crash the entire system! 🛡️
