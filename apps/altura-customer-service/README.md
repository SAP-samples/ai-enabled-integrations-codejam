# Altura Customer Service

CAP backend for Altura Coffee Co. customer service requests.

## What it exposes

| Surface          | URL                                                            |
|------------------|----------------------------------------------------------------|
| OData v4         | `http://localhost:4004/customer-requests/`                     |
| Custom action    | `POST /customer-requests/get_customer_requests`                |
| Fiori Elements   | `http://localhost:4004/customer-requests/webapp/index.html`    |
| MCP server       | `http://localhost:4004/mcp` (health: `/mcp/health`)            |

Note: the OData base path is `/customer-requests/` (not `/odata/v4/customer-requests/`) because the service uses `@path: '/customer-requests'`, which overrides the default OData prefix.

## Run locally

```bash
npm install
npm run watch
```

## Data model

`CustomerRequests` (1) -> `Tasks` (n) -> `Equipment` (n)

Equipment is modelled as a thin composition child rather than a flat array — the CAP-idiomatic way to persist arrays of strings.

## MCP tools

- `list_customer_requests` — list all requests
- `create_customer_request` — create a new request
- `get_customer_requests` — retrieve requests by customer_id

Note: `get_customer_requests` returns nested `tasks` and `equipment` arrays in the JSON response, even though the action's CDS return type is the flat `CustomerRequests` entity (so these nested arrays are not declared in OData `$metadata`). Clients should rely on the JSON shape, or call `GET /customer-requests/CustomerRequests?$expand=tasks($expand=equipment)` directly on the OData entity if a typed $metadata-backed shape is required.

The `/mcp` endpoint inherits CAP authentication (`auth: 'inherit'`). With the default mocked auth in development, MCP requests must include HTTP Basic credentials for a mock user, e.g. `-u alice:` (user `alice`, no password).

Test with:

```bash
npx @modelcontextprotocol/inspector
```

Connect to `http://localhost:4004/mcp` (provide Basic auth `alice:` in the inspector's auth settings).

## Seed data

One request from `ai-integrations-000` (Antonio Maradiaga) with 3 tasks covering Plaza Pablo Picasso (Madrid), Castellana 85 (Madrid), and Avinguda Diagonal (Barcelona).

## Deploy to CloudFoundry (MTA)

### Prerequisites

| Tool | Install |
| --- | --- |
| `mbt` (Cloud MTA Build Tool) | `npm install -g mbt` |
| `cf` CLI | [SAP BTP docs](https://help.sap.com/docs/btp/sap-business-technology-platform/install-cf-cli) |
| `multiapps` CF plugin | `cf install-plugin multiapps` |

### First-time setup

```bash
# Log in to CF (use --sso if SSO is configured)
cf login -a https://api.cf.eu20-002.hana.ondemand.com/ --sso

# Select org and space when prompted, or set directly:
cf target -o "Developer Advocates_ai-integrations-codejam-2tmfbzpb" -s apps
```

### Build

From `apps/altura-customer-service/`:

```bash
npm install          # installs ui5 cli and other build-time deps
mbt build            # compiles CAP backend + Fiori UI, produces .mtar
```

Output archive: `mta_archives/altura-customer-service_1.0.0.mtar`

### Deploy

```bash
cf deploy mta_archives/altura-customer-service_1.0.0.mtar
```

Two CF apps are created:

| App | Purpose |
|-----|---------|
| `altura-customer-service-srv` | CAP OData + MCP backend |
| `altura-customer-service-app` | Approuter: serves Fiori UI + proxies API |

The **approuter URL** is your single entry point:

| Surface | URL |
|---------|-----|
| Fiori Elements UI | `https://<approuter-url>/index.html` |
| OData v4 | `https://<approuter-url>/customer-requests/` |
| MCP server | `https://<srv-url>/mcp` (direct srv URL) |

Get URLs:
```bash
cf app altura-customer-service-app | grep routes   # approuter
cf app altura-customer-service-srv | grep routes   # srv (for MCP)
```

### Re-deploy after changes

```bash
mbt build && cf deploy mta_archives/altura-customer-service_1.0.0.mtar
```

### Undeploy

```bash
cf undeploy altura-customer-service --delete-services
```

> **Note:** SQLite data does not persist across restarts or redeploys. The database is re-seeded from CSV files (`db/data/`) on each startup.
