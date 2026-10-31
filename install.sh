#!/usr/bin/env bash
# ============================================================
# localcode — One-command installer
# Usage: bash install.sh
# ============================================================

set -e

CYAN='\033[96m'
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BOLD='\033[1m'
RESET='\033[0m'

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║   🤖 localcode — Installing...           ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Check Python 3.10+ ────────────────────────────────────────────────────────
echo -e "${CYAN}[1/5]${RESET} Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python3 not found. Install from https://python.org${RESET}"
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MINOR" -lt 10 ]; then
    echo -e "${RED}✗ Python 3.10+ required (you have $PY_VER)${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PY_VER${RESET}"

# ── Check/Install Ollama ──────────────────────────────────────────────────────
echo -e "${CYAN}[2/5]${RESET} Checking Ollama..."
if ! command -v ollama &>/dev/null; then
    echo -e "${YELLOW}  Ollama not found. Installing...${RESET}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &>/dev/null; then
            brew install ollama
        else
            echo -e "${YELLOW}  Download Ollama from: https://ollama.com/download${RESET}"
            echo -e "${YELLOW}  Then re-run this installer.${RESET}"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo -e "${YELLOW}  Download Ollama from: https://ollama.com/download${RESET}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Ollama installed${RESET}"

# ── Start Ollama server ───────────────────────────────────────────────────────
echo -e "${CYAN}[3/5]${RESET} Starting Ollama server..."
if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
    ollama serve &>/dev/null &
    sleep 3
fi
echo -e "${GREEN}✓ Ollama server running${RESET}"

# ── Pull best coding model ────────────────────────────────────────────────────
echo -e "${CYAN}[4/5]${RESET} Pulling coding model..."
echo ""

# Check available RAM to pick right model
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024)}' || echo 8000000)
TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024))

if [ "$TOTAL_RAM_GB" -ge 14 ]; then
    MODEL="qwen2.5-coder:14b"
    echo -e "  Detected ${TOTAL_RAM_GB}GB RAM → using ${GREEN}qwen2.5-coder:14b${RESET} (best quality)"
elif [ "$TOTAL_RAM_GB" -ge 8 ]; then
    MODEL="qwen2.5-coder:7b"
    echo -e "  Detected ${TOTAL_RAM_GB}GB RAM → using ${GREEN}qwen2.5-coder:7b${RESET} (good balance)"
else
    MODEL="qwen2.5-coder:3b"
    echo -e "  Detected ${TOTAL_RAM_GB}GB RAM → using ${GREEN}qwen2.5-coder:3b${RESET} (lightweight)"
fi

echo ""
ollama pull "$MODEL"
echo -e "${GREEN}✓ Model ready: $MODEL${RESET}"

# ── Install localcode ─────────────────────────────────────────────────────────
echo -e "${CYAN}[5/5]${RESET} Installing localcode..."

INSTALL_DIR="$HOME/.localcode"
mkdir -p "$INSTALL_DIR"

# Copy files
cp -r "$(dirname "$0")/." "$INSTALL_DIR/app/"

# Create wrapper script
cat > "$INSTALL_DIR/localcode" << WRAPPER
#!/usr/bin/env bash
cd "\$PWD"
LOCALCODE_MODEL="$MODEL" python3 "$INSTALL_DIR/app/bin/localcode" "\$@"
WRAPPER
chmod +x "$INSTALL_DIR/localcode"

# Add to PATH
SHELL_RC=""
if [[ -f "$HOME/.zshrc" ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ -f "$HOME/.bashrc" ]]; then
    SHELL_RC="$HOME/.bashrc"
elif [[ -f "$HOME/.bash_profile" ]]; then
    SHELL_RC="$HOME/.bash_profile"
fi

PATH_LINE='export PATH="$HOME/.localcode:$PATH"'
if [ -n "$SHELL_RC" ]; then
    if ! grep -q '.localcode' "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# localcode — Local AI Coding Agent" >> "$SHELL_RC"
        echo "$PATH_LINE" >> "$SHELL_RC"
        echo -e "${GREEN}✓ Added to PATH in $SHELL_RC${RESET}"
    fi
fi

# Save config
mkdir -p "$HOME/.localcode"
cat > "$HOME/.localcode/config.json" << CONFIG
{
  "model": "$MODEL",
  "ollama_url": "http://localhost:11434",
  "auto_confirm": false
}
CONFIG

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║   ✅  localcode installed successfully!  ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${BOLD}Model:${RESET}   $MODEL"
echo -e "  ${BOLD}Usage:${RESET}   ${CYAN}cd your-project && localcode${RESET}"
echo ""
echo -e "  ${BOLD}Restart your terminal or run:${RESET}"
echo -e "  ${CYAN}source $SHELL_RC${RESET}"
echo ""
echo -e "  ${BOLD}Then go to your project:${RESET}"
echo -e "  ${CYAN}cd /path/to/your/project${RESET}"
echo -e "  ${CYAN}localcode${RESET}"
echo ""
