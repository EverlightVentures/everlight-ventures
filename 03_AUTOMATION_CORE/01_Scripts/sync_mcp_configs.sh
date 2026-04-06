#!/bin/bash
# Sync MCP server configs between Claude Code and Gemini CLI
# Run after adding/changing MCP servers in either config
# Usage: bash sync_mcp_configs.sh

CLAUDE_MCP="/mnt/sdcard/AA_MY_DRIVE/.mcp.json"
GEMINI_SETTINGS="/root/.gemini/settings.json"

# Extract mcpServers from Claude's .mcp.json and merge into Gemini settings
python3 -c "
import json

claude = json.load(open('$CLAUDE_MCP'))
gemini = json.load(open('$GEMINI_SETTINGS'))

claude_servers = claude.get('mcpServers', {})
gemini_servers = gemini.get('mcpServers', {})

# Merge: Claude is source of truth for MCP servers
gemini['mcpServers'] = claude_servers

json.dump(gemini, open('$GEMINI_SETTINGS', 'w'), indent=2)

print(f'Synced {len(claude_servers)} MCP servers: {list(claude_servers.keys())}')
print('Claude -> Gemini: in sync')
"
