# Azure DevOps Boards

Imports Azure Boards user stories, tasks and bugs as Otaq tickets, through the Azure CLI's `azure-devops` extension.

- **Needs:** [`az`](https://learn.microsoft.com/cli/azure/) with the `azure-devops` extension (**Add extension** in
  Otaq's plugin settings), logged in (`az login`).
- **Settings:** the organization (`https://dev.azure.com/acme`), the project (per Otaq project) and the saved search
  in WIQL (default: assigned to you and not closed).
- **Imports:** open work items. Epics and Features are never imported; the parent shows on the ticket. The External
  ID is `#4021`, and the description is converted to Markdown.
