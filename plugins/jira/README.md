# Jira

Imports Jira Cloud stories, tasks, bugs and sub-tasks as Otaq tickets, through the Atlassian CLI.

- **Needs:** [`acli`](https://developer.atlassian.com/cloud/acli/), logged in (`acli jira auth login --web`, or
  **Log in** in Otaq's plugin settings).
- **Settings:** the Jira site (`acme.atlassian.net`) and the saved search in JQL (default: assigned to you and not
  done).
- **Imports:** open work items. Epics are never imported; a story's epic shows as its parent. The External ID is the
  issue key (`PAY-12`), and the description is converted to Markdown.
- **Jira Cloud only.** `acli` doesn't support Jira Data Center or Server.
