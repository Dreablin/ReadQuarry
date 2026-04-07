# ReadQuarry — Loop Prompt

Read `progress.md` to find the next uncompleted task (marked `[ ]`).
Read `PRD.md` to understand the requirements for that task.

Implement the task using TDD:
1. Write tests first.
2. Run tests — they should fail.
3. Write the implementation.
4. Run tests — they should all pass.
5. Run `pytest tests/ -v --tb=short` to verify the FULL test suite passes.

After the task passes all tests:
1. Update `progress.md`: mark the task `[x]`, update Current Status section, log decisions/issues if any.
2. Commit: `git add -A && git commit -m "feat: T{XX} - {description}"`

If ALL tasks in `progress.md` are marked `[x]`, output:
<promise>ALL_TASKS_COMPLETE</promise>
