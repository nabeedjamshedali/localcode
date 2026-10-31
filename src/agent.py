"""
Core coding agent — handles the tool-calling loop with Ollama.
Implements: read files, write files, run commands, search code,
list directory, create files, delete files, grep, web fetch.
"""
import os
import json
import subprocess
import urllib.request
import urllib.error
import glob
import fnmatch
from pathlib import Path
from .ui import UI
from .tools import TOOLS, execute_tool
from .config import Config

SYSTEM_PROMPT = """You are an expert AI coding agent running locally on the user's machine.
You have full access to their codebase and terminal. You work like Claude Code.

Current working directory: {work_dir}

## Your Capabilities
You can read files, write files, run shell commands, search code, list directories,
create/delete files, grep for patterns, and fetch web pages.

## How to Work
1. ALWAYS explore before acting — read files, list directories to understand context
2. Make changes incrementally and verify them
3. Explain what you're doing and why
4. When writing code, follow the existing style and conventions of the project
5. Run tests after making changes when possible
6. Be thorough — check edge cases, handle errors

## Tool Usage Rules
- Use read_file to inspect any file before editing it
- Use list_dir to understand project structure
- Use search_code to find relevant code across the project
- Use run_command for: running tests, building, installing packages, git operations
- Use write_file only when you have the complete, correct content
- Always confirm destructive operations (delete, overwrite important files)
- Chain tools together to solve complex problems step by step

## Response Style
- Be concise but complete
- Show code changes in context
- Explain your reasoning briefly
- If something fails, diagnose and fix it automatically
"""

DEFAULT_MODELS = [
    "qwen2.5-coder:14b",   # Best coding model, needs 10GB RAM
    "qwen2.5-coder:7b",    # Good balance, needs 6GB RAM
    "qwen2.5-coder:3b",    # Fastest, needs 3GB RAM, less capable
    "codellama:13b",        # Alternative
    "llama3.1:8b",          # General purpose fallback
]


class CodingAgent:
    def __init__(self, work_dir: str, model: str | None, auto_confirm: bool, ui: UI):
        self.work_dir = work_dir
        self.auto_confirm = auto_confirm
        self.ui = ui
        self.config = Config()
        self.conversation_history = []

        # Resolve model
        self.model = model or self.config.get('model') or self._pick_best_model()
        self.ollama_url = self.config.get('ollama_url') or 'http://localhost:11434'

    def check_ollama(self) -> bool:
        """Check if Ollama server is running."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def _pick_best_model(self) -> str:
        """Auto-select the best available model."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
                available = [m['name'] for m in data.get('models', [])]

            if not available:
                return DEFAULT_MODELS[1]  # Default if no models found

            # Prefer coding models in priority order
            for preferred in DEFAULT_MODELS:
                for avail in available:
                    if avail.startswith(preferred.split(':')[0]):
                        return avail

            return available[0]  # Use whatever is available
        except Exception:
            return DEFAULT_MODELS[1]

    def _build_system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(work_dir=self.work_dir)

    def _call_ollama(self, messages: list) -> dict:
        """Call Ollama API with tool support."""
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_ctx": 8192,
                "num_predict": 4096,
            }
        }).encode()

        req = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def _run_agent_loop(self, user_message: str):
        """Core agentic loop: send message → get response → execute tools → repeat."""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            *self.conversation_history
        ]

        max_iterations = 20  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                self.ui.thinking()
                response = self._call_ollama(messages)
            except urllib.error.URLError as e:
                self.ui.error(f"Failed to reach Ollama: {e}")
                return
            except Exception as e:
                self.ui.error(f"API error: {e}")
                return

            assistant_message = response.get('message', {})
            content = assistant_message.get('content', '')
            tool_calls = assistant_message.get('tool_calls', [])

            # Print any text response
            if content and content.strip():
                self.ui.assistant_message(content)

            # If no tool calls, we're done
            if not tool_calls:
                # Add final response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": content
                })
                break

            # Add assistant message with tool calls to conversation
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls
            })

            # Execute each tool call
            tool_results = []
            for tool_call in tool_calls:
                fn_name = tool_call.get('function', {}).get('name', '')
                fn_args = tool_call.get('function', {}).get('arguments', {})

                # Handle string args (some models serialize as JSON string)
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except json.JSONDecodeError:
                        fn_args = {}

                # Show what tool is being called
                self.ui.tool_call(fn_name, fn_args)

                # Ask confirmation for destructive operations
                if not self.auto_confirm and fn_name in ('write_file', 'run_command', 'delete_file', 'create_file'):
                    if not self.ui.confirm(fn_name, fn_args):
                        result = "Operation cancelled by user."
                        self.ui.info("Skipped.")
                    else:
                        result = execute_tool(fn_name, fn_args, self.work_dir)
                        self.ui.tool_result(fn_name, result)
                else:
                    result = execute_tool(fn_name, fn_args, self.work_dir)
                    self.ui.tool_result(fn_name, result)

                tool_results.append({
                    "role": "tool",
                    "content": str(result),
                })

            # Add all tool results to messages
            messages.extend(tool_results)

        if iteration >= max_iterations:
            self.ui.warning("Max iterations reached. Task may be incomplete.")

    def run_once(self, prompt: str):
        """Run a single prompt and exit."""
        self.ui.print_header(self.model, self.work_dir)
        self._run_agent_loop(prompt)

    def run_interactive(self):
        """Interactive REPL mode."""
        self.ui.print_header(self.model, self.work_dir)
        self.ui.print_help()

        while True:
            try:
                user_input = self.ui.get_input()
            except (KeyboardInterrupt, EOFError):
                self.ui.goodbye()
                break

            if not user_input.strip():
                continue

            # Built-in commands
            cmd = user_input.strip().lower()
            if cmd in ('/exit', '/quit', 'exit', 'quit'):
                self.ui.goodbye()
                break
            elif cmd in ('/clear', '/reset'):
                self.conversation_history = []
                self.ui.info("Conversation history cleared.")
                continue
            elif cmd in ('/help',):
                self.ui.print_help()
                continue
            elif cmd.startswith('/model '):
                new_model = user_input.strip()[7:].strip()
                self.model = new_model
                self.ui.info(f"Model switched to: {new_model}")
                continue
            elif cmd in ('/history',):
                self.ui.show_history(self.conversation_history)
                continue

            self._run_agent_loop(user_input)
