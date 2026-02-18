# Branch Protection Setup

> **Note**: Branch protection rules must be configured manually by a repository admin through the GitHub UI or API. They cannot be set via code in the repository.

## Required Settings for `main` Branch

### Step-by-Step Instructions

1. Navigate to your repository on GitHub
2. Go to **Settings** → **Branches**
3. Click **Add branch protection rule** (or edit existing rule for `main`)
4. Set **Branch name pattern** to: `main`

### Recommended Protection Rules

| Setting | Value | Reason |
|---------|-------|--------|
| **Require a pull request before merging** | ✅ Enabled | Prevents direct pushes to main |
| **Require approvals** | 1 | At least one review before merge |
| **Require status checks to pass before merging** | ✅ Enabled | CI must pass |
| **Require branches to be up to date before merging** | ✅ Enabled | Ensures PR is rebased on latest main |

### Required Status Checks

Add the following status check(s) that must pass before merging. These correspond to job names defined in `.github/workflows/ci.yml`:

- **`Test Python Layer`** — Runs ruff lint, ruff format check, and pytest

### Additional Recommended Settings

| Setting | Value |
|---------|-------|
| **Do not allow bypassing the above settings** | ✅ Enabled (for stricter enforcement) |
| **Restrict who can push to matching branches** | Optional — limit to maintainers |
| **Allow force pushes** | ❌ Disabled |
| **Allow deletions** | ❌ Disabled |

## Verification

After configuring branch protection:

1. Create a test branch and open a PR to `main`
2. Verify that the CI workflow runs automatically
3. Confirm that the PR cannot be merged until **Test Python Layer** passes
4. Confirm that at least one approval is required (if configured)

## CI Workflow Reference

The CI workflow (`.github/workflows/ci.yml`) triggers on:
- **Push** to `main`
- **Pull requests** targeting `main`

It runs a single job:
- **Test Python Layer**: Installs dependencies via `uv`, runs `ruff check`, `ruff format --check`, and `pytest tests/`
