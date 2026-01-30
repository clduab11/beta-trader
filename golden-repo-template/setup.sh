#!/bin/bash
# Golden Repo Template Setup Script
# Parallax Analytics

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║     Golden Repo Template Setup                    ║"
echo "║     Parallax Analytics                            ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Prompt for project details
echo -e "${YELLOW}Enter project details:${NC}"
read -p "Project Name: " PROJECT_NAME
read -p "Project Description: " PROJECT_DESCRIPTION
read -p "Project Type (api/web/cli/lib): " PROJECT_TYPE
read -p "Project Domain (e.g., example.com): " PROJECT_DOMAIN

# Optional integrations
echo ""
echo -e "${YELLOW}Integration IDs (press Enter to skip):${NC}"
read -p "Notion Spec Database ID: " NOTION_SPEC_DB
read -p "Notion Wiki Page ID: " NOTION_WIKI_ID
read -p "Linear Team ID: " LINEAR_TEAM_ID

# Replace placeholders in all config files
echo ""
echo -e "${BLUE}Configuring template files...${NC}"

# Function to replace placeholders
replace_placeholders() {
    local file=$1
    if [[ -f "$file" ]]; then
        sed -i.bak "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "$file"
        sed -i.bak "s/{{PROJECT_DESCRIPTION}}/$PROJECT_DESCRIPTION/g" "$file"
        sed -i.bak "s/{{PROJECT_TYPE}}/$PROJECT_TYPE/g" "$file"
        sed -i.bak "s/{{PROJECT_DOMAIN}}/$PROJECT_DOMAIN/g" "$file"

        if [[ -n "$NOTION_SPEC_DB" ]]; then
            sed -i.bak "s/{{NOTION_SPEC_DATABASE_ID}}/$NOTION_SPEC_DB/g" "$file"
        fi
        if [[ -n "$NOTION_WIKI_ID" ]]; then
            sed -i.bak "s/{{NOTION_WIKI_PAGE_ID}}/$NOTION_WIKI_ID/g" "$file"
        fi
        if [[ -n "$LINEAR_TEAM_ID" ]]; then
            sed -i.bak "s/{{LINEAR_TEAM_ID}}/$LINEAR_TEAM_ID/g" "$file"
        fi

        rm -f "${file}.bak"
        echo -e "  ${GREEN}✓${NC} $file"
    fi
}

# Process all config files
replace_placeholders ".claude/settings.json"
replace_placeholders ".gemini/config.yaml"
replace_placeholders ".gemini/styleguide.md"
replace_placeholders ".continue/config.yaml"
replace_placeholders ".continue/mcpServers/mcp-servers.yaml"
replace_placeholders "README.md"

# Create .env.example
echo ""
echo -e "${BLUE}Creating .env.example...${NC}"
cat > .env.example << 'EOF'
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=...
VOYAGE_API_KEY=...
PERPLEXITY_API_KEY=pplx-...
BRAVE_API_KEY=...

# Integration Keys
LINEAR_API_KEY=lin_api_...
NOTION_API_KEY=secret_...
GITHUB_TOKEN=ghp_...

# MCP Server Keys
MEM0_API_KEY=...
CONTEXT7_API_KEY=...

# Optional
SENTRY_AUTH_TOKEN=...
VERCEL_TOKEN=...
DATABASE_URL=postgresql://...
EOF
echo -e "  ${GREEN}✓${NC} .env.example created"

# Create .gitignore additions
echo ""
echo -e "${BLUE}Updating .gitignore...${NC}"
cat >> .gitignore << 'EOF'

# Environment files
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
*.swp
*.swo

# Dependencies
node_modules/
.pnpm-store/

# Build outputs
dist/
build/
.next/
.nuxt/

# Test coverage
coverage/

# OS files
.DS_Store
Thumbs.db

# Secrets
*.pem
*.key
secrets/

# Continue.dev local
.continue/.cache/
.continue/sessions/
EOF
echo -e "  ${GREEN}✓${NC} .gitignore updated"

# Initialize git if not already
if [[ ! -d ".git" ]]; then
    echo ""
    echo -e "${BLUE}Initializing git repository...${NC}"
    git init
    echo -e "  ${GREEN}✓${NC} Git initialized"
fi

# Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗"
echo -e "║     Setup Complete! 🚀                            ║"
echo -e "╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Copy .env.example to .env and fill in your API keys"
echo "2. Add secrets to GitHub repository settings"
echo "3. Install dependencies: pnpm install"
echo "4. Start coding!"
echo ""
echo -e "${BLUE}Required GitHub Secrets:${NC}"
echo "  - ANTHROPIC_API_KEY"
echo "  - LINEAR_API_KEY"
echo "  - NOTION_API_KEY"
echo "  - LINEAR_TEAM_ID"
echo "  - NOTION_SPEC_DATABASE_ID"
echo ""
echo -e "${GREEN}Happy coding! 🎉${NC}"
