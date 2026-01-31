# Customization Guide

Learn how to adapt repo-skeletor to your specific project needs.

## Overview

While repo-skeletor provides a comprehensive starting point, you'll want to customize it for your project. This guide covers:
- Modifying AI assistant configurations
- Customizing workflows
- Adapting the template structure
- Adding new integrations
- Project-specific settings

---

## AI Assistant Customization

### Claude Code Settings

Edit `settings.json` to control Claude's behavior:

#### 1. Adjust Permissions

**Add more allowed tools**:
```json
{
  "permissions": {
    "allowedTools": [
      "Edit",
      "Read",
      "Write",
      "Bash",
      "Glob",
      "Grep",
      "WebSearch",
      "CodeReview"  // ← Add new tool
    ]
  }
}
```

**Restrict directory access**:
```json
{
  "permissions": {
    "allowedDirectories": [
      "src/",
      "tests/"  // Only these directories
    ],
    "restrictedPatterns": [
      ".env*",
      "*.key",
      "secrets/",
      "config/production/*"  // ← Add specific restrictions
    ]
  }
}
```

#### 2. Customize Integration Behavior

**Linear integration**:
```json
{
  "integrations": {
    "linear": {
      "enabled": true,
      "teamPrefix": "YOUR_TEAM",  // ← Change team prefix
      "autoLinkIssues": true,
      "branchFromIssue": true,
      "autoAssignOnMention": false  // ← Disable auto-assign
    }
  }
}
```

**Notion integration**:
```json
{
  "integrations": {
    "notion": {
      "enabled": true,
      "specDatabaseId": "YOUR_DATABASE_ID",
      "wikiPageId": "YOUR_WIKI_ID",
      "autoSync": false  // ← Manual sync only
    }
  }
}
```

#### 3. Custom Prompts

**Modify system prompt**:
```json
{
  "prompts": {
    "systemPrompt": "You are a senior engineer specializing in {{PROJECT_TYPE}}. Follow these principles: DRY, SOLID, and Test-Driven Development.",
    "codeReviewPrompt": "Focus on: 1) Security 2) Performance 3) Testability",
    "prDescriptionPrompt": "Include: Summary, Technical Details, Testing, Screenshots"
  }
}
```

---

### Continue.dev Configuration

Edit `config.yaml` to customize Continue.dev:

#### 1. Change Models

**Switch to different models**:
```yaml
models:
  # Use GPT-4 instead of Claude
  - name: "gpt4"
    provider: "openai"
    model: "gpt-4-turbo-preview"
    apiKey: "${OPENAI_API_KEY}"
    contextLength: 128000

  # Use local Ollama model
  - name: "local"
    provider: "ollama"
    model: "codellama:34b"
    apiBase: "http://localhost:11434"
    contextLength: 16384

# Set as defaults
chat: gpt4
autocomplete: local
```

**Add specialized models**:
```yaml
models:
  - name: "code-review"
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
    systemMessage: "You are a code review expert. Be thorough but constructive."
    
  - name: "quick-edits"
    provider: "anthropic"
    model: "claude-haiku-4-20250514"
```

#### 2. Custom Slash Commands

**Add project-specific commands**:
```yaml
slashCommands:
  - name: "api-endpoint"
    description: "Generate REST API endpoint"
    prompt: |
      Generate a complete REST API endpoint with:
      - Express route handler
      - Request validation (Zod)
      - Error handling
      - OpenAPI documentation
      - Unit tests

  - name: "component"
    description: "Create React component"
    prompt: |
      Create a React component with:
      - TypeScript props interface
      - Styled components
      - Storybook story
      - Unit tests with React Testing Library
      
  - name: "db-migration"
    description: "Generate database migration"
    prompt: |
      Generate a Prisma migration with:
      - Schema changes
      - Up migration
      - Down migration
      - Seed data if needed
```

#### 3. Add Context Providers

**Add custom documentation**:
```yaml
contextProviders:
  - name: "docs"
    params:
      sites:
        - name: "Your API Docs"
          startUrl: "https://docs.yourproject.com"
        - name: "Internal Wiki"
          startUrl: "https://wiki.company.com/project"
```

**Add custom search**:
```yaml
contextProviders:
  - name: "database-schema"
    type: "custom"
    command: "npx prisma db pull && cat prisma/schema.prisma"
```

#### 4. Project-Specific Rules

```yaml
rules:
  - name: "api-validation"
    pattern: "**/api/**/*.ts"
    instructions: |
      - All inputs must be validated with Zod
      - Return consistent { success, data, error } format
      - Log all errors with request ID

  - name: "react-performance"
    pattern: "**/*.tsx"
    instructions: |
      - Memoize expensive calculations
      - Use React.memo for pure components
      - Avoid inline function definitions in JSX

  - name: "test-quality"
    pattern: "**/*.test.ts"
    instructions: |
      - Minimum 80% code coverage
      - Test edge cases and error paths
      - Use descriptive test names
      - Mock external dependencies
```

---

### MCP Server Customization

Edit `mcp-servers.yaml` to add or modify servers:

#### Add Custom MCP Server

```yaml
mcpServers:
  # Your custom MCP server
  - name: "custom-api"
    command: "npx"
    args:
      - "-y"
      - "@yourcompany/mcp-server-custom"
    env:
      CUSTOM_API_KEY: "${CUSTOM_API_KEY}"
      CUSTOM_BASE_URL: "https://api.yourcompany.com"
    connectionTimeout: 15000
```

#### Configure Database Server

```yaml
mcpServers:
  - name: "postgres"
    command: "npx"
    args:
      - "-y"
      - "@anthropic/mcp-server-postgres"
      - "--connection-string"
      - "${DATABASE_URL}"
    env:
      PGSSL: "true"
    connectionTimeout: 10000
```

#### Add Monitoring Integration

```yaml
mcpServers:
  - name: "sentry"
    command: "npx"
    args:
      - "-y"
      - "@sentry/mcp-server"
    env:
      SENTRY_AUTH_TOKEN: "${SENTRY_AUTH_TOKEN}"
      SENTRY_ORG: "your-org"
      SENTRY_PROJECT: "your-project"
```

---

## Workflow Customization

### CI Workflow Modifications

#### Add Language-Specific Steps

**For Python projects**:
```yaml
jobs:
  test:
    steps:
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
          
      - name: Run tests
        run: pytest --cov=src tests/
```

**For Go projects**:
```yaml
jobs:
  test:
    steps:
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
          
      - name: Run tests
        run: go test -v -race -coverprofile=coverage.out ./...
```

**For Rust projects**:
```yaml
jobs:
  test:
    steps:
      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          
      - name: Run tests
        run: cargo test --all-features
```

#### Add Custom Linting Rules

```yaml
jobs:
  lint:
    steps:
      # Add custom linting step
      - name: Run custom linter
        run: |
          # Your custom linting commands
          pnpm exec custom-lint src/
          
      # Add API schema validation
      - name: Validate OpenAPI spec
        run: pnpm exec openapi-validator api-spec.yaml
```

#### Add Performance Testing

```yaml
jobs:
  performance:
    name: Performance Tests
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Lighthouse CI
        uses: treosh/lighthouse-ci-action@v10
        with:
          urls: |
            https://staging.yourapp.com
          uploadArtifacts: true
```

### Deployment Workflow Customization

#### Add Preview Deployments

```yaml
jobs:
  preview:
    name: Deploy Preview
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel Preview
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          
      - name: Comment PR with preview URL
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '🚀 Preview deployed: ${{ env.PREVIEW_URL }}'
            })
```

#### Add Database Migrations

```yaml
jobs:
  migrate:
    name: Run Migrations
    runs-on: ubuntu-latest
    needs: build
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Prisma migrations
        run: npx prisma migrate deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

#### Add Smoke Tests Post-Deployment

```yaml
jobs:
  smoke-test:
    name: Smoke Tests
    runs-on: ubuntu-latest
    needs: deploy-production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run smoke tests
        run: |
          curl -f https://api.yourapp.com/health || exit 1
          pnpm exec newman run smoke-tests.postman.json
```

---

## Style Guide Customization

Edit `styleguide.md` to match your project's conventions:

### Add Framework-Specific Rules

**For React projects**:
```markdown
## React Best Practices

### Component Structure
- Use functional components with hooks
- Keep components under 200 lines
- Extract complex logic to custom hooks
- Use composition over inheritance

### State Management
- Local state: `useState` for simple state
- Shared state: Context API for app-wide state
- Server state: React Query for API data

### Performance
- Memoize expensive calculations with `useMemo`
- Memoize callbacks with `useCallback`
- Use `React.memo` for pure components
- Lazy load routes with `React.lazy`
```

**For API projects**:
```markdown
## API Design Standards

### REST Endpoints
- Use plural nouns: `/api/users`, not `/api/user`
- Use proper HTTP methods: GET, POST, PUT, DELETE
- Return consistent response format:
  ```json
  {
    "success": true,
    "data": {},
    "error": null
  }
  ```

### Validation
- Validate all inputs with Zod schemas
- Return 400 Bad Request for validation errors
- Include specific error messages

### Authentication
- Use JWT tokens in Authorization header
- Implement refresh token rotation
- Rate limit authentication endpoints
```

### Add Security Guidelines

```markdown
## Security Requirements

### Input Validation
- ✅ Validate all user input
- ✅ Sanitize HTML content
- ✅ Use parameterized queries
- ❌ Never trust client-side validation alone

### Authentication
- ✅ Hash passwords with bcrypt (cost factor 12+)
- ✅ Implement MFA for admin accounts
- ✅ Use secure session management
- ❌ Never store passwords in plain text

### API Security
- ✅ Implement rate limiting
- ✅ Use HTTPS only
- ✅ Validate JWT signatures
- ❌ Never expose internal errors to clients
```

---

## Linear ↔ Notion Sync Customization

### Custom Field Mappings

Edit `linear-to-notion-sync.yml` to add custom fields:

```yaml
- name: Sync to Notion
  uses: actions/github-script@v7
  with:
    script: |
      const properties = {
        'Name': { title: [{ text: { content: issueData.title } }] },
        'Linear ID': { rich_text: [{ text: { content: issueData.identifier } }] },
        'Status': { select: { name: stateMap[issueData.stateType] } },
        
        // Add custom fields
        'Sprint': {
          select: { name: issueData.cycle?.name || 'Backlog' }
        },
        'Story Points': {
          number: issueData.estimate || 0
        },
        'Team': {
          select: { name: issueData.team?.name || 'Engineering' }
        },
        'Epic': {
          relation: [{ id: epicPageId }]  // Link to epic page
        }
      };
```

### Custom Status Mappings

```yaml
# Map Linear states to your Notion statuses
const stateMap = {
  'unstarted': 'To Do',
  'started': 'In Progress',
  'completed': 'Done',
  'canceled': 'Canceled',
  'backlog': 'Backlog',
  'todo': 'To Do',
  'in_review': 'In Review',  // ← Add custom states
  'blocked': 'Blocked'
};
```

---

## Template Structure Customization

### Add New Directories

```bash
mkdir -p src/{api,components,utils,types,hooks,services}
mkdir -p tests/{unit,integration,e2e}
mkdir -p docs/{api,architecture,guides}
```

Update `settings.json` to allow access:
```json
{
  "permissions": {
    "allowedDirectories": [
      "src/",
      "tests/",
      "docs/",
      "scripts/"  // ← Add new directory
    ]
  }
}
```

### Add Project-Specific Files

**Add API documentation**:
```bash
touch docs/api/README.md
touch docs/api/authentication.md
touch docs/api/endpoints.md
```

**Add configuration files**:
```bash
touch .prettierrc
touch .eslintrc.js
touch jest.config.js
touch vitest.config.ts
```

### Create Custom Scripts

Add to `package.json`:
```json
{
  "scripts": {
    "dev": "vite dev",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:e2e": "playwright test",
    "lint": "eslint src",
    "lint:fix": "eslint src --fix",
    "format": "prettier --write src",
    "typecheck": "tsc --noEmit",
    "db:migrate": "prisma migrate dev",
    "db:seed": "prisma db seed",
    "docs:dev": "vitepress dev docs",
    "docs:build": "vitepress build docs"
  }
}
```

---

## Integration Customization

### Add Slack Integration

```yaml
# Add to deployment workflow
- name: Notify Slack on Deploy
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Deployed ${{ github.repository }} to production",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Deployment Successful*\nVersion: `${{ github.ref_name }}`\nAuthor: ${{ github.actor }}"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Add Discord Notifications

```yaml
- name: Discord Notification
  uses: Ilshidur/action-discord@master
  with:
    args: '🚀 {{ EVENT_PAYLOAD.repository.full_name }} deployed to production!'
  env:
    DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
```

### Add Jira Integration

```yaml
- name: Update Jira
  uses: atlassian/gajira-transition@v3
  with:
    issue: ${{ env.JIRA_ISSUE_KEY }}
    transition: "Done"
  env:
    JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
    JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
    JIRA_USER_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
```

---

## Best Practices for Customization

### 1. Document Changes
- Keep a CHANGELOG.md
- Update README.md with custom instructions
- Document custom workflows

### 2. Test Incrementally
- Test workflow changes on a branch first
- Use `workflow_dispatch` for manual testing
- Verify secrets are configured

### 3. Version Control
- Tag stable configurations
- Create backup branches before major changes
- Use feature branches for experiments

### 4. Keep It Simple
- Don't over-customize initially
- Add complexity only when needed
- Remove unused configurations

### 5. Security First
- Never commit secrets
- Minimize permissions
- Regular security audits

---

**Previous:** [Secrets & Environment Setup](./Secrets-and-Environment-Setup.md) | **Next:** [Linear ↔ Notion Sync](./Linear-Notion-Sync.md) →
