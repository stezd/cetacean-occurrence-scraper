---
name: block-escape-hatches
enabled: true
event: file
action: block
pattern: '@ts-ignore|@phpstan-ignore|eslint-disable|TODO\s*:\s*fix\s+later|HACK\s*:'
---

Blocked: this edit adds an escape hatch instead of a fix.

Matched: `@ts-ignore`, `@phpstan-ignore`, `eslint-disable*`, `TODO: fix later`, or `HACK:`.

Do one of these instead:

1. **Fix the root cause.** Correct the type, narrow the value, handle the branch, or delete
   the dead path. A suppression converts a compile error into a runtime surprise.
2. **Encode a deterministic check.** Add the assertion, lint rule, architecture test, or
   hookify rule that fails when the condition returns. A check outlives a comment.
3. **Stop and ask the user** if the suppression is genuinely required. Name the error, why
   it cannot be fixed here, and the check that will catch the regression. Do not write a
   rationalizing comment in place of an answer.

Do not rename the marker, split it across lines, or move it into a string. The block is on
the pattern, not on the wording.
