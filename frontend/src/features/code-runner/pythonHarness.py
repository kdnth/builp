import io
import json
import sys
import traceback

import _runner_io

_MAX_BUFFER = 10_000
_solution = None


class _Stream(io.TextIOBase):
    def __init__(self, name):
        self._name = name
        self._buffer = ""

    def writable(self):
        return True

    def write(self, text):
        self._buffer += text
        *lines, self._buffer = self._buffer.split("\n")
        for line in lines:
            _runner_io.write(self._name, line)
        if len(self._buffer) > _MAX_BUFFER:
            self.flush()
        return len(text)

    def flush(self):
        if self._buffer:
            _runner_io.write(self._name, self._buffer)
            self._buffer = ""


sys.stdout = _Stream("stdout")
sys.stderr = _Stream("stderr")


def _flush():
    sys.stdout.flush()
    sys.stderr.flush()


def _describe(exc):
    frames = [
        frame
        for frame in traceback.extract_tb(exc.__traceback__)
        if frame.filename == "<solution>"
    ]
    line = frames[-1].lineno if frames else None
    return f"{type(exc).__name__}: {exc}", line


def load_solution(code, function_name):
    global _solution
    _solution = None
    namespace = {"__name__": "__main__"}
    try:
        exec(compile(code, "<solution>", "exec"), namespace)
    except SyntaxError as exc:
        return json.dumps(
            {"message": f"{type(exc).__name__}: {exc.msg}", "line": exc.lineno}
        )
    except BaseException as exc:
        message, line = _describe(exc)
        return json.dumps({"message": message, "line": line})
    finally:
        _flush()

    candidate = namespace.get(function_name)
    if not callable(candidate):
        return json.dumps({"message": f"Define a function named `{function_name}`"})
    _solution = candidate
    return None


def run_test(input_json):
    try:
        result = _solution(*json.loads(input_json))
    except BaseException as exc:
        message, line = _describe(exc)
        return json.dumps({"error": message, "line": line})
    finally:
        _flush()

    try:
        output = json.dumps(result, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        return json.dumps({"error": "Return value is not JSON serializable"})
    return json.dumps({"outputJson": output})
