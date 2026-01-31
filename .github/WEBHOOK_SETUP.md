# Webhook Setup Guide

This guide explains how to configure webhooks for Linear↔Notion sync workflows.

## Prerequisites

1. GitHub Personal Access Token (PAT) with `repo` scope
2. Linear API key (for Linear webhook)
3. Notion integration token (for Notion webhook)

## Linear → Notion Sync Webhook

This webhook triggers the `linear-to-notion-sync.yml` workflow when Linear issues are updated.

### Setup Steps

1. **Create GitHub Personal Access Token**
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token with `repo` scope
   - Save the token securely

2. **Configure Linear Webhook**
   - Navigate to Linear Settings → API → Webhooks
   - Click "New webhook"
   - Configure the webhook:
     ```
     URL: https://api.github.com/repos/clduab11/repo-skeletor/dispatches
     ```

3. **Add Headers**
   ```
   Authorization: Bearer YOUR_GITHUB_PAT
   Accept: application/vnd.github.v3+json
   Content-Type: application/json
   ```

4. **Set Events**
   - Select: Issue created, Issue updated, Issue deleted

5. **Configure Payload** (if custom payload is supported)
   ```json
   {
     "event_type": "linear-webhook",
     "client_payload": {
       "issue_id": "{{issue.identifier}}",
       "action": "{{action}}"
     }
   }
   ```

### Alternative: Use GitHub Actions API Directly

If Linear doesn't support custom payloads, use a middleware service (Zapier, n8n, or custom):

```bash
curl -X POST \
  https://api.github.com/repos/clduab11/repo-skeletor/dispatches \
  -H "Authorization: Bearer YOUR_GITHUB_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{
    "event_type": "linear-webhook",
    "client_payload": {
      "issue_id": "PAR-123",
      "action": "full"
    }
  }'
```

## Notion → Linear Sync Webhook

This webhook triggers the `notion-to-linear-sync.yml` workflow when Notion pages are ready.

### Setup Steps

Since Notion doesn't have native webhooks, use one of these approaches:

#### Option 1: Automation Tool (Recommended)

Use Zapier, n8n, or Make.com:

1. **Trigger**: Notion - Database Item Created/Updated
2. **Filter**: Check if page meets criteria (e.g., status = "Ready for Linear")
3. **Action**: Webhooks - POST
   ```
   URL: https://api.github.com/repos/clduab11/repo-skeletor/dispatches
   Headers:
     Authorization: Bearer YOUR_GITHUB_PAT
     Accept: application/vnd.github.v3+json
   Body:
   {
     "event_type": "notion-spec-ready",
     "client_payload": {
       "notion_page_id": "{{notion_page_id}}"
     }
   }
   ```

#### Option 2: Custom Service

Create a simple webhook server:

```javascript
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

app.post('/notion-webhook', async (req, res) => {
  const { page_id } = req.body;
  
  await axios.post(
    'https://api.github.com/repos/clduab11/repo-skeletor/dispatches',
    {
      event_type: 'notion-spec-ready',
      client_payload: { notion_page_id: page_id }
    },
    {
      headers: {
        Authorization: `Bearer ${process.env.GITHUB_PAT}`,
        Accept: 'application/vnd.github.v3+json'
      }
    }
  );
  
  res.status(200).send('OK');
});

app.listen(3000);
```

## Manual Trigger Testing

Both workflows support manual triggering via GitHub Actions UI or GitHub CLI.

### Linear → Notion Sync

**Via GitHub UI**:
1. Go to Actions → Linear to Notion Sync
2. Click "Run workflow"
3. Enter issue ID (e.g., `PAR-123`)
4. Select sync type: `full`, `status-only`, or `metadata-only`

**Via GitHub CLI**:
```bash
gh workflow run linear-to-notion-sync.yml \
  -f issue_id=PAR-123 \
  -f sync_type=full
```

### Notion → Linear Sync

**Via GitHub UI**:
1. Go to Actions → Notion to Linear Sync
2. Click "Run workflow"
3. Enter Notion page ID
4. Choose whether to create an epic
5. Optionally specify Linear project name

**Via GitHub CLI**:
```bash
gh workflow run notion-to-linear-sync.yml \
  -f notion_page_id=abc123def456 \
  -f create_epic=true \
  -f linear_project="Q1 Features"
```

## Required GitHub Secrets

Ensure these secrets are configured in GitHub Settings → Secrets → Actions:

| Secret | Description | Used By |
|--------|-------------|---------|
| `LINEAR_API_KEY` | Linear API key | Both workflows |
| `NOTION_API_KEY` | Notion integration token | Both workflows |
| `NOTION_SPEC_DATABASE_ID` | Notion database ID for specs | Linear → Notion |
| `LINEAR_TEAM_ID` | Linear team ID | Notion → Linear |

## Troubleshooting

### Workflow Not Triggering

1. **Check webhook delivery** in Linear/GitHub settings
2. **Verify GitHub PAT** has correct permissions
3. **Check repository dispatch** event type matches exactly
4. **Review workflow run logs** in GitHub Actions

### Authentication Errors

1. **Verify API keys** are valid and not expired
2. **Check secret names** match exactly (case-sensitive)
3. **Ensure integrations** have necessary permissions

### Sync Issues

1. **Check database IDs** are correct
2. **Verify property names** in Notion database match workflow expectations
3. **Review Linear team settings** and permissions

## Security Best Practices

1. **Use separate API keys** for different environments
2. **Rotate tokens regularly**
3. **Never commit secrets** to repository
4. **Use webhook signatures** when available
5. **Implement rate limiting** for webhook endpoints
6. **Monitor failed runs** and set up alerts

## Support

For issues or questions:
- Check GitHub Actions logs
- Review Linear/Notion API documentation
- Create an issue in this repository
