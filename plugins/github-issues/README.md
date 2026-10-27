# GitHub Issues

Imports a repository's open issues as Otaq tickets, through the GitHub CLI.

- **Needs:** [`gh`](https://cli.github.com), logged in (`gh auth login`, or **Log in** in Otaq's plugin settings).
- **Settings:** the repository (`owner/name`, per project), the saved search (GitHub's search syntax, default
  `is:open assignee:@me`) and the labels that set a ticket's priority.
- **Imports:** every open issue. The External ID is `#12`.
