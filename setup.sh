#!/usr/bin/env bash
# Blindference Agent — One-Command Setup
# Usage: curl -sSL https://raw.githubusercontent.com/baync180705/blindference-agent/main/setup.sh | bash

set -e

REPO_URL="https://github.com/baync180705/blindference-agent.git"
INSTALL_DIR="${INSTALL_DIR:-blindference-agent}"

echo "🚀 Blindference Agent Setup"
echo "=========================="
echo ""

# 1. Clone the repo
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Directory '$INSTALL_DIR' already exists. Pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "📦 Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo ""

# 2. Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || true)
if [ -z "$PYTHON_VERSION" ]; then
    echo "❌ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo "❌ Python $PYTHON_VERSION is too old. Need Python ≥3.10."
    exit 1
fi

echo "✅ Python $PYTHON_VERSION"

# 3. Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -e ".[dev,langchain]"

# 4. Check Node.js
if ! command -v node &> /dev/null; then
    echo ""
    echo "⚠️  Node.js not found. The CoFHE bridge requires Node.js."
    echo "   Install it from https://nodejs.org/ or use your package manager:"
    echo "     Ubuntu/Debian: sudo apt-get install nodejs npm"
    echo "     macOS: brew install node"
    echo "   Then re-run this script."
    NODE_OK=false
else
    NODE_VERSION=$(node --version | sed 's/v//')
    echo "✅ Node.js $NODE_VERSION"
    NODE_OK=true
fi

# 5. Install npm dependencies (if Node is available)
if [ "$NODE_OK" = true ]; then
    echo ""
    echo "📦 Installing npm dependencies (CoFHE bridge)..."
    npm install
    echo "✅ npm deps installed"
fi

# 6. Create .env template
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env template..."
    cat > .env << 'EOF'
# Blindference Agent Configuration
# Get an Alchemy key for Arbitrum Sepolia: https://www.alchemy.com/
BLF_COFHE_RPC=https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY

# Generate a fresh wallet for the agent (or use an existing one)
BLF_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE

# ICL endpoint (default is fine)
BLF_ICL_URL=https://icl.blindference.xyz
EOF
    echo "✅ .env created — edit it with your keys"
else
    echo "✅ .env already exists"
fi

# 7. Run tests
echo ""
echo "🧪 Running tests..."
python -m pytest tests/ -q --tb=short || true

# 8. Print next steps
echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Alchemy API key and private key"
echo "  2. Run the Jupyter notebook:"
echo "     jupyter lab examples/getting_started.ipynb"
echo "  3. Or try an example script:"
echo "     python examples/simple_agent.py"
echo "     python examples/interactive_chat.py"
echo ""
echo "For mock mode (no keys needed):"
echo "  python examples/simple_agent.py  # Already uses mock=True"
echo ""
