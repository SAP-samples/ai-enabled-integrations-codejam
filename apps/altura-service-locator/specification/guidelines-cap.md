# CAP Guidelines

Technical constraints and patterns for building CAP Apps. Follow these throughout specification execution.

## Tech Stack

- CAP (Cloud Application Programming Model) — Node.js runtime
- Frontend (React)
- Deployment target: SAP BTP Cloud Foundry
- Database: SQLite (local dev) or in-memory (CF deployment) — no HANA Cloud required

## Project Structure

- CAP project lives in `assets/<asset-name>/`
- The `cap-development` skill handles project init, modeling, testing, and frontend scaffolding

## Key Constraints

- You MUST follow the `cap-development` skill for ALL CAP development (modeling, handlers, data, testing, frontend)
- Read the skill before writing any tasks to ensure correct patterns
- Only use public APIs; mock any private systems (like S/4HANA) with minimal mock data
- No Git operations, no authentication, no documentation/READMEs
- No `.env` files (environment variables supplied at runtime)
- No HANA Cloud or HDI container — use SQLite for local dev; the CF deployment uses an in-memory or SQLite-based persistence without HDI

## MTA Deployment

- Create an `mta.yaml` at the root of the CAP project (`assets/<asset-name>/mta.yaml`) for CF deployment
- The MTA must include:
  - A `nodejs` module for the CAP server (`srv`) with `npm start` as the build command
  - No HDI deployer module and no `hana` resource — SQLite/in-memory only
  - `memory: 256M` and `disk-quota: 512M` as CF resource limits
  - `NODE_ENV: production` set as an environment variable on the srv module
- The `package.json` `start` script must invoke `cds-serve` (or `node node_modules/@sap/cds/bin/cds-serve`) so the CF runtime can start the app correctly

## asset.yaml

Create `assets/<asset-name>/asset.yaml` with this content (replace placeholders):

```yaml
apiVersion: asset.sap/v1
kind: Asset
type: cap-app
metadata:
  name: {{application-name}}
components:
  # CAP backend
  - name: srv
    buildPath: .
    outputPath: gen/srv
    provides:
      endpoints:
        - path: /odata/v4
          port: 4004
          protocol: http
      protocols: [odata-v4, rest]
    port: 4004
```

## CAP Development

- MUST follow the `cap-development` skill for all modeling, handlers, data, testing, and frontend
- Read the skill before writing any code

## Testing

- CRITICAL: never skip testing after adding custom handler logic
- Only test custom logic — never test generic CRUD
- Follow testing guidelines in the `cap-development` skill (`references/write-tests.md`)

## Validation

- Run `cds compile srv/` regularly to validate CDS models compile without errors
- Run `cds watch` and curl endpoints to confirm service starts and responds
- Write tests for custom handler logic
- All source code must compile, all imports must resolve
- Fix validation failures immediately before proceeding
- Implement all backend functionality from PRD also in the UI
