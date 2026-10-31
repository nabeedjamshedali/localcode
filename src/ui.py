"""
Terminal UI for localcode agent.
Handles colors, formatting, confirmations, input, output.
"""
import sys
import os
import json
import threading
import time

# ANSI color codes
RESET   = '\033[0m'
BOLD    = '\033[1m'
DIM     = '\033[2m'
CYAN    = '\033[96m'
BLUE    = '\033[94m'
GREEN   = '\033[92m'
YELLOW  = '\033[93m'
RED     = '\033[91m'
MAGENTA = '\033[95m'
WHITE   = '\033[97m'
GRAY    = '\033[90m'

# Check if terminal supports colors
USE_COLOR = sys.stdout.isatty() and os.name != 'nt' or os.environ.get('FORCE_COLOR')

def c(code, text):
    """Apply color if supported."""
    if USE_COLOR:
        return f"{code}{text}{RESET}"
    return text


class Spinner:
    """Animated thinking spinner."""
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, text='Thinking'):
        self.text = text
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(f"\r{c(CYAN, frame)} {c(DIM, self.text)}...")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1

    def start(self):
        if sys.stdout.isatty():
            self._thread.start()

    def stop(self):
        self._stop.set()
        if sys.stdout.isatty():
            sys.stdout.write('\r' + ' ' * 40 + '\r')
            sys.stdout.flush()


class UI:
    def __init__(self):
        self._spinner = None

    def print_header(self, model: str, work_dir: str):
        print()
        print(c(BOLD + CYAN, '╔══════════════════════════════════════════╗'))
        print(c(BOLD + CYAN, '║') + c(BOLD + WHITE, '   🤖 localcode — Local AI Coding Agent   ') + c(BOLD + CYAN, '║'))
        print(c(BOLD + CYAN, '╚══════════════════════════════════════════╝'))
        print(f"  {c(DIM, 'Model:')}  {c(GREEN, model)}")
        print(f"  {c(DIM, 'Dir:')}    {c(CYAN, work_dir)}")
        print(f"  {c(DIM, 'Type')} {c(GRAY, '/help')} {c(DIM, 'for commands,')}", end=' ')
        print(c(GRAY, 'Ctrl+C') + c(DIM, ' to exit'))
        print()

    def print_help(self):
        help_text = [
            ("", c(DIM, "─" * 44)),
            ("Commands:", ""),
            (f"  {c(CYAN, '/help')}",     "Show this help"),
            (f"  {c(CYAN, '/clear')}",    "Clear conversation history"),
            (f"  {c(CYAN, '/model')} {c(DIM, '<name')})", "Switch model (e.g. qwen2.5-coder:14b)"),
            (f"  {c(CYAN, '/history')}",  "Show conversation history"),
            (f"  {c(CYAN, '/exit')}",     "Exit"),
            ("", c(DIM, "─" * 44)),
            ("Examples:", ""),
            (f"  {c(WHITE, 'explain this codebase')}", ""),
            (f"  {c(WHITE, 'add input validation to the login endpoint')}", ""),
            (f"  {c(WHITE, 'find all TODO comments and fix them')}", ""),
            (f"  {c(WHITE, 'write tests for src/auth.py')}", ""),
            (f"  {c(WHITE, 'refactor the database connection to use a pool')}", ""),
            ("", c(DIM, "─" * 44)),
        ]
        for left, right in help_text:
            if left and right:
                print(f"{left:<35} {right}")
            else:
                print(left or right)
        print()

    def thinking(self):
        """Show thinking indicator."""
        self._spinner = Spinner("Thinking")
        self._spinner.start()

    def _stop_spinner(self):
        if self._spinner:
            self._spinner.stop()
            self._spinner = None

    def assistant_message(self, text: str):
        self._stop_spinner()
        print()
        prefix = c(BOLD + CYAN, '◆ ')
        # Handle multi-line with indentation
        lines = text.split('\n')
        first = True
        in_code_block = False
        for line in lines:
            if line.startswith('```'):
                in_code_block = not in_code_block
                if first:
                    print(f"{prefix}{c(DIM, line)}")
                    first = False
                else:
                    print(f"  {c(DIM, line)}")
            elif in_code_block:
                if first:
                    print(f"{prefix}{c(GREEN, line)}")
                    first = False
                else:
                    print(f"  {c(GREEN, line)}")
            else:
                if first:
                    print(f"{prefix}{line}")
                    first = False
                else:
                    print(f"  {line}")
        print()

    def tool_call(self, name: str, args: dict):
        self._stop_spinner()
        # Format args preview
        arg_preview = ''
        if 'path' in args:
            arg_preview = c(CYAN, args['path'])
        elif 'command' in args:
            arg_preview = c(YELLOW, f"$ {args['command'][:60]}")
        elif 'pattern' in args:
            arg_preview = c(MAGENTA, f"/{args['pattern']}/")
        elif 'url' in args:
            arg_preview = c(CYAN, args['url'][:60])

        icon_map = {
            'read_file':    '📖',
            'write_file':   '✏️ ',
            'edit_file':    '🔧',
            'create_file':  '✨',
            'delete_file':  '🗑️ ',
            'list_dir':     '📁',
            'search_code':  '🔍',
            'run_command':  '⚡',
            'find_files':   '🔎',
            'fetch_url':    '🌐',
        }
        icon = icon_map.get(name, '🔨')
        tool_label = c(BOLD + MAGENTA, name)
        print(f"  {icon} {tool_label} {arg_preview}")

    def tool_result(self, name: str, result: str):
        """Show tool result, abbreviated if long."""
        lines = result.strip().split('\n')
        MAX_LINES = 15

        if name in ('run_command',):
            # Show full output for commands (trimmed)
            shown = lines[:MAX_LINES]
            color = GREEN if '✓' in result else (RED if '✗' in result else GRAY)
            for line in shown:
                print(f"    {c(color, line)}")
            if len(lines) > MAX_LINES:
                print(f"    {c(DIM, f'... ({len(lines) - MAX_LINES} more lines)')}")
        elif name in ('read_file',):
            # Show first few lines of file reads
            shown = lines[:8]
            for line in shown:
                print(f"    {c(GRAY, line)}")
            if len(lines) > 8:
                print(f"    {c(DIM, f'... ({len(lines) - 8} more lines)')}")
        elif lines[0].startswith('✓'):
            print(f"    {c(GREEN, lines[0])}")
        elif lines[0].startswith('Error') or lines[0].startswith('✗'):
            for line in lines[:5]:
                print(f"    {c(RED, line)}")
        else:
            shown = lines[:6]
            for line in shown:
                print(f"    {c(GRAY, line)}")
            if len(lines) > 6:
                print(f"    {c(DIM, f'... ({len(lines) - 6} more lines)')}")

        print()

    def get_input(self) -> str:
        """Get user input with a styled prompt."""
        self._stop_spinner()
        try:
            prompt = f"{c(BOLD + BLUE, '▶')} {c(BOLD, 'You')}: "
            return input(prompt)
        except KeyboardInterrupt:
            print()
            raise

    def confirm(self, tool_name: str, args: dict) -> bool:
        """Ask user to confirm a potentially destructive operation."""
        desc_map = {
            'write_file':   f"Write to file: {args.get('path', '')}",
            'create_file':  f"Create file: {args.get('path', '')}",
            'delete_file':  f"DELETE: {args.get('path', '')}",
            'run_command':  f"Run: {args.get('command', '')}",
        }
        desc = desc_map.get(tool_name, tool_name)
        print(f"\n  {c(YELLOW, '⚠')}  {c(BOLD, desc)}")
        try:
            ans = input(f"  {c(DIM, 'Allow? [Y/n]:')} ").strip().lower()
            return ans in ('', 'y', 'yes')
        except (KeyboardInterrupt, EOFError):
            return False

    def error(self, message: str):
        self._stop_spinner()
        print(f"\n{c(RED, '✗')} {c(BOLD, message)}\n")

    def warning(self, message: str):
        self._stop_spinner()
        print(f"\n{c(YELLOW, '⚠')}  {message}\n")

    def info(self, message: str):
        self._stop_spinner()
        print(f"  {c(CYAN, 'ℹ')}  {message}")

    def show_history(self, history: list):
        if not history:
            self.info("No conversation history.")
            return
        print(f"\n{c(DIM, '─' * 44)}")
        print(c(BOLD, f"Conversation history ({len(history)} messages):"))
        for i, msg in enumerate(history):
            role = msg['role'].upper()
            content = str(msg.get('content', ''))[:80]
            color = CYAN if msg['role'] == 'user' else GREEN
            print(f"  {i+1}. {c(color, role)}: {c(DIM, content)}...")
        print(c(DIM, '─' * 44) + '\n')

    def goodbye(self):
        self._stop_spinner()
        print(f"\n{c(DIM, 'Goodbye! 👋')}\n")
