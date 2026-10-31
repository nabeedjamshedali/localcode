"""
Main entry point for localcode agent.
Handles CLI args, interactive REPL, and single-shot mode.
"""
import sys
import os
import argparse
from .agent import CodingAgent
from .ui import UI

def main():
    parser = argparse.ArgumentParser(
        prog='localcode',
        description='Local AI Coding Agent — runs 100% on your machine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  localcode                          # Interactive REPL mode
  localcode "explain this codebase"  # Single prompt
  localcode --model qwen2.5-coder:7b # Use specific model
  localcode --dir /path/to/project   # Set working directory
        """
    )
    parser.add_argument('prompt', nargs='?', help='Single prompt to run (optional)')
    parser.add_argument('--model', default=None, help='Ollama model to use')
    parser.add_argument('--dir', default=None, help='Project directory (default: current dir)')
    parser.add_argument('--no-confirm', action='store_true', help='Skip confirmation for file writes/commands')
    parser.add_argument('--version', action='version', version='localcode 1.0.0')

    args = parser.parse_args()

    # Set working directory
    work_dir = os.path.abspath(args.dir) if args.dir else os.getcwd()
    if not os.path.isdir(work_dir):
        print(f"Error: directory '{work_dir}' does not exist")
        sys.exit(1)
    os.chdir(work_dir)

    ui = UI()

    # Check Ollama is running
    agent = CodingAgent(
        work_dir=work_dir,
        model=args.model,
        auto_confirm=args.no_confirm,
        ui=ui,
    )

    if not agent.check_ollama():
        ui.error("Ollama is not running. Start it with: ollama serve")
        ui.info("Install Ollama: https://ollama.com/download")
        sys.exit(1)

    if args.prompt:
        # Single-shot mode
        agent.run_once(args.prompt)
    else:
        # Interactive REPL
        agent.run_interactive()
