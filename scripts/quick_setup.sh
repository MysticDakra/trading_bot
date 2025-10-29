#!/bin/bash

# Quick Setup Script for Hyperliquid Trading System
# This script helps you get started quickly and safely

set -e  # Exit on error

echo "🚀 Hyperliquid Trading System - Quick Setup"
echo "==========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo -e "${GREEN}✅ Python $python_version found${NC}"
else
    echo -e "${RED}❌ Python 3.11+ required, found $python_version${NC}"
    exit 1
fi

# Create virtual environment
echo ""
echo "📦 Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi

# Check if .env exists
echo ""
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env and add your API keys!${NC}"
    echo ""
    echo "Required API keys:"
    echo "  - HYPERLIQUID_API_KEY"
    echo "  - HYPERLIQUID_PRIVATE_KEY"
    echo "  - DEEPSEEK_API_KEY (get from netmind.ai)"
    echo "  - NANSEN_API_KEY (optional)"
    echo ""
    read -p "Press Enter after you've added your API keys to .env..."
else
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
fi

# Test imports
echo ""
echo "🧪 Testing Python imports..."
python3 -c "
import sys
sys.path.insert(0, '.')

try:
    from src.core.config import get_config
    print('${GREEN}✅ Config module${NC}')
except Exception as e:
    print(f'${RED}✗ Config module: {e}${NC}')
    sys.exit(1)

try:
    from src.ai.deepseek_client import DeepSeekClient
    print('${GREEN}✅ DeepSeek client${NC}')
except Exception as e:
    print(f'${RED}✗ DeepSeek client: {e}${NC}')
    sys.exit(1)

try:
    from src.data.market_data import HyperliquidWebSocket
    print('${GREEN}✅ Market data${NC}')
except Exception as e:
    print(f'${RED}✗ Market data: {e}${NC}')
    sys.exit(1)

try:
    from src.risk.risk_manager import RiskManager
    print('${GREEN}✅ Risk manager${NC}')
except Exception as e:
    print(f'${RED}✗ Risk manager: {e}${NC}')
    sys.exit(1)

print('${GREEN}✅ All core modules imported successfully!${NC}')
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Import test failed${NC}"
    exit 1
fi

# Test DeepSeek connection
echo ""
echo "🧪 Testing DeepSeek API connection..."
if python3 scripts/test_deepseek.py; then
    echo -e "${GREEN}✅ DeepSeek API connection successful${NC}"
else
    echo -e "${YELLOW}⚠️  DeepSeek API test failed (optional, can continue)${NC}"
fi

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
pytest tests/ -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests failed (review output above)${NC}"
fi

# Setup complete
echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. 📝 Review MAINNET_DEPLOYMENT.md for deployment guide"
echo ""
echo "2. 🧪 Start with paper trading (RECOMMENDED):"
echo "   python -m src.core.trading_system"
echo ""
echo "3. 💰 Or start with minimal capital ($100):"
echo "   ENABLE_PAPER_TRADING=false ACTIVE_CAPITAL=100 python -m src.core.trading_system"
echo ""
echo "4. 📊 Monitor dashboard at:"
echo "   http://localhost:8080"
echo ""
echo "⚠️  WARNING:"
echo "   - Start with $100-500 MAXIMUM on mainnet"
echo "   - Monitor 24/7 for first week"
echo "   - Read MAINNET_DEPLOYMENT.md for full safety guide"
echo ""
