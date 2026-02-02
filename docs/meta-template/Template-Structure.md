# Template Structure

Understanding the repository organization and key files in repo-skeletor.

## 📁 Directory Structure

```
repo-skeletor/
├── .github/
│   └── workflows/           # GitHub Actions (not in template by default)
├── docs/
│   └── wiki/               # This documentation
├── golden-repo-template/   # Template files to be copied
│   ├── README.md           # Template README
│   └── setup.sh           # Setup script
├── ci.yml                 # Continuous Integration workflow
├── claude.yml             # Claude Code automation
├── deploy.yml             # Deployment pipeline
├── linear-to-notion-sync.yml   # Linear → Notion sync
├── notion-spec-to-linear.yml   # Notion → Linear conversion
├── config.yaml            # Continue.dev configuration
├── mcp-servers.yaml       # MCP server definitions
├── settings.json          # Claude Code settings
├── styleguide.md          # Project coding standards
├── setup.sh               # Interactive setup script
├── LICENSE                # License file
└── README.md              # Main documentation
```

## 🔧 Configuration Files

### AI Assistant Configurations

#### `settings.json` - Claude Code Settings
Configures Claude Code behavior, permissions, and integrations:
```json
{
  "project": {
    "name": "{{PROJECT_NAME}}",
    "type": "{{PROJECT_TYPE}}"
  },
  "permissions": {
    "allowedTools": ["Edit", "Read", "Write", "Bash", "Glob", "Grep"],
    "allowedDirectories": ["src/", "lib/", "tests/", "docs/"]
  }
}
```

**Key settings:**
- **allowedTools**: Controls which operations Claude can perform
- **allowedDirectories**: Restricts file access for security
- **integrations**: Linear and Notion integration settings

#### `config.yaml` - Continue.dev Configuration
Main configuration for Continue.dev AI assistant:
```yaml
models:
  - name: "claude-sonnet"
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
    
chat: claude-sonnet
autocomplete: claude-haiku
```

**Key sections:**
- **models**: Available AI models and their configurations
- **contextProviders**: Sources of context (files, git, docs)
- **slashCommands**: Custom commands like `/review`, `/test`
- **rules**: Project-specific coding guidelines

#### `mcp-servers.yaml` - MCP Server Definitions
Configures Model Context Protocol servers for enhanced AI capabilities:
```yaml
mcpServers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@anthropic/mcp-server-filesystem"]
    
  - name: "github"
    command: "npx"
    args: ["-y", "@anthropic/mcp-server-github"]
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
```

**Available servers:**
- **filesystem**: Safe file operations
- **github**: Repository, PR, and issue management
- **linear**: Issue tracking integration
- **notion**: Documentation access
- **web-search**: Research and documentation lookup
- **memory**: Persistent context across sessions

#### `styleguide.md` - Coding Standards
Project-specific coding conventions and style guide. Used by AI assistants for consistent code generation.

### Workflow Files

#### `ci.yml` - Continuous Integration
**Purpose**: Automated testing, linting, and building on every PR and push.

**Jobs:**
- `lint`: ESLint, TypeScript type checking, Prettier
- `test`: Unit tests with coverage
- `build`: Production build verification
- `integration`: Integration tests (main branch only)
- `security`: Security audit with pnpm and Snyk

**Triggers:**
```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

#### `claude.yml` - Claude Code Automation
**Purpose**: AI-powered code assistance via @claude mentions.

**Features:**
- Responds to `@claude` mentions in issues and PRs
- Automated PR reviews
- Creates branches following Linear patterns
- Sticky comments for ongoing assistance

**Triggers:**
```yaml
on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [assigned, labeled]
```

#### `deploy.yml` - Deployment Pipeline
**Purpose**: Automated deployments to staging and production.

**Environments:**
- **Staging**: Auto-deploys from `main` branch
- **Production**: Deploys from tags like `v1.0.0`

**Jobs:**
- `setup`: Determine environment and version
- `build`: Create production build
- `deploy-staging`: Deploy to staging environment
- `deploy-production`: Deploy to production with release creation

#### `linear-to-notion-sync.yml` - Linear → Notion Sync
**Purpose**: Sync Linear issues to Notion database.

**Triggers:**
- Repository dispatch (Linear webhook)
- Manual workflow dispatch

**Process:**
1. Fetch Linear issue data via API
2. Map Linear fields to Notion properties
3. Create or update Notion page
4. Link back to Linear

#### `notion-spec-to-linear.yml` - Notion → Linear Conversion
**Purpose**: Convert Notion spec documents into Linear epics with sub-issues.

**Process:**
1. Parse Notion page content
2. Extract tasks from checkboxes and lists
3. Create Linear epic issue
4. Create sub-issues for each task
5. Update Notion page with Linear links

### Template Files

#### `golden-repo-template/README.md`
Template README that gets customized during setup. Contains:
- Project overview structure
- Setup instructions
- Workflow documentation
- Branch naming conventions
- Security guidelines

#### `setup.sh`
Interactive shell script that:
1. Prompts for project details
2. Replaces `{{PLACEHOLDERS}}` in all config files
3. Creates `.env.example`
4. Updates `.gitignore`
5. Initializes git repository

## 📦 When Using the Template

After running `setup.sh`, your new project will have:

```
your-project/
├── .claude/
│   └── settings.json          # ← Customized with your project name
├── .gemini/
│   ├── config.yaml            # ← Gemini configuration
│   └── styleguide.md          # ← Your coding standards
├── .github/
│   └── workflows/
│       ├── claude.yml         # ← AI automation
│       ├── ci.yml             # ← CI pipeline
│       ├── deploy.yml         # ← Deployment
│       ├── linear-to-notion-sync.yml
│       └── notion-spec-to-linear.yml
├── .continue/
│   ├── config.yaml            # ← Continue.dev config
│   └── mcpServers/
│       └── mcp-servers.yaml   # ← MCP servers
├── src/                       # ← Your source code
├── tests/                     # ← Your tests
├── .env                       # ← Your secrets (gitignored)
├── .env.example               # ← Template for secrets
├── .gitignore                 # ← Updated with template patterns
├── package.json               # ← Your project dependencies
└── README.md                  # ← Customized README
```

## 🔑 Key Concepts

### Placeholders
Template files use placeholders that get replaced by `setup.sh`:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{PROJECT_NAME}}` | Project name | `my-awesome-api` |
| `{{PROJECT_DESCRIPTION}}` | Brief description | `REST API for user management` |
| `{{PROJECT_TYPE}}` | Project type | `api`, `web`, `cli`, `lib` |
| `{{PROJECT_DOMAIN}}` | Domain name | `example.com` |
| `{{NOTION_SPEC_DATABASE_ID}}` | Notion database ID | `abc123...` |
| `{{NOTION_WIKI_PAGE_ID}}` | Notion wiki page ID | `def456...` |
| `{{LINEAR_TEAM_ID}}` | Linear team ID | `a1b2c3d4...` |

### File Patterns to Ignore

The template includes comprehensive `.gitignore` patterns:

```gitignore
# Never commit
.env
.env.local
.env.*.local
*.key
*.pem
secrets/

# Build artifacts
dist/
build/
.next/
coverage/

# Dependencies
node_modules/
.pnpm-store/
```

## 📝 Customizing the Structure

### Adding New Workflows
1. Create `.github/workflows/` directory
2. Add workflow files (`.yml`)
3. Reference secrets in `env:` sections
4. Test with `workflow_dispatch` trigger first

### Adding New MCP Servers
1. Edit `mcp-servers.yaml`
2. Add server configuration:
   ```yaml
   - name: "my-server"
     command: "npx"
     args: ["-y", "@org/mcp-server-name"]
     env:
       API_KEY: "${MY_API_KEY}"
   ```
3. Add required secrets to `.env`

### Modifying Claude Settings
1. Edit `settings.json`
2. Adjust `allowedTools` for more/less permissions
3. Update `allowedDirectories` for file access
4. Configure integrations as needed

---

**Previous:** [Quick Start Guide](./Quick-Start-Guide.md) | **Next:** [GitHub Actions Architecture](./GitHub-Actions-Architecture.md) →
