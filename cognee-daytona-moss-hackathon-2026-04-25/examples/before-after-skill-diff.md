# Example Before/After Skill Diff

This is a small example of what judges want to see.

The goal is not to make `SKILL.md` longer. The goal is to add one concrete rule
that would have prevented a real failure.

## Baseline Run

Task:

```text
Review a PR that changes graph storage writes.
```

Result:

```text
The agent noticed the PR touched graph storage, but it only reviewed the happy
path. It missed that relationship extraction can produce an empty edge list.
The code called a relational edge upsert with an empty list, which caused an
invalid default insert.
```

Recorded feedback:

```text
SkillRunEntry(
    run_id="team-a:practice-1:pr-rescue",
    selected_skill_id="pr-rescue",
    task_text="Review PR changing graph storage writes",
    result_summary="Missed empty edge batch failure",
    success_score=0.3,
    feedback=-0.8,
    error_type="missed_bug",
    error_message="Agent did not verify empty graph relationship batches.",
)
```

## Skill Before

```markdown
## Review Checklist

For every changed workflow, ask:

- What input used to work that might now fail?
- Are user, tenant, dataset, or permission checks preserved?
- Does the test prove the changed behavior, or only the happy path?
```

## Skill After

```markdown
## Review Checklist

For every changed workflow, ask:

- What input used to work that might now fail?
- What empty, missing, duplicate, or unauthorized input can reach this code?
- If this path writes nodes, edges, files, rows, vectors, or cache entries,
  does an empty batch become a no-op instead of a malformed write?
- Are user, tenant, dataset, or permission checks preserved?
- Does the test prove the changed behavior, or only the happy path?
```

## Why This Is A Good Improvement

The new rule is:

- based on a real missed bug
- specific enough to change future behavior
- reusable across graph, vector, relational, file, and cache writes
- short enough that the skill remains readable

## Improved Run

Task:

```text
Review a second PR that changes batch indexing behavior.
```

Result:

```text
The agent explicitly checked empty batch handling, found that one path still
called the underlying adapter with an empty list, and recommended a no-op guard
plus a unit test for empty input.
```

Improved feedback:

```text
success_score = 0.8
feedback = 0.7
error_type = ""
error_message = ""
```

## What Not To Submit

Avoid vague skill changes like:

```markdown
- Be more careful.
- Think about edge cases.
- Review the code deeply.
```

Those do not prove self-improvement. Judges should be able to trace the change
from a real failure to a new behavior in the next run.
