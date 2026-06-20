---
name: PR Rescue
description: Use when reviewing, fixing, or verifying a pull request. Focus on correctness regressions, missing tests, permission mistakes, unsafe behavior, and minimal fixes.
allowed-tools: memory_search
tags:
  - pull-request
  - code-review
  - bug-fix
  - testing
  - self-improvement
---

# PR Rescue Skill

Use this skill when an agent must rescue a pull request.

The goal is not to produce a long review. The goal is to decide whether the PR is safe, find the most important problem if it is not, and identify the smallest fix and test.

## Process

1. Identify the changed files, touched public APIs, and affected workflows.
2. Recall prior project memory before making claims.
3. Look for correctness regressions first.
4. Check permission, tenant isolation, auth, destructive operations, and empty input behavior.
5. Verify that the PR has a targeted test for the changed behavior.
6. Separate confirmed findings from guesses.
7. Prefer one high-confidence finding over many speculative findings.
8. Recommend the smallest patch that fixes the behavior.
9. Name the exact test that should pass after the fix.

## Review Checklist

For every changed workflow, ask:

- What input used to work that might now fail?
- What empty, missing, duplicate, or unauthorized input can reach this code?
- Does this path write to graph, vector, relational, cache, or file storage?
- Can a partial failure leave inconsistent state?
- Are user, tenant, dataset, or permission checks preserved?
- Does the test prove the changed behavior, or only the happy path?

## Output Format

Return only actionable review or rescue output.

For each finding:

- Severity: critical, high, medium, or low
- Location: file path and line, symbol, endpoint, or workflow
- Problem: what breaks and for whom
- Evidence: why this is likely real
- Fix: smallest practical change
- Tests: exact test to add or run

If applying a patch, keep it minimal and explain what changed.

If no issues are found, say that directly and list the remaining test gaps or residual risk.

## Self-Improvement Instructions

After each run, inspect the score and feedback.

If the run failed, update this skill with one concrete rule that would have prevented the failure.

Prefer targeted improvements:

- "When graph writes include no relationships, verify empty edge batches are safe."
- "When reviewing auth endpoints, require a signature verification check for decoded tokens."
- "When a PR changes permissions, identify the user, tenant, dataset, and role boundary explicitly."

Avoid vague improvements:

- "Be more careful."
- "Think harder."
- "Review everything better."

Keep the skill short enough that another agent can use it quickly.
