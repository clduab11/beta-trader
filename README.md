# Golden Repo Template

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
│       └── notion-to-linear-sync.yml    # Notion → Linear sync
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
git clone https://github.com/parallax-analytics/golden-repo-template.git my-project
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
gh workflow run linear-to-notion-sync.yml -f issue_id=PAR-123 -f sync_type=full
```

**Webhook Setup**:
1. Go to Linear Settings → API → Webhooks
2. Create webhook with URL: `https://api.github.com/repos/clduab11/repo-skeletor/dispatches`
3. Add header: `Authorization: Bearer YOUR_GITHUB_PAT`
4. Add header: `Accept: application/vnd.github.v3+json`
5. Set payload: `{"event_type": "linear-webhook", "client_payload": {"issue_id": "{{issue.identifier}}", "action": "{{action}}"}}`

### Notion → Linear Sync

Convert Notion specs to Linear epics with sub-issues:

```bash
gh workflow run notion-to-linear-sync.yml \
  -f notion_page_id=abc123 \
  -f create_epic=true \
  -f linear_project="Q1 Features"
```

**Webhook Setup**:
1. Create Notion integration at https://www.notion.so/my-integrations
2. Use Notion's webhook API or automation tools (Zapier, n8n) to trigger:
3. Webhook URL: `https://api.github.com/repos/clduab11/repo-skeletor/dispatches`
4. Set payload: `{"event_type": "notion-spec-ready", "client_payload": {"notion_page_id": "{{page_id}}"}}`

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
