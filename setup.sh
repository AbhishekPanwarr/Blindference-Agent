#!/usr/bin/env bash
# Blindference Agent SDK — Development Setup
# Usage: curl -sSL https://raw.githubusercontent.com/baync180705/blindference-agent/main/setup.sh | bash

set -e

REPO_URL="https://github.com/baync180705/blindference-agent.git"
INSTALL_DIR="${INSTALL_DIR:-blindference-agent}"

echo "Blindference Agent SDK — Setup"
echo "=============================="
echo ""

# 1. Clone the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory '$INSTALL_DIR' exists. Pulling latest..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo ""

# 2. Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || true)
if [ -z "$PYTHON_VERSION" ]; then
    echo "Error: Python 3 not found. Install Python ≥3.10."
    exit 1
fi

MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo "Error: Python $PYTHON_VERSION is too old. Need ≥3.10."
    exit 1
fi

echo "Python $PYTHON_VERSION — OK"

# 3. Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -e ".[dev,langchain]"

# 4. Check Node.js (required for CoFHE bridge)
if ! command -v node &> /dev/null; then
    echo ""
    echo "Warning: Node.js not found. The CoFHE bridge requires Node.js ≥18."
    echo "Install from https://nodejs.org/ or your package manager."
    echo "Then run: npm install"
    NODE_OK=false
else
    NODE_VERSION=$(node --version | sed 's/v//')
    echo "Node.js $NODE_VERSION — OK"
    NODE_OK=true
fi

# 5. Install npm dependencies
if [ "$NODE_OK" = true ]; then
    echo ""
    echo "Installing npm dependencies (CoFHE bridge)..."
    npm install
fi

# 6. Create .env template
if [ ! -f .env ] && [ ! -f .env.local ]; then
    echo ""
    echo "Creating .env template..."
    cat > .env << 'EOF'
# Blindference Agent Configuration
# Arbitrum Sepolia RPC endpoint — get a free key at https://www.alchemy.com/
BLF_COFHE_RPC=https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY

# Generate a fresh wallet for the agent, or use an existing one
BLF_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE

# ICL endpoint (default is production)
BLF_ICL_URL=https://icl.blindference.xyz
EOF
    echo ".env created — edit it with your keys"
else
    echo ".env already exists"
fi

# 7. Run tests
echo ""
echo "Running tests..."
python -m pytest tests/ -q --tb=short || true

# 8. Next steps
echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Alchemy API key and agent wallet private key"
echo "  2. Start the notebook:"
echo "     jupyter lab examples/getting_started.ipynb"
echo "  3. Or run an example:"
echo "     python examples/simple_agent.py"
echo ""
echo "For development without keys, set mock=True in the agent constructor."
echo "See examples/getting_started.ipynb for details."
