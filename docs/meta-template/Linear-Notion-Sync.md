# Linear ↔ Notion Sync Configuration

Complete guide to setting up bidirectional synchronization between Linear and Notion.

## Overview

repo-skeletor provides two-way sync between Linear and Notion:
- **Linear → Notion**: Sync Linear issues to Notion database
- **Notion → Linear**: Convert Notion specs to Linear epics with sub-issues

## Architecture

```
┌──────────────┐                    ┌──────────────┐
│   Linear     │                    │   Notion     │
│   Issues     │                    │   Database   │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │ Webhook                           │ Manual/Schedule
       ▼                                   ▼
┌────────────────────────────────────────────────┐
│         GitHub Actions Workflows               │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │ linear-to-notion │  │ notion-to-linear │  │
│  │    -sync.yml     │  │      .yml        │  │
│  └──────────────────┘  └──────────────────┘  │
└────────────────────────────────────────────────┘
```

---

## Part 1: Linear → Notion Sync

Automatically sync Linear issues to a Notion database.

### Prerequisites

1. **Notion Integration** created ([how to](./Secrets-and-Environment-Setup.md#notion-api-key))
2. **Notion Database** set up for Linear issues
3. **Linear API Key** with read permissions
4. **GitHub Secrets** configured

### Step 1: Create Notion Database

1. Open Notion and create a new database
2. Add the following properties:

| Property Name | Type | Description |
|--------------|------|-------------|
| Name | Title | Issue title |
| Linear ID | Rich Text | Issue identifier (PAR-123) |
| Status | Select | Issue status |
| Priority | Select | Issue priority |
| Assignee | Rich Text | Assigned person |
| Due Date | Date | Due date |
| Estimate | Number | Story points/estimate |
| Project | Rich Text | Project name |
| Labels | Multi-select | Unified labels (see Labels-and-Sync-Strategy.md) |
| Linear URL | URL | Link to Linear issue |
| Last Synced | Date | Last sync timestamp |

3. Add Status options:
   - Not Started
   - In Progress
   - Done
   - Canceled
   - Backlog

4. Add Priority options:
   - No Priority
   - Urgent
   - High
   - Medium
   - Low

5. **Share the database** with your Notion integration:
   - Click **⋯** → **Add connections**
   - Select your integration
   - Click **Confirm**

### Step 2: Configure GitHub Secrets

Add these secrets to your repository:

```
NOTION_API_KEY=secret_...
NOTION_SPEC_DATABASE_ID=abc123def456...
LINEAR_API_KEY=lin_api_...
```

Get the database ID from the URL:
```
https://notion.so/workspace/DATABASE_ID?v=...
                         ^^^^^^^^^^^
```

### Step 3: Set Up Linear Webhook

#### Option A: Using Linear Webhooks (Recommended)

1. Go to Linear workspace settings
2. Navigate to **API** → **Webhooks**
3. Click **New webhook**
4. Configure:
   ```
   URL: https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/dispatches
   Secret: YOUR_WEBHOOK_SECRET (generate a secure token)
   ```

5. Select events to trigger:
   - ✅ Issue created
   - ✅ Issue updated
   - ✅ Issue status changed

6. Add authentication header:
   ```
   Authorization: Bearer YOUR_GITHUB_TOKEN
   ```

7. Set custom payload:
   ```json
   {
     "event_type": "linear-webhook",
     "client_payload": {
       "issue_id": "{{issue.identifier}}",
       "action": "{{action}}"
     }
   }
   ```

#### Option B: Using GitHub Webhook Proxy

If you need more control, use a webhook proxy:

1. Deploy a simple proxy (e.g., on Vercel/Netlify):
   ```javascript
   // api/linear-webhook.js
   export default async function handler(req, res) {
     const { data } = req.body;
     
     // Forward to GitHub
     await fetch(`https://api.github.com/repos/${REPO}/dispatches`, {
       method: 'POST',
       headers: {
         'Authorization': `Bearer ${GITHUB_TOKEN}`,
         'Content-Type': 'application/json'
       },
       body: JSON.stringify({
         event_type: 'linear-webhook',
         client_payload: {
           issue_id: data.identifier,
           action: data.action
         }
       })
     });
     
     res.status(200).json({ success: true });
   }
   ```

2. Use this proxy URL in Linear webhook configuration

### Step 4: Test the Sync

#### Manual Test

1. Go to your repository's **Actions** tab
2. Select **Linear to Notion Sync** workflow
3. Click **Run workflow**
4. Enter a Linear issue ID (e.g., `PAR-123`)
5. Select **full** sync type
6. Click **Run workflow**

#### Webhook Test

1. Create or update an issue in Linear
2. Check GitHub Actions for the triggered workflow
3. Verify the issue appears/updates in Notion

### Field Mappings

#### Linear → Notion Property Mapping

| Linear Field | Notion Property | Transformation |
|--------------|----------------|----------------|
| `identifier` | Linear ID | Direct |
| `title` | Name | Direct |
| `state.type` | Status | Mapped via stateMap |
| `priority` | Priority | Mapped via priorityMap |
| `assignee.name` | Assignee | Direct |
| `dueDate` | Due Date | ISO date format |
| `estimate` | Estimate | Number |
| `project.name` | Project | Direct |
| `url` | Linear URL | Direct |
| Current timestamp | Last Synced | Auto-generated |

#### Status Mapping

```javascript
const stateMap = {
  'unstarted': 'Not Started',
  'started': 'In Progress',
  'completed': 'Done',
  'canceled': 'Canceled',
  'backlog': 'Backlog'
};
```

#### Priority Mapping

```javascript
const priorityMap = {
  0: 'No Priority',
  1: 'Urgent',
  2: 'High',
  3: 'Medium',
  4: 'Low'
};
```

### Customizing Field Mappings

Edit `.github/workflows/linear-to-notion-sync.yml`:

```yaml
const properties = {
  'Name': {
    title: [{ text: { content: issueData.title } }]
  },
  'Linear ID': {
    rich_text: [{ text: { content: issueData.identifier } }]
  },
  
  // Add custom fields
  'Sprint': {
    select: { name: issueData.cycle?.name || 'No Sprint' }
  },
  'Labels': {
    multi_select: issueData.labels.map(l => ({ name: l.name }))
  },
  'Team': {
    select: { name: issueData.team?.name || 'Engineering' }
  }
};
```

---

## Part 2: Notion → Linear Sync

Convert Notion spec documents into Linear epics and sub-issues.

### Prerequisites

1. Notion integration connected to your workspace
2. Linear API key with write permissions
3. Linear team ID

### Step 1: Create Notion Spec Template

1. Create a new Notion page or use an existing one
2. Structure your spec:

```markdown
# Feature Name

## Overview
Brief description of the feature...

## Requirements
What needs to be built...

## Tasks
- [ ] Design database schema
- [ ] Implement API endpoints (estimate: 5h)
- [ ] Create UI components (estimate: 3h)
- [ ] Write tests
- [ ] Update documentation

## Technical Details
Implementation notes...

## Success Criteria
How to measure success...
```

3. Share the page with your integration

### Step 2: Run Conversion Workflow

#### Manual Trigger

1. Get the Notion page ID from URL:
   ```
   https://notion.so/Feature-Name-PAGE_ID
   ```

2. Go to **Actions** → **Notion Spec to Linear**
3. Click **Run workflow**
4. Enter:
   - **notion_page_id**: Your page ID
   - **create_epic**: `true` (creates epic + sub-issues)
   - **linear_project**: Project name (optional)

#### Programmatic Trigger

```bash
# Using GitHub CLI
gh workflow run notion-spec-to-linear.yml \
  -f notion_page_id=abc123def456 \
  -f create_epic=true \
  -f linear_project="Q1 Features"

# Using curl
curl -X POST \
  https://api.github.com/repos/USERNAME/REPO/actions/workflows/notion-spec-to-linear.yml/dispatches \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -d '{
    "ref": "main",
    "inputs": {
      "notion_page_id": "abc123def456",
      "create_epic": "true",
      "linear_project": "Q1 Features"
    }
  }'
```

### How It Works

1. **Parse Notion Page**:
   - Extracts title and description
   - Identifies sections from headings
   - Finds tasks in:
     - Todo items (`- [ ]`)
     - Bulleted lists with patterns
     - Task blocks

2. **Create Linear Issues**:
   - Creates parent epic with spec overview
   - Creates sub-issue for each task
   - Links sub-issues to epic
   - Assigns to project (if specified)

3. **Update Notion**:
   - Adds Linear epic link to page properties
   - Updates status to "In Linear"
   - Adds callout with issue links

### Task Parsing Rules

The workflow extracts tasks from:

**Todo items**:
```markdown
- [ ] Task description
- [x] Completed task (skipped)
```

**Bulleted lists with estimates**:
```markdown
- Implement authentication (estimate: 5h)
- Add error handling (estimate: 2h)
```

**Pattern matching**:
- Extracts task title
- Extracts estimate from `(estimate: Xh)` pattern
- Groups by section heading

### Customizing Task Parsing

Edit `.github/workflows/notion-spec-to-linear.yml`:

```javascript
// Custom task extraction logic
for (const block of blocks.results) {
  // Handle custom block types
  if (block.type === 'callout' && block.callout.icon.emoji === '🎯') {
    // Extract priority tasks
    tasks.push({
      title: block.callout.rich_text[0].plain_text,
      priority: 2,  // High priority
      section: currentSection
    });
  }
  
  // Custom pattern matching
  if (block.type === 'paragraph') {
    const text = block.paragraph.rich_text[0]?.plain_text || '';
    // Match "TODO: Description (3 days)"
    const match = text.match(/TODO:\s*(.+?)\s*\((\d+)\s*days?\)/i);
    if (match) {
      tasks.push({
        title: match[1],
        estimate: parseInt(match[2]) * 8,  // Convert days to hours
        section: currentSection
      });
    }
  }
}
```

---

## Advanced Configurations

### Bidirectional Sync

To keep both systems in sync continuously:

1. Set up Linear → Notion webhook (automatic)
2. Add Notion → Linear on a schedule:

```yaml
# Add to notion-spec-to-linear.yml
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  repository_dispatch:
    types: [notion-spec-ready]
```

### Selective Sync

Sync only specific Linear issues:

```yaml
# In linear-to-notion-sync.yml
- name: Filter Issues
  if: contains(issueData.labels, 'sync-to-notion')
  # Only sync issues with 'sync-to-notion' label
```

### Custom Notion Views

Create filtered views in Notion:

1. **By Status**:
   - Filter: Status = "In Progress"
   - Sort: Priority (descending)

2. **By Project**:
   - Filter: Project = "Q1 Features"
   - Group by: Status

3. **By Assignee**:
   - Filter: Assignee = "Your Name"
   - Sort: Due Date (ascending)

### Sync Status Monitoring

Add monitoring to workflows:

```yaml
- name: Notify on Sync Failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "⚠️ Linear-Notion sync failed for ${{ steps.extract.outputs.issue_id }}"
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Troubleshooting

### Linear → Notion Issues

**Issue not syncing**:
- Verify webhook is configured correctly
- Check GitHub Actions logs
- Ensure Notion integration has database access
- Verify secret names match exactly

**Wrong status mapping**:
- Check Linear state type matches `stateMap`
- Ensure Notion Select options exist
- Update mapping in workflow file

**Missing fields**:
- Verify Notion database has all required properties
- Check property names match exactly (case-sensitive)
- Review field mapping in workflow

### Notion → Linear Issues

**Tasks not extracted**:
- Check task format (use `- [ ]` or patterns)
- Verify block types are supported
- Check workflow logs for parsing errors

**Epic not created**:
- Verify `create_epic` is `true`
- Check Linear API permissions
- Ensure Linear team ID is correct

**Notion not updated**:
- Verify integration has write access
- Check page is shared with integration
- Review Notion API responses in logs

### Common Errors

**"Unauthorized" from Linear**:
```
Solution: Regenerate LINEAR_API_KEY with full permissions
```

**"Object not found" from Notion**:
```
Solution: Share database/page with integration
```

**"Validation failed" on issue creation**:
```
Solution: Check required Linear fields are provided
```

---

## Best Practices

### 1. Database Design
- Keep Notion database schema stable
- Use consistent property names
- Document custom fields

### 2. Workflow Management
- Test workflows on branches first
- Monitor workflow run times
- Set up failure notifications

### 3. Data Consistency
- Regular sync checks
- Handle edge cases (deleted issues, etc.)
- Maintain audit logs

### 4. Performance
- Batch updates when possible
- Use incremental sync
- Implement rate limiting

### 5. Security
- Rotate API keys quarterly
- Use minimum required permissions
- Never log sensitive data

---

## Examples

### Example 1: Simple Issue Sync

Linear issue:
```
Title: Add user authentication
Status: In Progress
Priority: High (2)
Assignee: John Doe
```

Syncs to Notion as:
```
Name: Add user authentication
Linear ID: PAR-123
Status: In Progress
Priority: High
Assignee: John Doe
Linear URL: https://linear.app/.../PAR-123
Last Synced: 2024-01-31T10:30:00Z
```

### Example 2: Spec to Epic Conversion

Notion spec:
```markdown
# User Authentication System

## Tasks
- [ ] Design database schema
- [ ] Implement JWT authentication (estimate: 5h)
- [ ] Add OAuth providers (estimate: 8h)
- [ ] Write tests
```

Creates in Linear:
```
Epic: [Spec] User Authentication System
├─ Sub-issue: Design database schema
├─ Sub-issue: Implement JWT authentication (5 points)
├─ Sub-issue: Add OAuth providers (8 points)
└─ Sub-issue: Write tests
```

---

**Previous:** [Customization Guide](./Customization-Guide.md) | **Back to Home:** [Wiki Home](./Home.md)
