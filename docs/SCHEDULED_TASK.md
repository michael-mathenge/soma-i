# SOMA.i reminder scheduled task evidence

## Scope

This is a record of the local scheduled-task setup and its observed runs. The schedule is currently paused, as shown in the Scheduled view screenshot below. The task runs the reminder report against a disposable copy of the demo database and appends its repeat-suppression log in the Windows temp folder.

The workflow does not write to the application database or send SMS or email. The Gmail draft step was not exercised; no draft was created. The live Gmail plugin path remains unverified.

## Prompt used for the successful run

The Scheduled form had no project field, so the prompt names the repository working directory and uses absolute paths. The successful prompt was:

```text
Invoke the $soma-reminder-ops skill. Use C:/dev/soma-i as the working directory. Run exactly this one PowerShell command:
$env:DATABASE_URL = 'sqlite:///.local/soma-reminder-demo-copy.sqlite3'; & 'C:/dev/soma-i/.venv/Scripts/python.exe' 'C:/dev/soma-i/backend/manage.py' reminder_ops --json --log "$env:TEMP/soma-reminder-alerts.jsonl"
Then follow the skill's instructions for the result. If the command fails, report the error text and stop. Do not run any other command. Do not edit files, read the database directly, run ingestion or seeding, or send anything.
```

The database URL points at `.local/soma-reminder-demo-copy.sqlite3`, a copy of the repository demo database. The explicit `--log` path puts the JSONL log in the Windows temp folder because scheduled runs could not write the log inside the repository.

## Run history

1. **Run 1 failed:** The scheduled run had no valid working directory and returned `The directory name is invalid. (os error 267)`.
2. **Run 2 failed:** After adding absolute paths, the command and database copy worked, but the default log destination inside the repository was denied: `CommandError: Cannot append JSONL log C:\dev\soma-i\.local\soma-reminder-ops\alerts.jsonl: [Errno 13] Permission denied`.
3. **Run 3 succeeded:** After adding `--log "$env:TEMP/soma-reminder-alerts.jsonl"`, the task reported Learner ID 1, Data Analyst, next checkpoint SQL checkpoint, Completed 1, Remaining 3. The alert was printed over four lines. The screenshot captures the successful alert and the working temp-folder log prompt.

Running the same command from a normal project chat printed the alert on the first attempt. Scheduled runs have narrower write permission than a project chat; the repository log path failed while the Windows temp path succeeded.

## Schedule state and evidence

The schedule is configured to run hourly on this computer. It is paused and is not running now. The Scheduled view screenshot shows the task marked `Paused · Hourly`.

![Scheduled task thread showing the repository log permission error, working temp-folder prompt, and generated reminder alert](images/scheduled-task.png)

![Scheduled view showing the task paused with an hourly interval](images/scheduled-task-paused.png)

## Limits

- A scheduled run has narrower write permission than a project chat. Keep its log in the Windows temp folder, as in the successful prompt.
- The schedule is paused; the screenshots document its state and one successful run, not ongoing execution.
- The Gmail draft step was not exercised. No draft was created, and Gmail connection status was not verified.
