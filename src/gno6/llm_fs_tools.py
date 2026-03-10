"""
Filesystem tools for LLM agents.

Usage:
    from llm_fs_tools import (
        FilesystemToolbox,
        ToolError,
    )

    tools = FilesystemToolbox(workspace_root=Path("/path/to/workspace"))

    tools.list_files(path=".", recursive=False, show_line_count=True)
    tools.read_file("src/main.py", start_line=1, end_line=40)
    tools.edit_file("src/main.py", 10, 12, "replacement text\nlines")
    tools.exec_script("scripts/run.sh", args=["--flag"], background=True)
"""

from __future__ import annotations
import subprocess
import threading
import shlex
import difflib
import re
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import questionary
from .utils import *
from . import config

class ToolError(Exception):
    """Exception raised for tool-specific errors (invalid input, OOB, permission, etc.)."""


class FilesystemToolbox:
    def __init__(self, workspace_root: Path):
        """
        workspace_root: Path - the root directory within which all operations are allowed.
        """
        self.workspace_root = Path(workspace_root).resolve()
        if not self.workspace_root.exists():
            raise ToolError(f"Workspace root does not exist: {self.workspace_root!s}")
        # Directory to store background process logs
        self._bg_log_dir = self.workspace_root / ".llm_runs"
        self._bg_log_dir.mkdir(exist_ok=True)

    # -----------------------
    # Helpers
    # -----------------------
    def _resolve_safe(self, path: str | Path) -> Path:
        p = Path(path)
        # if relative, resolve relative to workspace root
        if not p.is_absolute():
            p = (self.workspace_root / p)
        resolved = p.resolve()
        try:
            if not resolved.is_relative_to(self.workspace_root):
                raise ToolError(f"Path outside workspace: {path}")
        except AttributeError:
            # Python <3.9 fallback
            if str(self.workspace_root) != str(resolved) and not str(resolved).startswith(str(self.workspace_root) + os.sep):
                raise ToolError(f"Path outside workspace: {path}")
        return resolved

    @staticmethod
    def _read_all_lines(path: Path) -> List[str]:
        # Read as text with universal newlines, return list of lines without trailing newline character
        text = path.read_text(encoding="utf-8", errors="replace")
        # splitlines() drops trailing newline characters; easier indexing for lines
        return text.splitlines()

    # -----------------------
    # list_files
    # -----------------------
    def list_files(self, path: str = ".", recursive: bool = False, show_line_count: bool = False) -> Dict[str, Any]:
        """
        List files under `path`. Returns structured dict.
        :param path: directory path relative to workspace_root
        :param recursive: whether to recurse
        :param show_line_count: if True, include the number of lines in each file (text files; binary skipped)
        """
        if config.g_print_tool_output:
          print("> Listing files")
        root = self._resolve_safe(path)
        if not root.exists():
            raise ToolError(f"Path does not exist: {path}")
        if not root.is_dir():
            raise ToolError(f"Path is not a directory: {path}")

        entries: List[Dict[str, Any]] = []

        if recursive:
            walker = root.rglob("*")
        else:
            walker = root.iterdir()

        for p in walker:
            rel = p.relative_to(self.workspace_root)
            entry: Dict[str, Any] = {
                "path": str(rel),
                "is_dir": p.is_dir(),
            }
            if p.is_file() and show_line_count:
                try:
                    lines = self._read_all_lines(p)
                    entry["line_count"] = len(lines)
                except Exception:
                    entry["line_count"] = None
            entries.append(entry)

        return {"root": str(root.relative_to(self.workspace_root)), "entries": entries}

    # -----------------------
    # read_file
    # -----------------------
    def read_file(self, path: str, start_line: int|None = None, end_line: int|None = None) -> Dict[str, Any]:
        """
        Read file lines using 1-based inclusive indexing.
        If both start_line and end_line are None -> return full file.
        Raises ToolError if OOB.
        """
        file_path = self._resolve_safe(path)
        if not file_path.exists() or not file_path.is_file():
            raise ToolError(f"File not found: {path}")

        if config.g_print_tool_output:
          print(f"> Reading file `{str(file_path)}`")

        lines = self._read_all_lines(file_path)
        total = len(lines)

        if start_line is None:
            start_line = 1
        if end_line is None:
            end_line = total

        if start_line < 1 or end_line < start_line:
            raise ToolError(f"Invalid line window: start={start_line}, end={end_line}")

        if end_line > total:
            raise ToolError(f"Requested end_line {end_line} > file length {total}")

        # convert to 0-based slice
        slice_lines = lines[start_line - 1 : end_line]
        # prepare numbered snippet string
        numbered = "\n".join(f"{i:>6} | {l}" for i, l in enumerate(slice_lines, start=start_line))
        return {
            "file": str(file_path.relative_to(self.workspace_root)),
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total,
            "content_lines": slice_lines,
            "numbered": numbered,
        }

    # -----------------------
    # write_file
    # -----------------------
    def write_file(self, path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Create or overwrite a file.
        :param path: path relative to workspace_root
        :param content: full file content (string)
        :param overwrite: allow overwrite if file exists
        """
        file_path = self._resolve_safe(path)
        parent = file_path.parent
        parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists() and not overwrite:
            raise ToolError(f"File exists and overwrite is False: {path}")


        # Ensure text ends with newline
        data = content
        # Decide newline behaviour: keep as-is; ensure final newline for consistency
        if not data.endswith("\n"):
            data = data + "\n"
        confirm_exec(f"Write to file `{str(file_path)}` ?")
        file_path.write_text(data, encoding="utf-8")
        lines = data.splitlines()
        return {
            "file": str(file_path.relative_to(self.workspace_root)),
            "action": "wrote" if not file_path.exists() else "overwrote",
            "line_count": len(lines),
        }

    # -----------------------
    # edit_file
    # -----------------------
    def edit_file(self, path: str, start_line: int, end_line: int, replacement: str) -> Dict[str, Any]:
        """
        Replace lines [start_line, end_line] (1-based inclusive) with replacement text.
        Returns metadata and a colorized diff (if modified snippet < 100 lines).
        Raises ToolError for OOB or missing file.
        """
        file_path = self._resolve_safe(path)
        if not file_path.exists() or not file_path.is_file():
            raise ToolError(f"File not found: {path}")

        old_lines = self._read_all_lines(file_path)
        total = len(old_lines)

        if start_line < 1 or end_line < start_line:
            raise ToolError(f"Invalid window: start={start_line}, end={end_line}")
        if end_line > total:
            raise ToolError(f"Requested end_line {end_line} > file length {total}")

        # Replacement lines
        new_fragment = replacement.splitlines()
        # Build new lines list
        new_lines = old_lines[: start_line - 1] + new_fragment + old_lines[end_line :]

        # Write back: preserve trailing newline presence from original if present
        # Detect if original file ended with newline
        original_text = file_path.read_text(encoding="utf-8", errors="replace")
        ended_with_nl = original_text.endswith("\n")

        out_text = "\n".join(new_lines)
        if ended_with_nl:
            out_text = out_text + "\n"
        else:
            # keep as no trailing newline if original had none
            pass

        confirm_exec(f"Edit file inplace `{str(file_path)}` ?")

        file_path.write_text(out_text, encoding="utf-8")

        # Prepare diff but only for the modified region context: show a reasonable window
        # We'll show a unified diff for old vs new but if diff is > 100 lines we omit content.
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"{file_path.name} (before)",
                tofile=f"{file_path.name} (after)",
                lineterm="",
            )
        )

        show_diff = True
        if len(diff_lines) > 100:
            show_diff = False

        colored_diff = None
        if show_diff and diff_lines:
            colored = []
            for ln in diff_lines:
                if ln.startswith("---") or ln.startswith("+++"):
                    colored.append(f"{ANSI_BOLD}{ln}{ANSI_RESET}")
                elif ln.startswith("@@"):
                    colored.append(f"{ANSI_CYAN}{ln}{ANSI_RESET}")
                elif ln.startswith("+"):
                    colored.append(f"{ANSI_GREEN}{ln}{ANSI_RESET}")
                elif ln.startswith("-"):
                    colored.append(f"{ANSI_RED}{ln}{ANSI_RESET}")
                else:
                    colored.append(ln)
            colored_diff = "\n".join(colored)
            if colored_diff is not None:
              print(colored_diff)

        return {
            "file": str(file_path.relative_to(self.workspace_root)),
            "modified_region": {"start_line": start_line, "end_line": end_line, "replacement_lines": len(new_fragment)},
            "new_total_lines": len(new_lines),
            "diff_available": show_diff and bool(diff_lines),
            "colored_diff": colored_diff if colored_diff is not None else (None if show_diff else f"Diff too large to display ({len(diff_lines)} lines)"),
        }

    # -----------------------
    # search_in_files
    # -----------------------
    def search_in_files(self, pattern: str, path: str = ".", max_results: int = 200, use_regex: bool = True) -> Dict[str, Any]:
        """
        Search for `pattern` inside files under path. Returns list of matches:
          { "file": "path", "line_no": n, "line": "...", "match": "..." }

        :param pattern: string or regex
        :param path: directory/file path relative to workspace_root
        :param max_results: stop after this many matches
        :param use_regex: if True compile pattern as regex (re.I by default if pattern looks case-insensitive)
        """
        if config.g_print_tool_output:
          print(f"> Searching through files")

        root = self._resolve_safe(path)
        if not root.exists():
            raise ToolError(f"Path does not exist: {path}")

        matches: List[Dict[str, Any]] = []
        compiled = None
        if use_regex:
            try:
                compiled = re.compile(pattern)
            except re.error as e:
                raise ToolError(f"Invalid regex pattern: {e}")

        # Walk files (non-recursive if root is file)
        if root.is_file():
            files = [root]
        else:
            files = [f for f in root.rglob("*") if f.is_file()]

        for f in files:
            # Read safely (binary files will be skipped if decode fails heavily)
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                # try with replace fallback
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
            for i, line in enumerate(text.splitlines(), start=1):
                if compiled:
                    if compiled.search(line):
                        matches.append({"file": str(f.relative_to(self.workspace_root)), "line_no": i, "line": line})
                else:
                    if pattern in line:
                        matches.append({"file": str(f.relative_to(self.workspace_root)), "line_no": i, "line": line})
                if len(matches) >= max_results:
                    return {"pattern": pattern, "matches": matches, "truncated": True}
        return {"pattern": pattern, "matches": matches, "truncated": False}

    # -----------------------
    # exec_script
    # -----------------------
    def exec_script(
        self, path: str, args: list[str]|None = None, background: bool = False, timeout: int|None = None, shell: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a script at path. If background=True, start process and return PID and log paths; does not wait.
        If background=False, run synchronously and return exit code, stdout and stderr.

        Security:
          - The script path must be inside workspace_root.
          - 'shell' lets you run via shell; default False (recommended).
        """
        args = args or []
        script_path = self._resolve_safe(path)
        if not script_path.exists() or not script_path.is_file():
            raise ToolError(f"Script not found: {path}")

        # Ensure executable bit (not strictly necessary on Windows but good check)
        if os.name != "nt":
            mode = script_path.stat().st_mode
            if not (mode & 0o111):
                # Try to set exec bit for user
                try:
                    script_path.chmod(mode | 0o100)
                except Exception:
                    # Not fatal; continue but warn in result
                    pass

        confirm_exec(f"Exec file `{str(script_path)}` ?")
        cmd = [str(script_path)] + list(args)
        if background:
            # prepare log files
            pid_file = self._bg_log_dir / f"pid_{script_path.name}_{os.getpid()}_{threading.get_ident()}.txt"
            stdout_log = self._bg_log_dir / f"{script_path.name}_{os.getpid()}_{threading.get_ident()}.out"
            stderr_log = self._bg_log_dir / f"{script_path.name}_{os.getpid()}_{threading.get_ident()}.err"

            # Start process detached
            with open(stdout_log, "ab") as so, open(stderr_log, "ab") as se:
                # Use Popen; do not set close_fds=False on Windows
                proc = subprocess.Popen(cmd, stdout=so, stderr=se, cwd=str(self.workspace_root), shell=shell)
            # store pid
            pid_file.write_text(str(proc.pid), encoding="utf-8")
            return {
                "status": "started",
                "pid": proc.pid,
                "stdout_log": str(stdout_log.relative_to(self.workspace_root)),
                "stderr_log": str(stderr_log.relative_to(self.workspace_root)),
                "pid_file": str(pid_file.relative_to(self.workspace_root)),
            }
        else:
            try:
                # run and capture output
                # If shell=True you should pass a single string; we support both modes
                if shell:
                    cmd_text = " ".join(shlex.quote(p) for p in cmd)
                    completed = subprocess.run(cmd_text, shell=True, cwd=str(self.workspace_root), capture_output=True, text=True, timeout=timeout)
                else:
                    completed = subprocess.run(cmd, shell=False, cwd=str(self.workspace_root), capture_output=True, text=True, timeout=timeout)
                return {
                    "status": "finished",
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            except subprocess.TimeoutExpired as te:
                return {"status": "timeout", "timeout_seconds": timeout, "stdout": te.stdout or "", "stderr": te.stderr or ""}
            except Exception as e:
                raise ToolError(f"Failed to execute script: {e}")

# -----------------------
# Example instantiation (for developer usage)
# -----------------------
#if __name__ == "__main__":
#    # quick smoke test (adjust workspace_root to something valid)
#    toolbox = FilesystemToolbox(workspace_root=Path(".").resolve())
#    print("Listing current dir (no line counts):")
#    print(toolbox.list_files(".", recursive=False, show_line_count=False))
