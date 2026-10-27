# Otaq marketplace

Plugins for [Otaq](https://github.com/otaq-io/otaq), which runs coding agents on your tickets. A plugin connects Otaq
to a tool your team already uses, through that tool's own command-line program and your login: Otaq stores no tokens.

The first plugins connect issue trackers. You pick issues in Otaq (**New ticket ▾ → Import**) and they become Backlog
tickets, with the issue's key as their External ID; Otaq can refresh them later and pull new ones in the background.
More kinds of plugins will follow, such as notifications, pull request providers, CI status and context for agents.

How plugins work, and every rule below, is described in Otaq's
[docs/marketplace.md](https://github.com/otaq-io/otaq/blob/main/docs/marketplace.md).

| Plugin | Connects | Uses |
|---|---|---|
| [`github-issues`](plugins/github-issues) | GitHub Issues | `gh` |
| [`jira`](plugins/jira) | Jira Cloud | `acli` (Atlassian CLI) |
| [`azure-devops`](plugins/azure-devops) | Azure DevOps Boards | `az` with the `azure-devops` extension |

Install them from **Settings → Plugins** in Otaq. Each one shows a consent screen first, listing every command line it
can run.

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
skills/                 later
```

## Adding a plugin

Open a pull request with a new folder under `plugins/`. A plugin:

- is **declarative**: `plugin.yaml` names the vendor CLIs it runs and how their JSON output becomes what Otaq shows
  (issues, for the ticket sources of protocol 1). Protocol 1 has no scripts.
- is **open source**: `license:` is an OSI-approved SPDX id or FSL, with a `LICENSE` file in the folder.
- holds **only text**: the manifest, docs, license and fixtures. No binaries.
- stores **no tokens**: it relies on the CLI's own login.
- ships **fixtures**: `tests/fixtures/settings.json`, `search.json` with `search.expected.json`, and `fetch.json` with
  `fetch.expected.json`.

CI checks all of this on every pull request, and replays the fixtures with Otaq's own code on macOS, Linux and
Windows. To run the same checks locally:

```sh
pip install pyyaml
python3 scripts/marketplace.py validate
OTAQ_MARKETPLACE=$PWD cargo test --manifest-path ../otaq/Cargo.toml -p otaq-core --test suite -- \
  tracker_plugins::marketplace_plugins_map_their_fixtures
```

To try a plugin before it is released, use **Settings → Plugins → Add local folder…** in Otaq.

## Releasing

Change a plugin, bump its `version`, and merge. On `main`, CI releases each new version under the tag
`plugins/<id>-v<version>`, as a single `<id>-<version>.json` asset holding the plugin's files, and adds it to
`plugins/index.json` with its SHA256. Otaq checks that hash before installing.

## License

FSL-1.1-MIT, like Otaq. See [LICENSE](LICENSE).
