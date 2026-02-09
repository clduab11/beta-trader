# Claude Code Configuration for Beta-Trader

## Primary Reference
**Always read `AGENTS.md` first** — it contains the authoritative project structure, workflow, and agent instructions.

## Documentation-First Workflow
1. Check `docs/INDEX.md` to discover existing specs
2. Read relevant specs before implementing
3. Use templates from `docs/templates/` for new documentation
4. Follow the spec lifecycle: Draft → Under Review → Approved

## Phase-Gated Execution
- Check `docs/tickets/ROADMAP.md` for current phase and active ticket
- Only one implementation ticket should be In Progress at a time
- Peer review and spec writing can overlap with implementation

## Spec Status Authority
- Spec status (Draft/Under Review/Approved) is authoritative in the spec file
- Ticket status (Todo/In Progress/Done) is authoritative in the roadmap
- Master index is links-only (no status duplication)

## Validation Recording
When validating implementation:
- Add validation note inline in the spec's Validation History section
- Use standardized format: visible entry + HTML comment marker
- Example:
  ```
  - IMPLEMENTATION VALIDATION: 2026-02-10 — Actor: @clduab11 — Result: PASS — Notes: All acceptance criteria met
    <!-- VALIDATION:TYPE=IMPLEMENTATION;DATE=2026-02-10;ACTOR=@clduab11;RESULT=PASS;REF=commit-abc123 -->
  ```

## Integration Notes
- Continue.dev: Local execution and MCP/tool access
- Notion: Org-level spec storage (optional)
- Linear: Execution workboard (optional)
- Existing GitHub Actions handle Notion↔Linear sync

## References
- Architecture: `AGENTS.md` section 2
- Workflow: `docs/tickets/ROADMAP.md`
- Templates: `docs/templates/`
- Interfaces: `docs/interfaces/`
