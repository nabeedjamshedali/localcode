"""
Tool definitions and implementations for the coding agent.
All tools that the LLM can call to interact with the filesystem and terminal.
"""
import os
import subprocess
import glob
import fnmatch
import re
import shutil
from pathlib import Path
from typing import Any

# ── TOOL SCHEMAS (sent to the model) ─────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a file. Use this to inspect any file before editing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to work dir or absolute)"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional: start reading from this line number (1-indexed)"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional: stop reading at this line number (inclusive)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file with the given content. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content to write"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing a specific string with another. More surgical than write_file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit"
                    },
                    "old_str": {
                        "type": "string",
                        "description": "The exact string to find and replace (must be unique in the file)"
                    },
                    "new_str": {
                        "type": "string",
                        "description": "The replacement string"
                    }
                },
                "required": ["path", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file with content. Fails if file already exists (use write_file to overwrite).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to create"},
                    "content": {"type": "string", "description": "File content"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file or empty directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to delete"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories. Use this to understand project structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (default: current working dir)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "If true, show full recursive tree. Default: false (1 level)"
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Show hidden files/dirs (default: false)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a pattern (regex or string) across all files in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "String or regex pattern to search for"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File glob pattern to limit search (e.g. '*.py', '*.ts'). Default: all files"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search (default: false)"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the project directory. Use for: tests, builds, git, npm, pip, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 60)"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Override working directory for this command"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files matching a pattern in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match (e.g. '**/*.py', 'src/**/*.ts')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Root directory to search in (default: work dir)"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch content from a URL (documentation, APIs, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch"
                    }
                },
                "required": ["url"]
            }
        }
    },
]

# ── TOOL IMPLEMENTATIONS ──────────────────────────────────────────────────────

IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
               'env', '.env', 'dist', 'build', '.next', '.nuxt', 'target',
               '.idea', '.vscode', 'coverage', '.pytest_cache', '.mypy_cache'}

MAX_FILE_SIZE = 200_000  # 200KB max to avoid flooding context


def _resolve_path(path: str, work_dir: str) -> str:
    """Resolve a path relative to work_dir."""
    if os.path.isabs(path):
        return path
    return os.path.join(work_dir, path)


def tool_read_file(args: dict, work_dir: str) -> str:
    path = _resolve_path(args['path'], work_dir)
    start = args.get('start_line')
    end = args.get('end_line')

    if not os.path.exists(path):
        return f"Error: File not found: {path}"
    if not os.path.isfile(path):
        return f"Error: Not a file: {path}"

    size = os.path.getsize(path)
    if size > MAX_FILE_SIZE and not start:
        return (f"File is {size/1024:.0f}KB (too large). "
                f"Use start_line/end_line to read sections, or search_code to find specific parts.")

    try:
        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()

        if start or end:
            s = (start or 1) - 1
            e = end or len(lines)
            lines = lines[s:e]
            content = ''.join(lines)
            return f"[Lines {start or 1}–{end or len(lines)} of {path}]\n\n{content}"

        content = ''.join(lines)
        return f"[{path}] ({len(lines)} lines)\n\n{content}"
    except Exception as e:
        return f"Error reading file: {e}"


def tool_write_file(args: dict, work_dir: str) -> str:
    path = _resolve_path(args['path'], work_dir)
    content = args['content']

    try:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        lines = content.count('\n') + 1
        return f"✓ Written {lines} lines to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def tool_edit_file(args: dict, work_dir: str) -> str:
    path = _resolve_path(args['path'], work_dir)
    old_str = args['old_str']
    new_str = args['new_str']

    if not os.path.exists(path):
        return f"Error: File not found: {path}"

    try:
        with open(path, 'r', errors='replace') as f:
            content = f.read()

        count = content.count(old_str)
        if count == 0:
            return f"Error: String not found in {path}. Check exact whitespace/indentation."
        if count > 1:
            return f"Error: String found {count} times in {path}. Provide more context to make it unique."

        new_content = content.replace(old_str, new_str, 1)
        with open(path, 'w') as f:
            f.write(new_content)

        old_lines = old_str.count('\n') + 1
        new_lines = new_str.count('\n') + 1
        return f"✓ Edited {path}: replaced {old_lines} lines with {new_lines} lines"
    except Exception as e:
        return f"Error editing file: {e}"


def tool_create_file(args: dict, work_dir: str) -> str:
    path = _resolve_path(args['path'], work_dir)
    content = args['content']

    if os.path.exists(path):
        return f"Error: File already exists: {path}. Use write_file to overwrite."

    try:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        return f"✓ Created {path}"
    except Exception as e:
        return f"Error creating file: {e}"


def tool_delete_file(args: dict, work_dir: str) -> str:
    path = _resolve_path(args['path'], work_dir)

    if not os.path.exists(path):
        return f"Error: Not found: {path}"

    try:
        if os.path.isfile(path):
            os.remove(path)
            return f"✓ Deleted file: {path}"
        elif os.path.isdir(path):
            if os.listdir(path):
                return f"Error: Directory not empty: {path}. Use run_command with 'rm -rf' if you're sure."
            os.rmdir(path)
            return f"✓ Deleted empty directory: {path}"
    except Exception as e:
        return f"Error deleting: {e}"


def tool_list_dir(args: dict, work_dir: str) -> str:
    path = _resolve_path(args.get('path', '.'), work_dir)
    recursive = args.get('recursive', False)
    show_hidden = args.get('show_hidden', False)

    if not os.path.exists(path):
        return f"Error: Directory not found: {path}"

    try:
        lines = [f"📁 {path}/\n"]

        if recursive:
            for root, dirs, files in os.walk(path):
                # Filter ignored dirs
                dirs[:] = sorted([d for d in dirs
                                   if d not in IGNORE_DIRS
                                   and (show_hidden or not d.startswith('.'))])

                level = root.replace(path, '').count(os.sep)
                if level > 4:  # Max depth for recursive
                    dirs.clear()
                    continue

                indent = '  ' * level
                rel_root = os.path.relpath(root, path)
                if rel_root != '.':
                    lines.append(f"{indent}📁 {os.path.basename(root)}/\n")

                sub_indent = '  ' * (level + 1)
                for f in sorted(files):
                    if not show_hidden and f.startswith('.'):
                        continue
                    fpath = os.path.join(root, f)
                    size = os.path.getsize(fpath)
                    size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                    lines.append(f"{sub_indent}📄 {f} ({size_str})\n")
        else:
            entries = sorted(os.listdir(path))
            dirs_list = []
            files_list = []
            for entry in entries:
                if not show_hidden and entry.startswith('.'):
                    continue
                full = os.path.join(path, entry)
                if os.path.isdir(full):
                    dirs_list.append(entry)
                else:
                    files_list.append(entry)

            for d in dirs_list:
                if d in IGNORE_DIRS:
                    lines.append(f"  📁 {d}/ (ignored)\n")
                else:
                    lines.append(f"  📁 {d}/\n")
            for f in files_list:
                full = os.path.join(path, f)
                size = os.path.getsize(full)
                size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                lines.append(f"  📄 {f} ({size_str})\n")

        return ''.join(lines)
    except Exception as e:
        return f"Error listing directory: {e}"


def tool_search_code(args: dict, work_dir: str) -> str:
    pattern = args['pattern']
    file_pattern = args.get('file_pattern', '*')
    case_sensitive = args.get('case_sensitive', False)

    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Invalid regex pattern: {e}"

    results = []
    match_count = 0
    MAX_MATCHES = 50

    for root, dirs, files in os.walk(work_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]

        for fname in files:
            if not fnmatch.fnmatch(fname, file_pattern):
                continue

            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, work_dir)

            if os.path.getsize(fpath) > MAX_FILE_SIZE:
                continue

            try:
                with open(fpath, 'r', errors='replace') as f:
                    lines = f.readlines()
            except Exception:
                continue

            file_matches = []
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    file_matches.append(f"  {i:4d}: {line.rstrip()}")
                    match_count += 1
                    if match_count >= MAX_MATCHES:
                        break

            if file_matches:
                results.append(f"\n{rel_path}:")
                results.extend(file_matches[:10])  # Max 10 matches per file
                if len(file_matches) > 10:
                    results.append(f"  ... ({len(file_matches) - 10} more matches)")

            if match_count >= MAX_MATCHES:
                results.append(f"\n[Stopped at {MAX_MATCHES} matches. Refine pattern or use file_pattern filter.]")
                break

    if not results:
        return f"No matches found for '{pattern}'"

    return f"Found {match_count} match(es) for '{pattern}':\n" + '\n'.join(results)


def tool_run_command(args: dict, work_dir: str) -> str:
    command = args['command']
    timeout = args.get('timeout', 60)
    cwd = args.get('cwd') or work_dir

    if not os.path.isabs(cwd):
        cwd = os.path.join(work_dir, cwd)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")

        status = f"Exit code: {result.returncode}"
        if result.returncode == 0:
            status = f"✓ {status}"
        else:
            status = f"✗ {status} (error)"

        return '\n'.join(output) + f"\n{status}" if output else status

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s"
    except Exception as e:
        return f"Error running command: {e}"


def tool_find_files(args: dict, work_dir: str) -> str:
    pattern = args['pattern']
    path = _resolve_path(args.get('path', '.'), work_dir)

    try:
        matches = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for fname in files:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, work_dir)
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(fname, pattern.split('/')[-1]):
                    size = os.path.getsize(fpath)
                    size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                    matches.append(f"  {rel} ({size_str})")

        if not matches:
            return f"No files found matching '{pattern}'"

        return f"Found {len(matches)} file(s) matching '{pattern}':\n" + '\n'.join(matches[:100])
    except Exception as e:
        return f"Error finding files: {e}"


def tool_fetch_url(args: dict, work_dir: str) -> str:
    import urllib.request
    url = args['url']

    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 localcode-agent/1.0'}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode('utf-8', errors='replace')

        # Basic HTML stripping
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()

        if len(content) > 10000:
            content = content[:10000] + "\n\n[Content truncated...]"

        return f"[{url}]\n\n{content}"
    except Exception as e:
        return f"Error fetching URL: {e}"


# ── DISPATCHER ────────────────────────────────────────────────────────────────

TOOL_MAP = {
    'read_file':    tool_read_file,
    'write_file':   tool_write_file,
    'edit_file':    tool_edit_file,
    'create_file':  tool_create_file,
    'delete_file':  tool_delete_file,
    'list_dir':     tool_list_dir,
    'search_code':  tool_search_code,
    'run_command':  tool_run_command,
    'find_files':   tool_find_files,
    'fetch_url':    tool_fetch_url,
}


def execute_tool(name: str, args: dict, work_dir: str) -> str:
    """Execute a tool by name with given args."""
    fn = TOOL_MAP.get(name)
    if not fn:
        return f"Error: Unknown tool '{name}'"
    try:
        return fn(args, work_dir)
    except Exception as e:
        return f"Error in tool '{name}': {e}"
