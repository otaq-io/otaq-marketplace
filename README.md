# Otaq marketplace

The plugin marketplace for [Otaq](https://github.com/otaq-io/otaq), which runs coding agents on your tickets.
Plugins are add-ons that Otaq runs itself, with no agent involved. A plugin connects Otaq to a tool your team already
uses, through that tool's own command-line program and your login: Otaq stores no tokens.

Every plugin here is open source and readable, is reviewed before it is merged, and is checked against the SHA256 in
this repository's index before Otaq reads it; Otaq shows a consent screen before every install and update.

| Plugin | Kind | Connects | Uses |
|---|---|---|---|
| [`github-issues`](plugins/github-issues) | ticket source | GitHub Issues | `gh` |
| [`jira`](plugins/jira) | ticket source | Jira Cloud | `acli` (Atlassian CLI) |
| [`azure-devops`](plugins/azure-devops) | ticket source | Azure DevOps Boards | `az` with the `azure-devops` extension |

More kinds are planned: context for agents (Notion, Confluence, Figma), notifications, pull request providers, CI
status and previews. See [Kinds of plugin](#kinds-of-plugin).

## Contents

- [Using the marketplace](#using-the-marketplace)
- [Trust and safety](#trust-and-safety)
- [Installing and updating](#installing-and-updating)
- [How a plugin works](#how-a-plugin-works)
- [Writing a plugin](#writing-a-plugin)
- [Adding a plugin](#adding-a-plugin)
- [Releasing](#releasing)
- [Kinds of plugin](#kinds-of-plugin)
- [Ticket sources](#ticket-sources)
- [Layout](#layout)
- [License](#license)

## Using the marketplace

**Settings → Plugins** is where you manage plugins:

- browse the marketplace and install, update or remove plugins;
- add another marketplace by its GitHub URL, or a plugin from a folder on disk;
- set **global defaults** for each plugin's settings;
- check each plugin's command-line tools, with **Log in** (and **Add extension**) when one needs it.

## Trust and safety

**Every plugin is open source, and all of it can be read:**

- **A license is required.** `license:` is an OSI-approved SPDX id (MIT, Apache-2.0, BSD, MPL, GPL…) or FSL
  (`FSL-1.1-MIT`, `FSL-1.1-Apache-2.0`), and the plugin's folder has a `LICENSE` file.
- **No binaries.** A plugin holds only text: its manifest, docs, license and test fixtures. Programs and non-text files
  are refused. The CLIs a plugin uses are installed by you, separately.
- **What you install is the source.** Each release is one JSON file listing the plugin folder's files, built by CI from
  the tagged folder. Otaq checks its SHA256 against the marketplace's index before reading it.

Each plugin has a **label**:

| Label | Where it comes from |
|---|---|
| **Official** | This repository. Every change is reviewed before merge. |
| **Community** | Another marketplace you added by URL. Not reviewed by the Otaq project. |
| **Local** | A folder on disk, for writing and testing a plugin. |

Otaq enforces the open-source rules when installing Official and Community plugins; a Local folder gets warnings
instead, so you can try a plugin before it has a license.

Before an install or an update, Otaq shows a **consent screen**: every CLI and command line the plugin can run, whether
it can pull in the background, its license, label and source, and for an update a link to what changed. Nothing
installs until you agree. A Local plugin whose commands change is stopped until you add its folder again.

## Installing and updating

- Otaq reads each marketplace's `plugins/index.json`.
- **Network use is minimal.** Otaq reads the index when you open Settings → Plugins (if its copy is over an hour old),
  and once a day only while a marketplace plugin is installed. With no plugins, it makes no requests for them. Nothing
  about you is sent.
- **Updates are never automatic.** Settings shows "Update to 1.3.0", which opens the consent screen again.
- Versions that don't support your Otaq version are hidden.
- **Removing a plugin** keeps the tickets you imported, with their links to the tracker.

## How a plugin works

A plugin contains no code. It is a **manifest** (`plugin.yaml`) that tells Otaq which command-line tool to run and how
to read its JSON output. It relies on the tool's own login:

- **Otaq stores no tokens.** You log in with the vendor's CLI (`gh auth login`, `az login`, `acli jira auth login`);
  **Log in** opens that command in Otaq's terminal, and the CLI usually finishes the login in your browser.
- **Your project's environment variables are not passed to plugins.** Plugin commands see only your normal
  environment.

Otaq runs the CLI directly, never through a shell, so the same plugin works on macOS, Linux and Windows. Each command
has a time limit (30 seconds for a search or a fetch, 15 for a check) and capped output.

A tracker plugin has two commands: **`search`** lists issues for a query, and **`fetch`** reads one issue in full.
Azure DevOps, for example, searches with `az boards query`, and Otaq then fetches each issue you pick with
`az boards work-item show`. Descriptions in a tracker's own format (Jira's ADF, Azure DevOps' HTML) become Markdown
through Otaq's **built-in transforms**, so plugins stay declarative.

## Writing a plugin

A plugin is a folder with a `plugin.yaml`. Here is the GitHub Issues one, shortened (see
[`plugins/github-issues/plugin.yaml`](plugins/github-issues/plugin.yaml) for all of it):

```yaml
id: github-issues
name: GitHub Issues
version: 1.0.0
protocol: 1                    # the plugin format
otaq: ">=0.1.0, <2.0.0"        # the Otaq versions it works with
license: FSL-1.1-MIT
provides: [ticket_source]
capabilities: [import, refresh, auto_pull]

requires:
  - id: gh
    name: GitHub CLI
    check: [gh, --version]
    login_check: [gh, auth, status]
    login: [gh, auth, login]
    install:
      macos: brew install gh

settings:
  - { key: repo, label: Repository, required: true, format: owner_repo, scope: project }
  - { key: query, label: Saved search, default: "is:open assignee:@me" }
  - { key: priority_labels, label: Priority labels, type: map, default: { P1: urgent, P2: high } }

issue_url: "https://github.com/{settings.repo}/issues/{id}"

commands:
  search:
    run: [gh, issue, list, -R, "{settings.repo}", --search, "{query}", --limit, "{limit}",
          --json, "number,title,url,state,labels"]
    map:
      items: "$"
      id: number
      key: "#{number}"
      url: url
      title: title
      state: state
      priority: { from: "labels[].name", via: settings.priority_labels }
  fetch:
    run: [gh, issue, view, "{id}", -R, "{settings.repo}", --json, "number,title,body,url,state,labels"]
    map:
      item: "$"
      id: number
      key: "#{number}"
      title: title
      body: body
```

The fields:

- **`requires`**: the CLIs the plugin runs. Otaq checks each is installed (`check`), logged in (`login_check`) and, for
  a CLI that needs one, has its `extension`; it shows the `install` hint and **Log in** otherwise.
- **`settings`**: the form in Settings. Each value is the project's, else the global default, else the manifest's
  `default`. A string has a `format`: `text`, `slug`, `owner_repo`, `host` or `url`. `scope: project` has no global
  default; `type: map` holds name → value pairs. A plugin with `auto_pull` has a `query` setting: the saved search the
  Import dialog starts with and auto-pull runs.
- **`types`**: which tracker types are work items and which are containers (`containers: [Epic, Feature]`).
  **`states`**: the states that count as finished, when the mapping gives no `state_category`.
- **`run`**: the command line, one list item per argument, its program one of `requires`. A `{placeholder}` fills part
  of one argument and never splits it: `{settings.<key>}`, `{query}` and `{limit}` for a search, `{id}` for a fetch.
  Unknown placeholders are refused, and a value that starts with `-` or holds a line break is refused.
- **`map`**: how the JSON output becomes issues. `items` (search) or `item` (fetch) is where they are; each field is a
  dotted path (`fields.summary`, `labels[0]`, `labels[].name` for each element, `fields["System.Title"]` for a key
  with dots), a text that reads the issue (`"#{number}"`), or a rule with a `transform` (`adf_to_markdown`,
  `html_to_markdown`) or a lookup (`via:` an inline map, or `settings.<key>` naming a map setting).
- **`issue_url`**: the issue's page, when the output has no `url`.

Every issue comes out in one shape:

```json
{ "id": "PAY-12", "key": "PAY-12", "url": "https://acme.atlassian.net/browse/PAY-12",
  "title": "…", "body": "Markdown", "type": "Story", "type_category": "work",
  "state": "To Do", "state_category": "open", "parent": { "key": "PAY-3" }, "priority": 2 }
```

A priority maps from `urgent`, `high`, `normal`, `low` (and Jira's Highest, Medium, Lowest) or 1–4. A failed command is
reported as `not_installed`, `not_logged_in`, `bad_settings`, `not_found`, `rate_limited` or `failed`, with its first
line of output. `script:` commands are reserved for a later protocol: today every plugin is declarative.

The manifest's schema is [`plugins/plugin.schema.json`](plugins/plugin.schema.json). To try a plugin as you write it,
use **Settings → Plugins → Add local folder…** in Otaq.

## Adding a plugin

Open a pull request with a new folder under `plugins/`. A plugin:

- is **declarative**: `plugin.yaml` names the CLIs it runs and how their JSON output becomes what Otaq shows. No
  scripts.
- is **open source**: an OSI-approved or FSL `license:`, with a `LICENSE` file in the folder.
- holds **only text**: the manifest, docs, license and fixtures. No binaries.
- stores **no tokens**: it relies on the CLI's own login.
- ships **fixtures**: `tests/fixtures/settings.json`, then `search.json` with `search.expected.json` and `fetch.json`
  with `fetch.expected.json`: recorded CLI output and the issues Otaq should make of it.

CI checks all of this on every pull request (the rules, the schema, a version bump for a changed plugin), and replays
the fixtures with Otaq's own code on macOS, Linux and Windows. The same checks locally:

```sh
pip install pyyaml check-jsonschema
python3 scripts/marketplace.py validate
check-jsonschema --schemafile plugins/plugin.schema.json plugins/*/plugin.yaml
OTAQ_MARKETPLACE=$PWD cargo test --manifest-path ../otaq/Cargo.toml -p otaq-core --test suite -- \
  tracker_plugins::marketplace_plugins_map_their_fixtures
```

## Releasing

Change a plugin, bump its `version`, and merge. On `main`, CI releases each new version under the tag
`plugins/<id>-v<version>`, as one `<id>-<version>.json` file holding the plugin's files, and adds it to
`plugins/index.json` with its SHA256. Otaq checks that hash before installing.

## Kinds of plugin

A plugin says what it is in its manifest's `provides:` field. Otaq runs `ticket_source` today; the others aren't built
yet, and the list will change. Proposals and pull requests are welcome, starting with the ticket sources, which
need nothing new from Otaq.

| Kind (`provides:`) | What it does | Examples |
|---|---|---|
| `ticket_source` | Imports work as Backlog tickets, refreshes it and pulls new items (available now). | Linear, GitLab Issues, YouTrack, ClickUp, Shortcut; Sentry and Datadog errors; Dependabot, Snyk and GitHub code scanning alerts |
| `context` | Pulls pages or designs linked from a ticket into it, for the agent to read. | Notion, Confluence, Google Docs, Figma |
| `notify` | Tells you when a ticket needs you or is ready for review. | Slack, Microsoft Teams, Discord, ntfy |
| `pr_provider` | Opens and follows pull requests on more hosts. | GitLab, Bitbucket, Gitea |
| `ci_status` | Shows CI results on a ticket before you review it. | GitHub Actions, Azure Pipelines, GitLab CI, CircleCI |
| `preview` | Starts a preview environment for a ticket's worktree. | Vercel, Netlify, Docker Compose |
| Write-back | Updates the tracker as a ticket moves: its state, a comment with the PR link. | Jira, Azure DevOps, GitHub Issues |

Kinds that act on Otaq's events (`notify`, `pr_provider`, `ci_status`, `preview` and write-back) do more than read,
so they need a later plugin protocol and more trust on the consent screen; they will be designed before they are
built.

Content, which runs no code, will get its own top-level folders next to `plugins/`, each with its own index:

- `skills/`: skills for Otaq's agents.
- `flows/`: flow presets, such as a test-first flow or a docs-only flow.
- `instructions/`: agent instruction packs, such as a house style for a language.
- `themes/`: Otaq themes.

## Ticket sources

The kind of plugin Otaq runs today: it brings work into Otaq as tickets.

A ticket source offers up to three features:

| Feature | What it does |
|---|---|
| **Import** | Search the tracker, pick issues, and create Backlog tickets. Each ticket gets the issue's key as its External ID (e.g. `PAY-123`), its priority and a link back to the issue. |
| **Refresh** | Fetch an imported ticket's title and description again, when the issue changed after you imported it. |
| **Auto-pull** | Run a saved search every few minutes (15 by default) and add new issues to the Backlog. Off unless you turn it on for a project. |

The first plugins are **read-only**: they never change anything in the tracker. Only **work that is ready to be worked
on** is imported: open stories, tasks, bugs and sub-tasks. Epics and other containers are never imported; a ticket's
epic is shown as a link on it.

**Project settings → Plugins** is where a project uses a plugin: turn it on and fill in its settings (site,
repository, saved search…). An empty field uses the global default. A project can use several plugins, each set up
once; one search can cover several projects or repositories (e.g. `project in (PAY, AUTH)` in Jira).

**On the board**, **New ticket ▾ → Import from \<plugin\>** opens a search:

```
Import from Jira
 [sprint in openSprints()         ] [Search]
 [x] PAY-123  Fix login        parent PAY-100
 [x] PAY-124  Add SSO
 [ ] PAY-130  Old bug          already imported
 [ ] PAY-131  Flaky test       dismissed · import again
                                   [Import 2]
```

- A search shows at most **100 issues**; with more, narrow it.
- Issues already imported are greyed out.
- Deleting an imported ticket marks its issue **dismissed**: auto-pull never brings it back, but you can import it
  again from this dialog.

**Imported tickets** show their tracker issue on the card ("Jira · PAY-12"), and the ticket's editor has **Open in
Jira ↗**, the quick way to update the issue yourself.

**Refresh from tracker** compares each field (title and description) as imported, as the ticket has it now, and as
the tracker has it now. A field you didn't edit takes the tracker's text silently; a field both sides changed is shown
side by side, and you pick **Use tracker** or **Keep mine**. Nothing is overwritten without asking.

**Auto-pull** runs while Otaq's background service runs, also with the window closed to the tray. It only adds
tickets to the Backlog: it never moves, starts or deletes anything, and it skips issues already imported or dismissed.
A failed pull shows its reason in the project's plugin settings.

### Agents and ticket sources

Otaq's Project agent can search and import through the plugins you turned on for its project, with
`otaq plugins search <plugin> ["<query>"]` and `otaq plugins import <plugin> <id>…`. For example: "import this
sprint's stories and plan them". Imports land in the Backlog. Ticket agents can't use plugins, and no agent can
install, configure or approve one.

## Layout

Each kind of content has its own folder, and everything of that kind lives under it:

```
plugins/
  index.json            written by CI only: every released version, with its SHA256
  plugin.schema.json    the manifest's schema
  <id>/
    plugin.yaml         the manifest
    README.md
    LICENSE
    tests/fixtures/     recorded CLI output and the issues Otaq should map it to
skills/  flows/  …      later (see Kinds of plugin)
scripts/marketplace.py  the CI's checks and releases
```

## License

FSL-1.1-MIT, like Otaq. See [LICENSE](LICENSE).
