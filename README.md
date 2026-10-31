# 🤖 localcode — Local AI Coding Agent

**Works exactly like Claude Code. Runs 100% on your machine. Zero cost. Zero internet.**

```
cd your-project
localcode
▶ You: explain this codebase and find any bugs
```

---

## ✨ What It Does

- **Reads your entire codebase** — understands your project structure
- **Writes & edits files** — makes surgical edits, creates new files
- **Runs commands** — tests, builds, git, npm, pip, anything
- **Searches code** — grep across all files, find patterns
- **Chains tool calls** — reads → edits → runs tests → fixes → repeats
- **Runs offline** — no API keys, no internet required after setup
- **100% private** — your code never leaves your machine

---

## 🚀 Install (One Command)

### Mac / Linux
```bash
git clone <this-repo> localcode
cd localcode
bash install.sh
```

### Windows
```bat
git clone <this-repo> localcode
cd localcode
install.bat
```

That's it. The installer:
1. Installs Ollama (if not present)
2. Auto-detects your RAM and picks the right model
3. Downloads the model
4. Adds `localcode` to your PATH

---

## 📋 Requirements

| Requirement | Details |
|---|---|
| **Python** | 3.10 or higher |
| **Ollama** | Auto-installed |
| **RAM** | 6 GB minimum (8 GB+ recommended) |
| **Disk** | 5–10 GB for model |
| **Internet** | Only for initial model download |

**Zero Python dependencies** — uses only the standard library.

---

## 🎮 Usage

### Interactive Mode (recommended)
```bash
cd /your/project
localcode
```

### Single Command Mode
```bash
localcode "write unit tests for all functions in src/auth.py"
localcode "find all API endpoints and document them"
localcode "refactor the database module to use connection pooling"
```

### Options
```bash
localcode --model qwen2.5-coder:14b   # Use specific model
localcode --dir /path/to/project      # Different directory
localcode --no-confirm                # Skip confirmations (careful!)
```

---

## 💬 Built-in Commands

| Command | Description |
|---|---|
| `/help` | Show help |
| `/clear` | Clear conversation (start fresh) |
| `/model qwen2.5-coder:14b` | Switch model |
| `/history` | Show conversation history |
| `/exit` | Quit |

---

## 🔧 What the Agent Can Do

| Tool | What it does |
|---|---|
| `read_file` | Read any file with optional line ranges |
| `write_file` | Write/overwrite files |
| `edit_file` | Surgical find-and-replace edits |
| `create_file` | Create new files |
| `delete_file` | Delete files |
| `list_dir` | List directory (flat or recursive tree) |
| `search_code` | Grep across entire project |
| `run_command` | Execute any shell command |
| `find_files` | Find files by glob pattern |
| `fetch_url` | Fetch web pages (docs, APIs) |

---

## 🤖 Models

The installer auto-picks the best model for your hardware:

| RAM | Model | Size | Quality |
|---|---|---|---|
| 16 GB+ | qwen2.5-coder:14b | 9 GB | ⭐⭐⭐⭐⭐ Best |
| 8 GB+ | qwen2.5-coder:7b  | 4.7 GB | ⭐⭐⭐⭐ Great |
| 6 GB+  | qwen2.5-coder:3b  | 2 GB | ⭐⭐⭐ Good |

Switch models anytime:
```bash
# Download a different model
ollama pull qwen2.5-coder:14b

# Use it in localcode
localcode --model qwen2.5-coder:14b
# or inside session:
/model qwen2.5-coder:14b
```

---

## 💡 Example Sessions

### Understand a new codebase
```
▶ You: I just cloned this repo. Explain the architecture and main components.

◆ localcode: [reads package.json, lists src/, reads main files]
  This is a Node.js REST API using Express...
```

### Add a feature
```
▶ You: Add rate limiting to all API endpoints. 50 requests/minute per IP.

◆ localcode: [reads existing routes, installs express-rate-limit, edits app.js]
  Done! Added rate limiting middleware...
```

### Debug an issue
```
▶ You: My tests are failing with "Cannot read property of undefined". Fix it.

◆ localcode: [runs tests, reads stack trace, finds bug, edits file, reruns tests]
  Found the issue in auth.js line 42. Fixed null check. Tests passing now.
```

### Write tests
```
▶ You: Write comprehensive unit tests for src/utils.py

◆ localcode: [reads utils.py, writes tests/test_utils.py, runs pytest]
  Created 23 test cases covering all edge cases. All passing.
```

---

## ⚙️ Configuration

Config file: `~/.localcode/config.json`

```json
{
  "model": "qwen2.5-coder:7b",
  "ollama_url": "http://localhost:11434",
  "auto_confirm": false
}
```

Set `auto_confirm: true` to skip all confirmation prompts (not recommended).

---

## 🔐 Privacy

- Your code **never leaves your machine**
- No telemetry, no logging to external services
- Runs entirely through Ollama on localhost
- Works fully offline after model download

---

## 🙏 Credits

Built on top of:
- [Ollama](https://ollama.com) — local model serving
- [Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder) — Alibaba's coding model
- Inspired by [Claude Code](https://claude.ai/code) by Anthropic

---

Made with ❤️ — Making AI free for everyone.
