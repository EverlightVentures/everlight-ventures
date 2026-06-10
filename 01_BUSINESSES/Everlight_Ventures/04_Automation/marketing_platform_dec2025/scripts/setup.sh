#!/bin/bash

# Everlight Ventures Setup Script
# This script helps you get started quickly

set -e

echo "🚀 Everlight Ventures Setup"
echo "============================"
echo ""

# Check Node version
NODE_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
if [ "$NODE_VERSION" -lt 18 ]; then
  echo "❌ Error: Node.js >= 18.0.0 required (you have $(node -v))"
  exit 1
fi
echo "✅ Node.js version check passed"

# Check if .env exists
if [ ! -f .env ]; then
  echo "📝 Creating .env file from .env.example..."
  cp .env.example .env

  # Generate NEXTAUTH_SECRET
  SECRET=$(openssl rand -base64 32)
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/your-secret-key-here-generate-with-openssl-rand-base64-32/$SECRET/" .env
  else
    sed -i "s/your-secret-key-here-generate-with-openssl-rand-base64-32/$SECRET/" .env
  fi

  echo "✅ Created .env file with generated NEXTAUTH_SECRET"
  echo "⚠️  Please edit .env and set your DATABASE_URL"
  echo ""
else
  echo "✅ .env file already exists"
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Generate Prisma client
echo "🔧 Generating Prisma client..."
npm run db:generate

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and set your DATABASE_URL"
echo "2. Run: npm run db:push"
echo "3. (Optional) Run: cd packages/db && npm run seed"
echo "4. Run: npm run dev"
echo ""
echo "Visit http://localhost:3000 when ready!"
