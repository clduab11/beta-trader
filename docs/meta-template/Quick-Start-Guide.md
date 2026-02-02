# Quick Start Guide

Get your AI-augmented development environment up and running in minutes.

## Prerequisites

- **Git** installed on your machine
- **Node.js** v20 or higher
- **pnpm** v9 or higher (or npm/yarn)
- GitHub account with appropriate permissions
- API keys for integrations (see [Secrets Setup](./Secrets-and-Environment-Setup.md))

## Step 1: Clone or Use Template

### Option A: Use as GitHub Template
1. Go to [repo-skeletor repository](https://github.com/clduab11/repo-skeletor)
2. Click **"Use this template"** → **"Create a new repository"**
3. Name your repository and create it
4. Clone your new repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```

### Option B: Clone Directly
```bash
git clone https://github.com/clduab11/repo-skeletor.git my-project
cd my-project
rm -rf .git
git init
```

## Step 2: Run Setup Script

The interactive setup script will configure all template placeholders:

```bash
chmod +x setup.sh
./setup.sh
```

You'll be prompted for:
- **Project Name**: Your project's name
- **Project Description**: Brief description
- **Project Type**: `api`, `web`, `cli`, or `lib`
- **Project Domain**: Your domain (e.g., `example.com`)
- **Notion Spec Database ID**: (optional)
- **Notion Wiki Page ID**: (optional)
- **Linear Team ID**: (optional)

## Step 3: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Fill in your API keys in `.env`:
   ```bash
   # Required for Claude Code
   ANTHROPIC_API_KEY=sk-ant-...
   
   # Required for Linear integration
   LINEAR_API_KEY=lin_api_...
   
   # Required for Notion integration
   NOTION_API_KEY=secret_...
   
   # Required for GitHub operations
   GITHUB_TOKEN=ghp_...
   
   # Optional but recommended
   GOOGLE_AI_API_KEY=...
   VOYAGE_API_KEY=...
   ```

See [Secrets & Environment Setup](./Secrets-and-Environment-Setup.md) for details on obtaining these keys.

## Step 4: Configure GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

**Required:**
- `ANTHROPIC_API_KEY` - Claude API key
- `LINEAR_API_KEY` - Linear API key
- `NOTION_API_KEY` - Notion integration token

**Optional but recommended:**
- `LINEAR_TEAM_ID` - Your Linear team ID
- `NOTION_SPEC_DATABASE_ID` - Notion database for specs
- `CODECOV_TOKEN` - For code coverage reports
- `SNYK_TOKEN` - For security scanning
- `SLACK_WEBHOOK_URL` - For deployment notifications

## Step 5: Install Dependencies

```bash
pnpm install
```

Or with npm:
```bash
npm install
```

## Step 6: Verify Setup

Run a basic build to ensure everything is configured:

```bash
# Type check
pnpm typecheck

# Run linter
pnpm lint

# Run tests (if applicable)
pnpm test

# Build project
pnpm build
```

## Step 7: Create Your First Branch

Follow the Linear-integrated branch naming convention:

```bash
git checkout -b YOUR_USERNAME/ISSUE_ID-brief-description
```

Example:
```bash
git checkout -b clduab11/PAR-123-add-user-auth
```

## Step 8: Test AI Integration

### Test Claude Code
1. Create a test issue or PR
2. Comment with `@claude` followed by your request
3. Claude should respond within a few minutes

### Test Continue.dev (if installed)
1. Open your project in VS Code
2. Ensure Continue.dev extension is installed
3. Try a slash command like `/review` on some code

## Next Steps

Now that you're set up, explore:

- **[Template Structure](./Template-Structure.md)** - Understand the repository layout
- **[GitHub Actions Architecture](./GitHub-Actions-Architecture.md)** - Learn about automated workflows
- **[Customization Guide](./Customization-Guide.md)** - Tailor the template to your needs
- **[Linear ↔ Notion Sync](./Linear-Notion-Sync.md)** - Set up bidirectional syncing

## Troubleshooting

### Setup script fails
- Ensure you have `bash` available
- Check file permissions: `chmod +x setup.sh`
- On Windows, use Git Bash or WSL

### GitHub Actions not triggering
- Verify secrets are added correctly
- Check workflow permissions in Settings → Actions → General
- Ensure workflows are enabled for your repository

### Claude not responding
- Verify `ANTHROPIC_API_KEY` is set in repository secrets
- Check that the workflow file `.github/workflows/claude.yml` exists
- Ensure you're using the trigger phrase `@claude`

### Environment variables not loading
- Ensure `.env` file is in project root
- Check `.env` is in `.gitignore` (never commit secrets!)
- Restart your terminal/IDE after setting environment variables

## Common Commands

```bash
# Development
pnpm dev              # Start development server
pnpm build            # Build for production
pnpm test             # Run tests
pnpm lint             # Run linter
pnpm format           # Format code

# Git operations
git status            # Check repository status
git add .             # Stage all changes
git commit -m "msg"   # Commit changes
git push              # Push to remote

# GitHub CLI (if installed)
gh pr create          # Create pull request
gh workflow list      # List workflows
gh workflow run <name> # Trigger workflow manually
```

---

**Next:** [Template Structure](./Template-Structure.md) →
