"""Regression tests for Python executor sandbox and subprocess behavior."""

import json
import time
from importlib import metadata as importlib_metadata
from pathlib import Path

import pytest

from tooluniverse.python_executor_tool import PythonCodeExecutor, PythonScriptRunner

pytestmark = pytest.mark.unit


def _code_executor():
    return PythonCodeExecutor({"name": "python_code_executor"})


def _script_runner():
    return PythonScriptRunner({"name": "python_script_runner"})


def test_allowed_imports_is_not_exposed_in_tool_schema():
    """The MCP schema must not advertise caller-controlled import permissions."""
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "python_executor_tools.json"
    )
    config = json.loads(config_path.read_text())

    assert "allowed_imports" not in config[0]["parameter"]["properties"]


def test_caller_allowed_imports_is_rejected_explicitly():
    """Legacy calls that bypass schema validation must receive a clear error."""
    result = _code_executor().run(
        {
            "code": "import time\nresult = time.time()",
            "allowed_imports": ["time"],
        }
    )

    assert result["status"] == "error"
    assert result["data"]["error_type"] == "SecurityError"
    assert "cannot be set per call" in result["data"]["error"]


def test_allowed_package_submodules_are_importable():
    """Allowlisting a package must also allow its internal submodules."""
    executor = _code_executor()
    safe_import = executor._create_safe_globals()["__builtins__"]["__import__"]

    imported = safe_import("numpy._core._methods")

    assert imported.__name__ == "numpy"


def test_module_prefix_must_end_at_package_boundary():
    """A package-name prefix without a dot must not bypass the allowlist."""
    executor = _code_executor()
    safe_import = executor._create_safe_globals()["__builtins__"]["__import__"]

    with pytest.raises(ImportError, match="is not allowed"):
        safe_import("numpymalicious")


def test_dangerous_allowed_package_submodule_remains_blocked():
    """Package-prefix matching must not expose an FFI sandbox escape."""
    executor = _code_executor()
    safe_import = executor._create_safe_globals()["__builtins__"]["__import__"]

    with pytest.raises(ImportError, match="is not allowed"):
        safe_import("numpy.ctypeslib")


def test_script_runner_completes_and_captures_output(tmp_path):
    """A trivial script must exit promptly and return its stdout."""
    script = tmp_path / "trivial.py"
    script.write_text('print("hello")\n')

    started = time.monotonic()
    result = _script_runner().run(
        {
            "script_path": str(script),
            "working_directory": str(tmp_path),
            "timeout": 5,
        }
    )

    assert time.monotonic() - started < 5
    assert result["status"] == "success"
    assert result["data"]["stdout"] == "hello\n"


def test_script_runner_returns_partial_output_on_timeout(tmp_path):
    """Output flushed before a timeout must be returned to the caller."""
    script = tmp_path / "timeout.py"
    script.write_text(
        "import sys\n"
        "import time\n"
        'print("stdout-before-timeout", flush=True)\n'
        'print("stderr-before-timeout", file=sys.stderr, flush=True)\n'
        "time.sleep(10)\n"
    )

    result = _script_runner().run(
        {
            "script_path": str(script),
            "working_directory": str(tmp_path),
            "timeout": 0.2,
        }
    )

    assert result["status"] == "error"
    assert result["data"]["error_type"] == "TimeoutError"
    assert result["data"]["stdout"] == "stdout-before-timeout\n"
    assert result["data"]["stderr"] == "stderr-before-timeout\n"


def test_dependency_check_distinguishes_cpu_and_gpu_distributions(monkeypatch):
    """The CPU distribution must not satisfy an onnxruntime-gpu dependency."""

    def fake_version(distribution_name):
        if distribution_name == "onnxruntime":
            return "1.28.0"
        raise importlib_metadata.PackageNotFoundError(distribution_name)

    monkeypatch.setattr(importlib_metadata, "version", fake_version)

    result = _code_executor()._check_and_install_dependencies(
        ["onnxruntime-gpu"], auto_install=False, require_confirmation=True
    )

    assert result["success"] is False
    assert result["missing_packages"] == ["onnxruntime-gpu"]
    assert result["packages_to_install"] == ["onnxruntime-gpu"]


def test_dependency_check_accepts_exact_distribution(monkeypatch):
    """An exact installed distribution name must satisfy the dependency check."""

    def fake_version(distribution_name):
        if distribution_name == "onnxruntime":
            return "1.28.0"
        raise importlib_metadata.PackageNotFoundError(distribution_name)

    monkeypatch.setattr(importlib_metadata, "version", fake_version)

    result = _code_executor()._check_and_install_dependencies(["onnxruntime"])

    assert result["success"] is True
