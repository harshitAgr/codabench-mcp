# codabench-mcp

MCP server for the [Codabench](https://www.codabench.org) REST API. Lets an
AI agent drive a full participant ML-benchmark workflow: discover
competitions, read rules, download data, submit, poll, read leaderboards.

## Features

Curated tools for the participant path:

- `search_competitions`, `get_competition`, `list_competition_phases`,
  `get_phase`, `get_competition_rules`, `list_competition_tasks`, `get_task`
- `download_dataset` (streaming + SHA-256)
- `list_my_submissions`, `get_submission`, `get_submission_logs`
- `submit_to_phase` (handles Codabench's 3-step upload flow)
- `poll_submission` (backoff + timeout + non-error "still_running")
- `get_leaderboard`, `get_my_profile`
- `codabench_request` — generic REST escape hatch (GET-only by default)

## Authentication

You need a Codabench API token. Two ways to get one:

### 1. Swagger UI (recommended)

1. Visit https://www.codabench.org/api/docs/
2. Find the `api-token-auth` endpoint → **Try it out**
3. POST your username/password
4. Copy the `token` value from the response

### 2. curl

```bash
curl -X POST https://www.codabench.org/api/api-token-auth/ \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}'
```

The response is `{"token": "..."}`.

## Install

```bash
uvx codabench-mcp
```

To run the bleeding-edge `main` branch instead of the last release:

```bash
uvx --from git+https://github.com/harshitAgr/codabench-mcp codabench-mcp
```

Or for development:

```bash
git clone https://github.com/harshitAgr/codabench-mcp.git
cd codabench-mcp
uv sync
uv run codabench-mcp  # requires CODABENCH_API_TOKEN
```

## Configure an MCP client

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "codabench": {
      "command": "uvx",
      "args": ["codabench-mcp"],
      "env": {
        "CODABENCH_API_TOKEN": "paste-your-token-here"
      }
    }
  }
}
```

### Claude Code (plugin marketplace)

```shell
/plugin marketplace add harshitAgr/codabench-mcp
/plugin install codabench-mcp@codabench-mcp
```

Then export your token in the shell where you launch Claude Code:

```bash
export CODABENCH_API_TOKEN=paste-your-token-here
```

### Claude Code (manual)

If you'd rather skip the plugin layer:

```bash
claude mcp add codabench \
  --env CODABENCH_API_TOKEN=paste-your-token-here \
  -- uvx codabench-mcp
```

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `CODABENCH_API_TOKEN` | yes | — | DRF token, sent as `Authorization: Token <token>` |
| `CODABENCH_BASE_URL` | no | `https://www.codabench.org` | Override for tests |
| `CODABENCH_ALLOW_WRITE_RAW` | no | `0` | Set to `1` to allow non-GET methods through `codabench_request` |
| `CODABENCH_MAX_DOWNLOAD_BYTES` | no | `5368709120` (5 GB) | Cap for `download_dataset` |

## Development

```bash
uv sync
uv run pytest                              # unit tests, no network
uv run ruff check .                        # lint
uv run ruff format --check .               # format check
```

## License

MIT — see [LICENSE](LICENSE).

<sub>`mcp-name: io.github.harshitAgr/codabench-mcp`</sub>
