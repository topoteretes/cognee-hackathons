# PR Rescue Arena

## Challenge

Your agent receives a pull request that looks plausible but contains a bug, regression, missing test, security issue, or permission mistake.

Your job is to build a skill that helps the agent rescue the PR and then improve the skill from the run result.

## Required Loop

Every team must demonstrate this sequence:

```text
1. Run starter or initial skill on PR #1.
2. Score the run.
3. Store the run as SkillRunEntry in Cognee.
4. Improve SKILL.md based on that feedback.
5. Run the improved skill on PR #2.
6. Compare before and after performance.
```

The skill improvement should be specific. Avoid generic additions like "be more careful". Prefer changes such as:

- check permission boundaries before suggesting endpoint changes
- run the narrowest test that covers the changed file
- verify empty input behavior before approving graph writes
- separate confirmed findings from guesses
- include the exact file and symbol for every finding

## Agent Expectations

For each PR, the agent should:

1. Identify changed files and touched workflows.
2. Infer the user-visible or system-visible risk.
3. Find the smallest likely fix.
4. Run or specify targeted tests.
5. Record outcome and failure mode.
6. Improve the skill if the result was weak.

## What Counts As A Rescue

A PR is rescued when the agent does at least one of these well:

- finds the real defect and explains it
- proposes a correct minimal patch
- identifies the missing test
- blocks an unsafe change
- catches a permission or tenant-isolation regression
- explains why the PR is safe after verification

## Feedback Fields

Use `SkillRunEntry` to store run feedback. Recommended fields:

```python
SkillRunEntry(
    run_id="team:round:skill",
    selected_skill_id="pr-rescue",
    task_text="Review and rescue PR #...",
    result_summary="Short summary of what the agent found",
    success_score=0.0,  # 0.0 failure, 0.5 partial, 1.0 strong
    feedback=-1.0,     # -1.0 bad, 0 neutral, 1.0 good
    error_type="missed_bug",
    error_message="Agent missed the failing empty-edge path",
)
```

Useful `error_type` values:

- `missed_bug`
- `wrong_fix`
- `missing_test`
- `hallucinated_api`
- `permission_gap`
- `unsafe_change`
- `weak_evidence`
- `agent_failed`

## Scoring Rubric

Total: 100 points.

```text
40 - PR rescue quality
25 - self-improvement evidence
20 - review clarity
10 - reproducibility
5  - safety
```

### PR Rescue Quality

- finds the real issue
- proposes a practical fix
- targets the right tests
- avoids unrelated edits

### Self-Improvement Evidence

- stores feedback in Cognee
- shows before and after scores
- updates the skill based on a concrete failure
- improved run performs better

### Review Clarity

- severity is clear
- file references are concrete
- impact is explained
- fix and tests are actionable

### Reproducibility

- Daytona run can be replayed
- logs are included
- no hidden local state required

### Safety

- no permission bypasses
- no secrets printed
- no destructive commands without reason
- no hallucinated APIs or fake tests

## Suggested Multi-Agent Flow

You can use one agent, but multi-agent teams are encouraged.

```text
Scout -> finds changed files and likely risk areas
Fixer -> proposes or applies the patch
Critic -> scores the result and labels failure modes
Editor -> updates SKILL.md
Verifier -> reruns tests or checks the improved result
```

The best teams will show that agents share useful memory through Cognee instead of repeating work.

## Final Round

The final PR is hidden until the end.

During the final round:

- use your improved skill as-is
- do not manually edit the skill
- let the agent run
- submit the final output and score

The final round tests whether your skill learned a reusable PR rescue strategy, not a one-off answer.
