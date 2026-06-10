# Phase 5 Plan — Distribution & Import

> [한국어](04-phase5-plan-ko.md) · Status: **planned** (not yet implemented)

## Goal

Get an agent from *somewhere else* into a running host without rebuilding it. Two import sources, one convention:

```
agent-factory import ./agent-translator-0.1.0.zip          # zip / tar.gz archive
agent-factory import git+https://github.com/me/agent-x.git  # git repo (convention below)
agent-factory import git+https://...@v0.2.0                 # pinned ref
```

This matches where the ecosystem is heading in 2026: npm-style one-line installs for agent skills (skills.sh, MCP hubs) and machine-readable capability cards (A2A's `agent.json`). Our `AgentManifest` already plays the card role; Phase 5 adds the install pipeline around it.

## The import convention

An importable unit — whether unpacked from an archive or cloned from git — must be a directory that looks exactly like our example agents:

```
agent-x/
├── pyproject.toml      # REQUIRED: [project.entry-points."agent_factory.agents"]
│                       #           dependency on agent-factory-sdk (version band)
├── src/agent_x/
│   ├── __init__.py     # AGENT (manifest with sdk_version, build())
│   └── graph.py
└── tests/              # RECOMMENDED: assert_agent_valid() at minimum
```

Validation gate (before any install):
1. `pyproject.toml` parses and declares exactly one `agent_factory.agents` entry point.
2. Declared dependencies stay inside the SDK's allowed band (`langgraph`, `langchain-core`, `agent-factory-sdk`) — anything else needs an explicit `--allow-deps` flag.
3. After install: load through the existing registry (`check_compat` + `assert_agent_valid` with a `ScriptedChatModel`), in a subprocess so a hostile `import` cannot take down the host.

## Pipeline design

```
archive/git → staging dir → validate → uv pip install --target <agents-site>/<name>@<version>
            → registry refresh (entry points re-scan) → report (loaded | rejected + reason)
```

- **`agent_factory_sdk.importer`** (new module): `import_archive(path)`, `import_git(url, ref)`, both returning the same `LoadReport` shape the loader already uses — failures isolate, never raise.
- **Versioned install dirs** (`<name>@<version>`) make rollback a directory delete; `sys.path` gets the active version only.
- **Git mode** is `git clone --depth 1` (+ optional `--ref`); a commit hash in the lockfile (`agents.lock`) makes installs reproducible.
- **K8s shape** stays the Phase 3 recommendation: an initContainer runs `agent-factory import` against a PVC; the main container restarts to pick it up. No in-process hot reload.

## Trust model (the hard part)

Importing an agent is executing someone's code. Defaults are conservative:

| Risk | Mitigation |
|---|---|
| malicious `import` side effects | validation runs in a subprocess with `--no-network` env; host process never imports unvalidated code |
| dependency confusion / typosquatting | `--allow-deps` required for anything outside the SDK band; lockfile pins hashes |
| tampered archives | optional `--sha256` flag; git imports record the resolved commit |
| privilege of imported agents | same-process model is trusted-by-design — the escape hatch for untrusted agents remains a separate service + A2A, not import |

## Example repository

A public template repo, `jyje/pilot-agent-template`, doubling as the git-import demo target:

- the convention above, pre-wired (`cookiecutter`-style placeholders or a `create-agent` script)
- CI: `uv run pytest` (contract harness) + manifest JSON export as a release artifact (the A2A-style "agent card")
- a tagged release (`v0.1.0`) so `agent-factory import git+...@v0.1.0` works out of the box

## Milestones

1. **5a — archive import**: importer module + `import` CLI + tests with fixture zips (good/broken/incompatible).
2. **5b — git import**: clone + ref pinning + `agents.lock`.
3. **5c — template repo**: publish `pilot-agent-template`, document the end-to-end demo (`import git+…` → appears in the web app sidebar).
4. **5d (stretch)** — `GET /api/agents` grows an `agent.json`-compatible export; the backend gains `POST /api/import` guarded behind an admin flag.
