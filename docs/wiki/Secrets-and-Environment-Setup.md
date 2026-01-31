# Secrets & Environment Setup

Complete guide to configuring API keys, secrets, and environment variables for repo-skeletor.

## Overview

repo-skeletor integrates with multiple services, each requiring authentication credentials. This guide covers:
1. **Local environment variables** (`.env` file)
2. **GitHub repository secrets** (for Actions)
3. **How to obtain each API key**
4. **Security best practices**

## Quick Reference

### Required Secrets

| Secret | Used By | Required For |
|--------|---------|--------------|
| `ANTHROPIC_API_KEY` | Claude Code | AI assistance, code review |
| `LINEAR_API_KEY` | Linear sync | Issue tracking integration |
| `NOTION_API_KEY` | Notion sync | Documentation integration |

### Optional but Recommended

| Secret | Used By | Purpose |
|--------|---------|---------|
| `LINEAR_TEAM_ID` | Linear workflows | Team-specific operations |
| `NOTION_SPEC_DATABASE_ID` | Notion workflows | Spec database access |
| `GITHUB_TOKEN` | Continue.dev | Repo operations (auto-provided) |
| `CODECOV_TOKEN` | CI workflow | Code coverage reporting |
| `SNYK_TOKEN` | CI workflow | Security scanning |
| `SLACK_WEBHOOK_URL` | Deploy workflow | Deployment notifications |

### Optional AI/Tools

| Secret | Used By | Purpose |
|--------|---------|---------|
| `GOOGLE_AI_API_KEY` | Continue.dev | Gemini model access |
| `VOYAGE_API_KEY` | Continue.dev | Embeddings & reranking |
| `PERPLEXITY_API_KEY` | Continue.dev | Web search |
| `BRAVE_API_KEY` | MCP servers | Web search |
| `MEM0_API_KEY` | MCP servers | Persistent memory |
| `CONTEXT7_API_KEY` | MCP servers | Library documentation |

---

## Step-by-Step Setup

### 1. Local Environment (`.env`)

Create a `.env` file in your project root:

```bash
cp .env.example .env
```

Edit `.env` with your actual keys:

```bash
# === Required ===
ANTHROPIC_API_KEY=sk-ant-api03-...
LINEAR_API_KEY=lin_api_...
NOTION_API_KEY=secret_...

# === Recommended ===
LINEAR_TEAM_ID=a1b2c3d4-...
NOTION_SPEC_DATABASE_ID=abc123...

# === Optional AI ===
GOOGLE_AI_API_KEY=AIza...
VOYAGE_API_KEY=pa-...
PERPLEXITY_API_KEY=pplx-...
BRAVE_API_KEY=BSA...

# === Optional MCP ===
MEM0_API_KEY=...
CONTEXT7_API_KEY=...

# === Optional Tools ===
CODECOV_TOKEN=...
SNYK_TOKEN=...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# === Deployment (if applicable) ===
VERCEL_TOKEN=...
RAILWAY_TOKEN=...
DATABASE_URL=postgresql://...
```

**Important**: Never commit `.env` to git! Verify it's in `.gitignore`.

---

### 2. GitHub Repository Secrets

Add secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name shown below

#### Required Secrets

**`ANTHROPIC_API_KEY`**
```
Name: ANTHROPIC_API_KEY
Value: sk-ant-api03-...
```

**`LINEAR_API_KEY`**
```
Name: LINEAR_API_KEY
Value: lin_api_...
```

**`NOTION_API_KEY`**
```
Name: NOTION_API_KEY
Value: secret_...
```

#### Optional Secrets

Add these as needed based on your configuration:

- `LINEAR_TEAM_ID`
- `NOTION_SPEC_DATABASE_ID`
- `CODECOV_TOKEN`
- `SNYK_TOKEN`
- `SLACK_WEBHOOK_URL`
- `STAGING_DEPLOY_TOKEN`
- `PRODUCTION_DEPLOY_TOKEN`

---

## Obtaining API Keys

### Anthropic API Key (Claude)

**Required for**: Claude Code GitHub Action, Continue.dev

**Steps**:
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to **API Keys**
4. Click **Create Key**
5. Name it (e.g., "repo-skeletor")
6. Copy the key (starts with `sk-ant-`)

**Format**: `sk-ant-api03-...`

**Pricing**: Pay-as-you-go, ~$3-15 per million tokens

**Tips**:
- Set usage limits in the console
- Monitor usage regularly
- Use different keys for dev/prod

---

### Linear API Key

**Required for**: Linear ↔ Notion sync, Linear issue creation

**Steps**:
1. Go to [linear.app/settings/api](https://linear.app/settings/api)
2. Click **Personal API keys**
3. Click **Create key**
4. Name it (e.g., "repo-skeletor-sync")
5. Copy the key (starts with `lin_api_`)

**Format**: `lin_api_...`

**Permissions**: Full access (required for creating/updating issues)

#### Getting Linear Team ID

**Option A: From URL**
```
https://linear.app/YOUR_WORKSPACE/team/PAR/...
                                      ^^^
                                   Team Key

Your team ID is visible in Linear URLs.
```

**Option B: Via API**
```bash
curl https://api.linear.app/graphql \
  -H "Authorization: YOUR_LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ teams { nodes { id name key } } }"}'
```

**Format**: UUID like `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

---

### Notion API Key

**Required for**: Notion ↔ Linear sync, spec parsing

**Steps**:
1. Go to [www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **+ New integration**
3. Fill in details:
   - Name: "repo-skeletor"
   - Associated workspace: Your workspace
   - Type: Internal
4. Click **Submit**
5. Copy the **Internal Integration Token**

**Format**: `secret_...`

**Capabilities needed**:
- ✅ Read content
- ✅ Update content
- ✅ Insert content

#### Connecting Integration to Pages/Databases

After creating the integration, you must explicitly grant it access:

1. Open your Notion page or database
2. Click **⋯** (three dots) → **Add connections**
3. Search for your integration name
4. Select it to grant access

#### Getting Notion Database ID

**From URL**:
```
https://notion.so/workspace/abc123def456?v=...
                          ^^^^^^^^^^^^
                          Database ID
```

**From Share Menu**:
1. Open database
2. Click **Share**
3. Copy link
4. Extract the 32-character ID

**Format**: `abc123def456...` (32 hex characters, no dashes)

#### Getting Notion Page ID

**From URL**:
```
https://notion.so/Page-Title-abc123def456
                             ^^^^^^^^^^^^
                             Page ID
```

**Format**: Same as database ID format

---

### GitHub Token

**Required for**: Continue.dev GitHub operations

**For GitHub Actions**: Automatically provided as `${{ secrets.GITHUB_TOKEN }}`

**For local development**:
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **Generate new token** → **Generate new token (classic)**
3. Name: "repo-skeletor-local"
4. Scopes:
   - ✅ `repo` (full repository access)
   - ✅ `workflow` (update workflows)
   - ✅ `read:org` (read org data)
5. Click **Generate token**
6. Copy immediately (can't be viewed again)

**Format**: `ghp_...`

---

### Optional: Google AI API Key (Gemini)

**Used for**: Gemini models in Continue.dev

**Steps**:
1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Click **Create API key**
3. Select project or create new
4. Copy the key

**Format**: `AIza...`

---

### Optional: Voyage AI API Key

**Used for**: Embeddings and reranking in Continue.dev

**Steps**:
1. Go to [dash.voyageai.com](https://dash.voyageai.com)
2. Sign up or log in
3. Navigate to **API Keys**
4. Create new key
5. Copy the key

**Format**: `pa-...`

---

### Optional: Codecov Token

**Used for**: Code coverage reporting in CI

**Steps**:
1. Go to [codecov.io](https://codecov.io)
2. Log in with GitHub
3. Add your repository
4. Copy the upload token

---

### Optional: Snyk Token

**Used for**: Security vulnerability scanning

**Steps**:
1. Go to [snyk.io](https://snyk.io)
2. Sign up or log in
3. Navigate to **Account Settings** → **API Token**
4. Click **Show** and copy

---

### Optional: Slack Webhook URL

**Used for**: Deployment notifications

**Steps**:
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name it and select workspace
4. Click **Incoming Webhooks**
5. Toggle **Activate Incoming Webhooks** to On
6. Click **Add New Webhook to Workspace**
7. Select channel and authorize
8. Copy the webhook URL

**Format**: `https://hooks.slack.com/services/T.../B.../...`

---

## Verification

### Test Local Environment

```bash
# Check .env exists and is not committed
cat .env
git status  # Should not list .env

# Test with a simple script
node -e "require('dotenv').config(); console.log('ANTHROPIC_API_KEY:', process.env.ANTHROPIC_API_KEY?.substring(0, 10) + '...')"
```

### Test GitHub Secrets

Create a test workflow:

```yaml
name: Test Secrets
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Check secrets
        run: |
          echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:10}..."
          echo "LINEAR_API_KEY: ${LINEAR_API_KEY:0:10}..."
          echo "NOTION_API_KEY: ${NOTION_API_KEY:0:10}..."
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
          NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
```

### Test API Connections

**Test Claude API**:
```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

**Test Linear API**:
```bash
curl https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { name email } }"}'
```

**Test Notion API**:
```bash
curl https://api.notion.com/v1/users/me \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28"
```

---

## Security Best Practices

### ✅ Do's

1. **Use `.env` for local development**
   - Never commit `.env` files
   - Use `.env.example` as template

2. **Use GitHub Secrets for workflows**
   - Never hardcode secrets in YAML
   - Use `${{ secrets.SECRET_NAME }}`

3. **Rotate keys periodically**
   - Change keys every 90 days
   - Immediately rotate if exposed

4. **Use minimum required permissions**
   - Linear: Read/write only for sync
   - Notion: Access only needed databases

5. **Monitor usage**
   - Check API dashboards regularly
   - Set up usage alerts

6. **Use environment-specific keys**
   - Different keys for dev/staging/prod
   - Separate testing keys

### ❌ Don'ts

1. **Never commit secrets to git**
   - Check `.gitignore` includes `.env*`
   - Use git-secrets or similar tools

2. **Don't share keys in chat/email**
   - Use secure secret sharing tools
   - Revoke and regenerate if shared

3. **Don't reuse keys across projects**
   - Create project-specific keys
   - Makes revocation easier

4. **Don't log secrets**
   - Sanitize logs
   - Use `${VAR:0:10}...` in debugging

5. **Don't store in plain text backups**
   - Use encrypted backup solutions
   - Exclude secrets from backups

---

## Troubleshooting

### "Unauthorized" or "Invalid API key"
- Verify key is copied completely
- Check for extra whitespace
- Ensure key hasn't been revoked
- Confirm key has required permissions

### Secrets not available in GitHub Actions
- Check secret name matches exactly (case-sensitive)
- Verify secret is set at repository level (not environment)
- Check workflow has correct permissions

### Environment variables not loading
- Ensure `.env` is in project root
- Check `.env` file permissions
- Use `dotenv` package: `require('dotenv').config()`
- Restart terminal/IDE after setting

### "Rate limit exceeded"
- Check API usage in provider dashboard
- Implement exponential backoff
- Add delays between requests
- Upgrade plan if needed

---

## Environment Templates

### Minimal Setup (just AI assistance)
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### Full Integration Setup
```bash
# AI
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=AIza...
VOYAGE_API_KEY=pa-...

# Integrations
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_ID=a1b2c3d4-...
NOTION_API_KEY=secret_...
NOTION_SPEC_DATABASE_ID=abc123...
GITHUB_TOKEN=ghp_...

# Optional
CODECOV_TOKEN=...
SNYK_TOKEN=...
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

---

**Previous:** [GitHub Actions Architecture](./GitHub-Actions-Architecture.md) | **Next:** [Customization Guide](./Customization-Guide.md) →
