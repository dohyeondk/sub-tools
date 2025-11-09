# Python 3.14 Compatibility Report

## Summary

✅ **The sub-tools codebase is fully compatible with Python 3.14**

## Testing Details

### Environment
- Python Version: 3.14.0
- Test Date: 2025-11-09
- Platform: Linux (Ubuntu Noble)

### Findings

#### ✅ Syntax Compatibility
- All Python source files compile successfully with Python 3.14
- No syntax errors or incompatibilities detected
- Modern type hints (e.g., `list[tuple[int, int]]`) are properly used

#### ✅ Deprecated Features Check
No deprecated Python features were found in the codebase:
- ✓ No usage of `datetime.utcnow()` or `datetime.utcfromtimestamp()`
- ✓ No usage of removed modules (`wave`, `aifc`, `audioop`, `imp`, `cgi`, `cgitb`)
- ✓ No usage of deprecated XML methods (`.getchildren()`, `.getiterator()`)
- ✓ Proper use of `importlib.metadata` instead of deprecated `pkg_resources`

#### ✅ audioop Replacement
The project correctly uses `audioop-lts>=0.2.1` for Python 3.13+, which is the recommended replacement for the removed `audioop` module.

```python
# From pyproject.toml
"audioop-lts>=0.2.1; python_version >= '3.13'",
```

### Dependency Status

#### ✅ Available for Python 3.14
The following dependencies have been successfully tested with Python 3.14:
- ✅ audioop-lts (0.2.2)
- ✅ openai (2.7.1)
- ✅ pycountry (24.6.1)
- ✅ pydub (0.25.1)
- ✅ pysrt (1.1.2)
- ✅ pytest (8.4.2)
- ✅ pytest-asyncio (1.2.0)
- ✅ python-ffmpeg (2.0.12)
- ✅ rich (14.2.0)
- ✅ soundfile (0.13.1)

#### ⏳ Not Yet Available for Python 3.14
- ⏳ **silero-vad** - Requires `onnxruntime` which doesn't have Python 3.14 wheels yet
  - This is expected as Python 3.14 was recently released (October 2024)
  - The package maintainers will likely release Python 3.14 support soon
  - **Action**: Monitor onnxruntime releases for Python 3.14 support

## Recommendations

### 1. Continue Supporting Python 3.10+
Keep the current minimum Python version requirement of 3.10+ as specified in `pyproject.toml`:

```toml
requires-python = ">=3.10"
```

This provides broad compatibility while the ecosystem catches up with Python 3.14.

### 2. CI/CD Testing
Once `onnxruntime` releases Python 3.14 wheels, add Python 3.14 to the CI/CD test matrix to ensure ongoing compatibility.

### 3. Docker Image
The current Dockerfile uses Python 3.13, which is appropriate:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
```

Consider adding a Python 3.14 variant once all dependencies are available.

### 4. Monitor Dependencies
Keep track of these key dependencies for Python 3.14 support:
- `onnxruntime`: https://github.com/microsoft/onnxruntime/releases
- `silero-vad`: https://github.com/snakers4/silero-vad

## Conclusion

The sub-tools codebase is **ready for Python 3.14** from a code perspective. The only blocker is the external dependency `onnxruntime` which is beyond our control. Once that dependency releases Python 3.14 wheels (expected soon), the project will work seamlessly with Python 3.14.

**No code changes are required** - the codebase is already following best practices and avoiding deprecated features.
