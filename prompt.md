# ReadQuarry — Loop Prompt

## Ralph Loop: `max_iterations` safety cap

When starting this loop in Cursor, set **`max_iterations` to a finite positive number** (for example 15–100) in `.cursor/ralph/scratchpad.md` frontmatter or via the plugin’s `--max-iterations` flag. **Do not use `0` (unlimited)** as the only guard: some setups may keep scheduling turns even after `<promise>ALL_TASKS_COMPLETE</promise>`, which wastes iterations. The completion promise remains the primary stop signal; a finite cap is a **hard backup limit**.

---

Read `progress.md` to find the next uncompleted task (marked `[ ]`).
Read `BUGS.md` to understand the requirements for that task.

Implement the task using TDD:
1. Write tests first.
2. Run tests — they should fail.
3. Write the implementation.
4. Run tests — they should all pass.
5. Run `pytest tests/ -v --tb=short` to verify the FULL test suite passes.

After the task passes all tests:
1. Update `progress.md`: mark the task `[x]`, update Current Status section, log decisions/issues if any.
2. Commit: `git add -A && git commit -m "fix: B{XX} - {description}"`

If ALL tasks in `progress.md` are marked `[x]`, output:
<promise>ALL_TASKS_COMPLETE</promise>
