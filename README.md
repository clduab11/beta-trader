# Repo Template

> Parallax Analytics Solo Developer Workflow Template

A maximally configured repository template integrating **Claude Code**, **Gemini**, **Continue.dev**, **Linear**, **Notion**, and **GitHub Actions** for an autonomous, AI-augmented development workflow.

## 🏗️ Structure

```
.
├── .claude/
│   └── settings.json          # Claude Code project settings
├── .gemini/
│   ├── config.yaml            # Gemini API configuration
│   └── styleguide.md          # Project coding standards
├── .github/
│   └── workflows/
│       ├── claude.yml         # Claude Code GitHub Action
│       ├── ci.yml             # Continuous Integration
│       ├── deploy.yml         # Deployment pipeline
│       ├── linear-to-notion-sync.yml    # Linear → Notion sync
│       └── notion-spec-to-linear.yml    # Notion spec → Linear issues
├── .continue/
│   ├── config.yaml            # Continue.dev main config
│   └── mcpServers/
│       └── mcp-servers.yaml   # MCP server definitions
└── README.md
```

## 🔧 Setup

### 1. Clone and Configure

```bash
# Clone template
git clone https://github.com/clduab11/repo-skeletor.git my-project
cd my-project

# Run setup script
./setup.sh
```

### 2. Required Secrets

Add these secrets to your GitHub repository (Settings → Secrets → Actions):

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `LINEAR_API_KEY` | Linear API key |
| `NOTION_API_KEY` | Notion integration token |
| `LINEAR_TEAM_ID` | Your Linear team ID |
| `NOTION_SPEC_DATABASE_ID` | Notion database for specs |

### 3. Configure Templates

Replace placeholders in configuration files:

| Placeholder | Replace With |
|-------------|--------------|
| `{{PROJECT_NAME}}` | Your project name |
| `{{PROJECT_DESCRIPTION}}` | Project description |
| `{{PROJECT_TYPE}}` | `api`, `web`, `cli`, etc. |
| `{{PROJECT_DOMAIN}}` | Your domain (e.g., `example.com`) |
| `{{NOTION_SPEC_DATABASE_ID}}` | Notion database ID |
| `{{NOTION_WIKI_PAGE_ID}}` | Notion wiki page ID |

## 🚀 Workflows

### Claude Code (@claude mentions)

Mention `@claude` in PR comments or issues:

```
@claude Review this PR for security issues

@claude Can you add error handling to the auth module?

@claude Fix the failing test in user-service.test.ts
```

### Linear → Notion Sync

Automatically triggered via Linear webhook, or manually:

```bash
gh workflow run linear-to-notion-sync.yml -f issue_id=PAR-123
```

### Notion Spec → Linear Issues

Convert Notion specs to Linear epics with sub-issues:

```bash
gh workflow run notion-spec-to-linear.yml \
  -f notion_page_id=abc123 \
  -f create_epic=true \
  -f linear_project="Q1 Features"
```

## 🤖 Continue.dev Integration

### MCP Servers Available

| Server | Description |
|--------|-------------|
| `filesystem` | Local file operations |
| `github` | Repository, PRs, issues |
| `linear` | Issue tracking |
| `notion` | Documentation |
| `web-search` | Research lookup |
| `memory` | Persistent context (mem0) |
| `context7` | Library docs |

### Custom Slash Commands

| Command | Description |
|---------|-------------|
| `/review` | Code review with styleguide |
| `/test` | Generate Vitest tests |
| `/doc` | Generate JSDoc documentation |
| `/linear` | Create Linear issue from context |
| `/spec` | Generate Notion spec |

## 📋 Branch Naming

Format: `<user>/<linear-id>-<description>`

Example: `clduab11/PAR-123-add-auth-module`

## 🔐 Security

- Secrets are never committed
- `.env*` files are gitignored
- Claude has restricted directory access
- Destructive operations require confirmation

## 📚 Resources

- [Claude Code GitHub Actions](https://github.com/anthropics/claude-code-action)
- [Continue.dev Documentation](https://docs.continue.dev)
- [Linear API](https://developers.linear.app)
- [Notion API](https://developers.notion.com)

---

Built by [Parallax Analytics](https://parallax-analytics.com) 🚀
