# Linear↔Notion Sync - Quick Reference

## 🚀 Quick Start

### Manual Triggers

**Linear → Notion Sync**
```bash
gh workflow run linear-to-notion-sync.yml -f issue_id=REP-2 -f sync_type=full
```

**Notion → Linear Sync**
```bash
gh workflow run notion-to-linear-sync.yml -f notion_page_id=abc123 -f create_epic=true
```

## 📋 Required Secrets

Configure in GitHub Settings → Secrets → Actions:

- `LINEAR_API_KEY` - From Linear Settings → API
- `NOTION_API_KEY` - From https://www.notion.so/my-integrations
- `LINEAR_TEAM_ID` - Your Linear team identifier
- `NOTION_SPEC_DATABASE_ID` - Target Notion database ID

## 🔗 Webhooks

### Linear Webhook
```
URL: https://api.github.com/repos/clduab11/repo-skeletor/dispatches
Event Type: linear-webhook
Headers:
  Authorization: Bearer YOUR_GITHUB_PAT
  Accept: application/vnd.github.v3+json
```

### Notion Webhook (via automation tool)
```
URL: https://api.github.com/repos/clduab11/repo-skeletor/dispatches
Event Type: notion-spec-ready
Headers:
  Authorization: Bearer YOUR_GITHUB_PAT
  Accept: application/vnd.github.v3+json
```

## 📖 Documentation

- [WEBHOOK_SETUP.md](WEBHOOK_SETUP.md) - Complete webhook configuration
- [MANUAL_TRIGGER_TESTING.md](MANUAL_TRIGGER_TESTING.md) - Testing guide
- [README.md](../README.md) - Project overview

## 🎯 Workflow Details

### Linear to Notion Sync
- **File**: `.github/workflows/linear-to-notion-sync.yml`
- **Triggers**: `repository_dispatch` (linear-webhook), `workflow_dispatch`
- **Inputs**: 
  - `issue_id` (required) - Linear issue identifier
  - `sync_type` (required) - full | status-only | metadata-only

### Notion to Linear Sync
- **File**: `.github/workflows/notion-to-linear-sync.yml`
- **Triggers**: `repository_dispatch` (notion-spec-ready), `workflow_dispatch`
- **Inputs**: 
  - `notion_page_id` (required) - Notion page ID
  - `create_epic` (required) - Create as epic with sub-issues
  - `linear_project` (optional) - Linear project name

## ✅ Next Steps

1. **Configure Secrets** in GitHub repository settings
2. **Test Manual Triggers** using GitHub Actions UI or CLI
3. **Set Up Webhooks** following WEBHOOK_SETUP.md
4. **Monitor Runs** in GitHub Actions tab

## 🆘 Troubleshooting

**Workflow not appearing?**
- Ensure files are in `.github/workflows/` directory
- Check branch - workflows must be committed to the branch

**Authentication errors?**
- Verify all secrets are configured correctly
- Check API keys are not expired
- Ensure integrations have proper permissions

**Sync failures?**
- Review workflow logs in GitHub Actions
- Verify IDs (issue_id, notion_page_id, etc.) are valid
- Check API rate limits

For detailed troubleshooting, see [MANUAL_TRIGGER_TESTING.md](MANUAL_TRIGGER_TESTING.md#troubleshooting)
