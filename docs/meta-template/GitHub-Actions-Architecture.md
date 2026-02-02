# GitHub Actions Architecture

Deep dive into the automated workflows powering repo-skeletor.

## Overview

repo-skeletor includes five core GitHub Actions workflows that automate:
- ✅ Continuous Integration (CI)
- 🤖 AI-powered code assistance
- 🚀 Automated deployments
- 🔄 Linear ↔ Notion synchronization
- 📝 Spec to issue conversion

## Workflow Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Push/PR Event          @claude mention       Tag push      │
│       │                      │                    │          │
│       ▼                      ▼                    ▼          │
│  ┌─────────┐          ┌──────────┐         ┌─────────┐     │
│  │ ci.yml  │          │claude.yml│         │deploy.yml│    │
│  └─────────┘          └──────────┘         └─────────┘     │
│       │                      │                    │          │
│       ├─► Lint               ├─► AI Response      ├─► Build │
│       ├─► Test               ├─► Code Review      ├─► Deploy│
│       ├─► Build              └─► Create PR        └─► Release│
│       └─► Security                                           │
│                                                              │
│  Linear Webhook         Manual Trigger                      │
│       │                      │                               │
│       ▼                      ▼                               │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │linear-to-notion  │  │notion-to-linear  │                │
│  │    -sync.yml     │  │    .yml          │                │
│  └──────────────────┘  └──────────────────┘                │
│       │                      │                               │
│       └─► Sync Issue         └─► Create Epic + Sub-issues   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Workflow Details

### 1. CI Workflow (`ci.yml`)

**Purpose**: Ensure code quality on every push and PR.

#### Trigger Conditions
```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

#### Jobs and Flow

```
Lint Job (parallel)
├─ Checkout code
├─ Setup pnpm + Node.js
├─ Install dependencies
├─ Run ESLint
├─ TypeScript type check
└─ Prettier format check

Test Job (parallel, needs: lint)
├─ Checkout code
├─ Setup pnpm + Node.js
├─ Install dependencies
├─ Run unit tests with coverage
└─ Upload coverage to Codecov

Build Job (parallel, needs: lint)
├─ Checkout code
├─ Setup pnpm + Node.js
├─ Install dependencies
├─ Production build
└─ Upload build artifacts

Integration Job (conditional)
├─ Only runs on main branch OR with 'run-integration' label
├─ Checkout code
├─ Setup environment
├─ Run integration tests
└─ Use test secrets

Security Job (parallel)
├─ Checkout code
├─ Setup pnpm
├─ Run pnpm audit
└─ Run Snyk security scan

CI Success Job (needs: [lint, test, build])
└─ Verify all required jobs passed
```

#### Configuration Points

**Concurrency Control:**
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true  # Cancel old runs on new push
```

**Environment Variables:**
```yaml
env:
  NODE_VERSION: "20"
  PNPM_VERSION: "9"
```

**Artifacts:**
- Build output: Retained for 7 days
- Coverage reports: Uploaded to Codecov

#### Customization

**Add/Remove Linting Steps:**
```yaml
- name: Run Custom Linter
  run: pnpm custom-lint
```

**Modify Test Configuration:**
```yaml
- name: Run unit tests
  run: pnpm test:unit --coverage --maxWorkers=4
```

**Add E2E Tests:**
```yaml
e2e:
  name: E2E Tests
  runs-on: ubuntu-latest
  needs: build
  steps:
    - name: Run Playwright tests
      run: pnpm test:e2e
```

---

### 2. Claude Code Workflow (`claude.yml`)

**Purpose**: AI-powered assistance via @claude mentions and automated PR reviews.

#### Trigger Conditions
```yaml
on:
  issue_comment:              # @claude in issue comments
  pull_request_review_comment: # @claude in PR reviews
  issues:                     # Assigned to claude or labeled
  pull_request:               # Auto-review new PRs
```

#### Jobs and Flow

**Job 1: claude-response**
```
Trigger: @claude mention or assignment
├─ Check trigger condition
├─ Checkout repository (full history)
├─ Run Claude Code Action
│  ├─ Parse comment/issue
│  ├─ Execute Claude CLI
│  ├─ Make code changes
│  ├─ Create/update PR
│  └─ Post sticky comment
└─ Update PR status
```

**Job 2: claude-review**
```
Trigger: PR opened or synchronized
├─ Checkout repository
├─ Run Claude Code Review
│  ├─ Analyze diff
│  ├─ Check styleguide adherence
│  ├─ Identify issues
│  └─ Generate review comments
└─ Post review as sticky comment
```

#### Configuration

**Model Settings:**
```yaml
claude_args: |
  --max-turns 15
  --model claude-sonnet-4-20250514
  --allowedTools Edit,Read,Write,Bash,Glob,Grep,WebSearch
```

**Branch Configuration:**
```yaml
branch_prefix: "${{ github.actor }}/"
base_branch: "main"
```

**Permissions Required:**
```yaml
permissions:
  contents: write       # Create/modify files
  pull-requests: write  # Create/update PRs
  issues: write         # Comment on issues
  id-token: write       # OIDC auth
```

#### Usage Examples

**In Issue Comments:**
```
@claude Add error handling to the user authentication module
@claude Review this PR for security vulnerabilities
@claude Can you fix the failing test in user-service.test.ts?
```

**Auto-Review Prompt:**
The workflow automatically reviews PRs using:
```yaml
prompt: |
  Review this PR for:
  1. Code quality and adherence to .gemini/styleguide.md
  2. Security vulnerabilities
  3. Performance implications
  4. Test coverage
  5. Documentation completeness
```

---

### 3. Deployment Workflow (`deploy.yml`)

**Purpose**: Automated deployments to staging and production environments.

#### Trigger Conditions
```yaml
on:
  push:
    branches: [main]        # Auto-deploy to staging
    tags: ["v*.*.*"]        # Auto-deploy to production on tags
  workflow_dispatch:        # Manual deployment
    inputs:
      environment: staging | production
      skip_tests: boolean
```

#### Jobs and Flow

```
Setup Job
├─ Determine target environment
│  ├─ workflow_dispatch → use input
│  ├─ tag push → production
│  └─ main push → staging
└─ Set version
   ├─ tag → v1.2.3
   └─ commit → sha-abc12345

Build Job (needs: setup)
├─ Checkout code
├─ Setup environment
├─ Install dependencies
├─ Build for target environment
└─ Upload artifacts

Deploy Staging (needs: [setup, build])
├─ Condition: environment == 'staging'
├─ Download build artifacts
├─ Deploy to staging
└─ Notify via Slack

Deploy Production (needs: [setup, build])
├─ Condition: environment == 'production'
├─ Download build artifacts
├─ Deploy to production
├─ Create GitHub Release
└─ Notify via Slack
```

#### Environment Configuration

**Staging:**
```yaml
environment:
  name: staging
  url: https://staging.{{PROJECT_DOMAIN}}
```

**Production:**
```yaml
environment:
  name: production
  url: https://{{PROJECT_DOMAIN}}
```

#### Customization

**Add Deployment Provider:**

For Vercel:
```yaml
- name: Deploy to Vercel
  run: vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

For AWS:
```yaml
- name: Deploy to AWS
  uses: aws-actions/aws-cloudformation-github-deploy@v1
  with:
    name: my-stack
    template: infrastructure/cloudformation.yml
```

For Railway:
```yaml
- name: Deploy to Railway
  run: |
    railway up --service ${{ secrets.RAILWAY_SERVICE }}
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

---

### 4. Linear to Notion Sync (`linear-to-notion-sync.yml`)

**Purpose**: Keep Linear issues synchronized with Notion database.

#### Trigger Conditions
```yaml
on:
  repository_dispatch:
    types: [linear-webhook]   # Webhook from Linear
  workflow_dispatch:          # Manual sync
    inputs:
      issue_id: string        # e.g., PAR-123
      sync_type: full | status-only | metadata-only
```

#### Data Flow

```
Linear Webhook OR Manual Trigger
       │
       ▼
Extract Issue Data
├─ issue_id (PAR-123)
├─ action (update/create)
└─ sync_type
       │
       ▼
Fetch from Linear API
├─ Issue details
├─ State information
├─ Assignee data
├─ Project info
└─ Labels
       │
       ▼
Map to Notion Fields
├─ Title → Name property
├─ Status → Select property
├─ Priority → Select property
├─ Assignee → Text property
├─ Due Date → Date property
└─ Estimate → Number property
       │
       ▼
Search/Create in Notion
├─ Query by Linear ID
├─ Update if exists
└─ Create if new
       │
       ▼
Post Summary
```

#### Field Mappings

**Linear → Notion:**

| Linear Field | Notion Property | Type |
|--------------|----------------|------|
| `identifier` | Linear ID | Rich Text |
| `title` | Name | Title |
| `state.type` | Status | Select |
| `priority` | Priority | Select |
| `assignee.name` | Assignee | Rich Text |
| `dueDate` | Due Date | Date |
| `estimate` | Estimate | Number |
| `project.name` | Project | Rich Text |
| `url` | Linear URL | URL |

**State Mappings:**
```javascript
{
  'unstarted': 'Not Started',
  'started': 'In Progress',
  'completed': 'Done',
  'canceled': 'Canceled',
  'backlog': 'Backlog'
}
```

**Priority Mappings:**
```javascript
{
  0: 'No Priority',
  1: 'Urgent',
  2: 'High',
  3: 'Medium',
  4: 'Low'
}
```

#### Setup Requirements

See [Linear ↔ Notion Sync Configuration](./Linear-Notion-Sync.md) for webhook setup.

---

### 5. Notion to Linear Workflow (`notion-spec-to-linear.yml`)

**Purpose**: Convert Notion spec documents into Linear epics with sub-issues.

#### Trigger Conditions
```yaml
on:
  repository_dispatch:
    types: [notion-spec-ready]
  workflow_dispatch:
    inputs:
      notion_page_id: string
      create_epic: boolean
      linear_project: string (optional)
```

#### Jobs and Flow

```
Parse Spec Job
├─ Fetch Notion page
├─ Extract title
├─ Parse content blocks
│  ├─ Headings → Sections
│  ├─ Paragraphs → Description
│  ├─ Todo items → Tasks
│  └─ Lists → Tasks (with estimates)
└─ Output: spec_data, tasks[]

Create Issues Job
├─ Initialize Linear client
├─ Find team and project
├─ If create_epic:
│  ├─ Create parent epic
│  └─ For each task:
│     └─ Create sub-issue
└─ Else:
   └─ Create single issue
   
Update Notion Job
├─ Add Linear link to Notion
├─ Set status to "In Linear"
└─ Add callout with epic ID
```

#### Task Parsing

**Supported formats:**

```markdown
## Section Name

- [ ] Task 1
- [ ] Task 2 (estimate: 3h)

Todo items and bullet points are extracted as tasks.
```

**Extracted data per task:**
```javascript
{
  title: "Task description",
  section: "Section Name",
  estimate: 3,  // from (estimate: 3h) pattern
  completed: false
}
```

---

## Workflow Interactions

### CI + Claude Integration
```
Developer creates PR
       │
       ├─► CI workflow runs
       │   ├─ Lint
       │   ├─ Test
       │   └─ Build
       │
       └─► Claude auto-reviews
           ├─ Analyzes changes
           ├─ Checks styleguide
           └─ Posts review comments
                  │
                  ▼
           Developer sees:
           ├─ CI status ✅/❌
           └─ Claude review 🤖
```

### Linear → Notion → Linear Flow
```
1. Create spec in Notion
       │
       ▼
2. Trigger notion-spec-to-linear
       │
       ├─► Parse spec
       ├─► Create Linear epic + sub-issues
       └─► Update Notion with Linear links
              │
              ▼
3. Work on Linear issues
       │
       ▼
4. Linear webhook fires on updates
       │
       ▼
5. linear-to-notion-sync runs
       │
       └─► Updates Notion database
              │
              ▼
       Notion stays synchronized ✅
```

---

## Best Practices

### 1. Workflow Organization
- Keep workflows focused on single responsibilities
- Use job dependencies to create clear execution flow
- Leverage workflow reusability with `workflow_call`

### 2. Security
- Never hardcode secrets in workflow files
- Use environment protection rules for production
- Limit workflow permissions to minimum required

### 3. Performance
- Use concurrency controls to cancel outdated runs
- Cache dependencies (pnpm, npm, pip)
- Parallelize independent jobs
- Set appropriate timeouts

### 4. Debugging
- Use `workflow_dispatch` for manual testing
- Add `echo` statements for visibility
- Use `$GITHUB_STEP_SUMMARY` for formatted output
- Enable debug logging: Set `ACTIONS_STEP_DEBUG` secret

### 5. Maintenance
- Pin action versions: `actions/checkout@v4` not `@main`
- Document custom workflows
- Test workflow changes in branches first
- Monitor workflow run times and costs

---

**Previous:** [Template Structure](./Template-Structure.md) | **Next:** [Secrets & Environment Setup](./Secrets-and-Environment-Setup.md) →
