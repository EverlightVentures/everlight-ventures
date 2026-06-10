#!/usr/bin/env bash
# OnyxPOS Frontend Setup Script

set -e

echo "=================================="
echo "  OnyxPOS Frontend Setup"
echo "=================================="
echo ""

# Check Node.js version
echo "Checking Node.js version..."
node --version

# Check npm version
echo "Checking npm version..."
npm --version

# Install dependencies
echo "Installing dependencies..."
npm install

echo ""
echo "=================================="
echo "  ✅ Setup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Make sure backend is running on port 5000"
echo "2. Run: npm run dev"
echo "3. Open browser to http://localhost:3000"
echo ""
