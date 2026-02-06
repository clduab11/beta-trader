# Linear & Notion Label Sync Strategy

## Overview

To maintain consistency across GitHub, Linear, and Notion, we use a unified set of labels. This ensures that filtering, reporting, and automation work seamlessly across all three platforms.

## Source of Truth

The master list of labels is maintained in `.github/labels.yml` within the repository.
Any changes to labels should be committed there first.

## Unified Label List

### Automation Group
*Applied automatically by CI/CD or Bots*
- `auto-deploy`: Triggered by automated deployment pipelines
- `auto-hook`: Related to webhook automation
- `auto-label`: Applied by label automation bots
- `auto-monitor`: Related to monitoring automation
- `auto-sync`: Related to sync automation
- `auto-workflow`: Related to GitHub Actions workflows

### Cadence (Priority)
*Maps to Linear Priority*
- `p0-blocker`: Urgent blocker (Linear: Urgent)
- `p1-high`: High priority (Linear: High)
- `p2-medium`: Medium priority (Linear: Medium)
- `p3-low`: Low priority (Linear: Low)

### Domain
*Functional area of the codebase*
- `domain/ai`: AI, ML, and LLM components
- `domain/community`: Community features
- `domain/infrastructure`: DevOps & Cloud
- `domain/integration`: External APIs
- `domain/monitoring`: Observability

### Scope (Size)
*T-Shirt sizing for effort estimation*
- `size-xs`, `size-s`, `size-m`, `size-l`, `size-xl`
- `size-unk`: Unknown estimate

### Special Status
- `blocked-ext`: Blocked by external dependency
- `blocked-int`: Blocked by internal dependency
- `breaking-change`: Contains breaking changes
- `tech-debt`: Internal cleanup

### Type
*Work Item Type*
- `bug`: Something isn't working
- `documentation`: Docs only
- `enhancement`: Improvement to existing feature
- `feature`: New functionality
- `infra`: Infrastructure changes
- `performance`: Speed/Efficiency
- `personality`: AI Persona/Voice tuning
- `qol-imp`: Quality of Life
- `refactor`: Code restructuring
- `security`: Security fix
- `social`: Social integration
- `spike`: Research task

## Syncing Mechanism

1. **GitHub**: Labels are synced using the `crazy-max/ghaction-github-labeler` workflow (if enabled) or manually matched to `.github/labels.yml`.
2. **Linear**: Labels should be created in Team Settings to match this list exactly.
3. **Notion**: select/multi-select properties in the spec database should include these options.
