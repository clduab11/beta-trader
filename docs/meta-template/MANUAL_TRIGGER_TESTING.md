# Manual Trigger Testing Guide

This guide provides instructions for testing the Linear↔Notion sync workflows using manual triggers.

## Prerequisites

- GitHub account with access to the repo-skeletor repository
- GitHub CLI (`gh`) installed (optional, for CLI testing)
- Valid Linear issue ID for testing (e.g., `PAR-123`, `REP-2`)
- Valid Notion page ID for testing

## Test 1: Linear → Notion Sync

### Via GitHub Web UI

1. Navigate to the repository: https://github.com/clduab11/repo-skeletor
2. Click on the **Actions** tab
3. Select **Linear to Notion Sync** from the workflows list (left sidebar)
4. Click **Run workflow** button (top right)
5. Fill in the form:
   - **Use workflow from**: `copilot/deploy-linear-notion-sync-rep-2` (or your branch)
   - **issue_id**: Enter a valid Linear issue ID (e.g., `REP-2`, `PAR-123`)
   - **sync_type**: Select one of:
     - `full` - Syncs all issue data
     - `status-only` - Syncs only status changes
     - `metadata-only` - Syncs metadata without content
6. Click **Run workflow**
7. Refresh the page to see the workflow run appear
8. Click on the workflow run to view logs

### Via GitHub CLI

```bash
# Install GitHub CLI if needed
# macOS: brew install gh
# Linux: See https://cli.github.com/manual/installation

# Authenticate
gh auth login

# Run the workflow
gh workflow run linear-to-notion-sync.yml \
  -f issue_id=REP-2 \
  -f sync_type=full \
  --repo clduab11/repo-skeletor

# View the workflow run
gh run list --workflow=linear-to-notion-sync.yml --limit 1

# Watch the workflow run (follow logs in real-time)
gh run watch
```

### Expected Results

✅ **Success Indicators**:
- Workflow completes without errors
- Job summary shows:
  - Issue ID that was synced
  - Action performed (full/status-only/metadata-only)
  - Status: success
- In Notion database:
  - Page exists with Linear ID matching the issue identifier
  - Properties are populated (Status, Priority, Assignee, etc.)
  - Last Synced timestamp is updated

❌ **Potential Issues**:
- **Authentication Error**: Check `LINEAR_API_KEY` and `NOTION_API_KEY` secrets
- **Issue Not Found**: Verify the issue ID exists in Linear
- **Database Not Found**: Check `NOTION_SPEC_DATABASE_ID` secret
- **Property Mismatch**: Ensure Notion database has required properties

## Test 2: Notion → Linear Sync

### Via GitHub Web UI

1. Navigate to the repository: https://github.com/clduab11/repo-skeletor
2. Click on the **Actions** tab
3. Select **Notion to Linear Sync** from the workflows list
4. Click **Run workflow** button
5. Fill in the form:
   - **Use workflow from**: `copilot/deploy-linear-notion-sync-rep-2` (or your branch)
   - **notion_page_id**: Enter a Notion page ID (32-character hex string)
   - **create_epic**: Check to create as epic with sub-issues, uncheck for single issue
   - **linear_project** (optional): Enter a Linear project name
6. Click **Run workflow**
7. Click on the workflow run to view logs

### Via GitHub CLI

```bash
# Run with epic creation
gh workflow run notion-to-linear-sync.yml \
  -f notion_page_id=abc123def456789012345678901234 \
  -f create_epic=true \
  -f linear_project="Q1 Features" \
  --repo clduab11/repo-skeletor

# Run without epic (single issue)
gh workflow run notion-to-linear-sync.yml \
  -f notion_page_id=abc123def456789012345678901234 \
  -f create_epic=false \
  --repo clduab11/repo-skeletor

# View results
gh run list --workflow=notion-to-linear-sync.yml --limit 1
gh run watch
```

### Expected Results

✅ **Success Indicators**:
- Workflow completes both jobs (parse-spec and create-issues)
- Job summary displays:
  - Created issues in JSON format
  - Epic ID (if create_epic=true)
- In Linear:
  - Epic issue created with title `[Spec] {Title}`
  - Sub-issues created and linked to epic
  - Issues are in "Backlog" state
  - Issues link back to Notion spec
- In Notion:
  - Page updated with Linear Epic URL
  - Linear ID field populated
  - Status changed to "In Linear"
  - Callout block added with Linear link

❌ **Potential Issues**:
- **Page Not Found**: Verify Notion page ID is correct
- **Team Not Found**: Check `LINEAR_TEAM_ID` secret
- **Permission Denied**: Ensure Notion integration has access to the page
- **Parsing Errors**: Check Notion page structure (should have title, headers, tasks)

## Test 3: Webhook Trigger Simulation

### Linear Webhook Simulation

```bash
# Replace YOUR_GITHUB_PAT with your Personal Access Token
curl -X POST \
  https://api.github.com/repos/clduab11/repo-skeletor/dispatches \
  -H "Authorization: Bearer YOUR_GITHUB_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "linear-webhook",
    "client_payload": {
      "issue_id": "REP-2",
      "action": "full"
    }
  }'
```

### Notion Webhook Simulation

```bash
curl -X POST \
  https://api.github.com/repos/clduab11/repo-skeletor/dispatches \
  -H "Authorization: Bearer YOUR_GITHUB_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "notion-spec-ready",
    "client_payload": {
      "notion_page_id": "abc123def456789012345678901234"
    }
  }'
```

### Expected Results

- Workflow triggers automatically
- No manual intervention required
- Same results as manual trigger tests

## Troubleshooting

### Workflow Not Appearing

- **Ensure workflows are committed** to the repository
- **Check branch**: Workflows must be on the branch you're viewing
- **Wait for sync**: GitHub may take a few seconds to index new workflows

### Permission Errors

```
Error: Resource not accessible by integration
```

**Solution**: Check that secrets are properly configured:
1. Go to Settings → Secrets and variables → Actions
2. Verify all required secrets exist and are not expired

### Invalid Workflow File

```
Error: Invalid workflow file
```

**Solution**: Validate YAML syntax:
```bash
# Using Python
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/linear-to-notion-sync.yml'))"

# Using yamllint (if installed)
yamllint .github/workflows/linear-to-notion-sync.yml
```

### Job Failures

1. **View detailed logs** in GitHub Actions UI
2. **Check step-by-step output** for specific errors
3. **Verify API credentials** are correct
4. **Check rate limits** on Linear/Notion APIs

## Test Checklist

After running tests, verify:

- [ ] **Linear → Notion Sync**
  - [ ] Workflow appears in Actions tab
  - [ ] Manual trigger works via UI
  - [ ] Manual trigger works via CLI
  - [ ] Workflow completes successfully
  - [ ] Data appears correctly in Notion
  - [ ] Webhook simulation works

- [ ] **Notion → Linear Sync**
  - [ ] Workflow appears in Actions tab
  - [ ] Manual trigger works via UI
  - [ ] Manual trigger works via CLI
  - [ ] Epic creation works
  - [ ] Sub-issues are created correctly
  - [ ] Notion page is updated with Linear link
  - [ ] Webhook simulation works

- [ ] **General**
  - [ ] All secrets are configured
  - [ ] Workflow files are valid YAML
  - [ ] Documentation is complete and accurate
  - [ ] No sensitive data in workflow files

## Next Steps

After successful testing:

1. **Configure real webhooks** in Linear and Notion (see WEBHOOK_SETUP.md)
2. **Set up monitoring** for failed workflow runs
3. **Create alerts** for authentication issues
4. **Document any custom configurations** for your team

## Support

If you encounter issues:
- Check [WEBHOOK_SETUP.md](WEBHOOK_SETUP.md) for webhook configuration
- Review GitHub Actions logs for detailed error messages
- Verify all secrets are correctly configured
- Ensure Linear and Notion APIs are accessible
