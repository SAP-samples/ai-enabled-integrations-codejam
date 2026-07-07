# Altura Coffee Co. — Website

Demo website for the AI-enabled Integrations CodeJam. Two-page Vite + TypeScript site that allows customers to browse Altura Coffee Co.'s products and submit support requests. Requests are published as [CloudEvents](https://cloudevents.io/) to SAP Integration Suite, advanced event mesh (AEM) via its REST API.

## Pages

| Page | File | Description |
|------|------|-------------|
| Homepage | `index.html` | Brand landing page with product overview and support CTA |
| Support request | `support.html` | Form with four mandatory fields that publishes to AEM on submit |

## Tech stack

- **Vite** — build tool and dev server
- **TypeScript** — type-safe form logic
- **Express** — thin Node.js server that hosts the built site and proxies form submissions to AEM (keeps credentials server-side and avoids CORS)
- **Vanilla CSS** — no UI framework; all styles in `src/style.css`

## Prerequisites

- Node.js 20+
- npm 9+
- Access to an SAP Integration Suite, advanced event mesh instance (service key from your instructor 🔐)

## Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Copy the env example and fill in your AEM credentials:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set the following values from your AEM service key:

   | Variable | Description |
   |----------|-------------|
   | `AEM_USERNAME` | Basic auth username (`username`) |
   | `AEM_PASSWORD` | Basic auth password (`password`) |
   | `AEM_BASE_URL` | AEM REST base URL (`uri`) |
   | `AEM_TOPIC` | Topic to publish to (e.g. `altura/website/support/request/v1/submitted`) |

   These vars are **server-side only** (no `VITE_` prefix). Credentials never reach the browser.

3. In one terminal, start the Express backend:

   ```bash
   npm start
   ```

   Listens on [http://localhost:3000](http://localhost:3000).

4. In a second terminal, start the Vite dev server:

   ```bash
   npm run dev
   ```

   Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api/*` to the backend.

## How it works

When a user submits the support form, `src/support.ts`:

1. Validates all fields client-side
2. `POST /api/support-request` with the plain JSON payload
3. `server.js` validates, wraps in a CloudEvent, adds Basic auth, and publishes to the AEM topic

The CloudEvent payload sent to AEM:

```json
{
  "specversion": "1.0",
  "type": "altura.coffee.support.request.created.v1",
  "source": "/altura-coffee-website/support-form",
  "id": "<uuid>",
  "time": "<iso-timestamp>",
  "datacontenttype": "application/json",
  "data": {
    "customer_id": "ai-integrations-001",
    "contact_name": "Antonio Maradiaga",
    "contact_email": "SAP Spain",
    "country": "Spain",
    "customer_request": "We have a La Marzocco Micra..."
  }
}
```

The topic is resolved per request as `${AEM_TOPIC}/${customer_id}`.

## Build

```bash
npm run build
```

Output goes to `dist/`. Both `index.html` and `support.html` are included as separate entry points. `server.js` serves `dist/` in production.

## Deploy to Cloud Foundry

The site runs as a Node.js app on CF: Express serves the built `dist/` and proxies form submissions to AEM.

### Deploy prerequisites

- `cf` CLI logged in and targeted at the right org / space
  
   ```bash
   # Log in to CF (use --sso if SSO is configured)
   cf login -a https://api.cf.eu20-002.hana.ondemand.com/ --sso

   # Select org and space when prompted, or set directly:
   cf target -o "Developer Advocates_ai-integrations-codejam-2tmfbzpb" -s apps
   ```

- AEM service key values on hand

### Steps

1. Build the site locally (CF only installs production deps, so `vite`/`tsc` are not available on the platform):

   ```bash
   npm run build
   ```

2. Push the app **without starting it** so env vars can be set first:

   ```bash
   cf push --no-start
   ```

3. Set the AEM environment variables:

   ```bash
   cf set-env altura-coffee-website AEM_USERNAME '<username>'
   cf set-env altura-coffee-website AEM_PASSWORD '<password>'
   cf set-env altura-coffee-website AEM_BASE_URL 'https://<your-aem-instance>.messaging.solace.cloud:9443'
   cf set-env altura-coffee-website AEM_TOPIC 'altura/website/support/request/v1/submitted'
   ```

4. Start the app:

   ```bash
   cf start altura-coffee-website
   ```

5. Open the assigned route:

   ```bash
   cf app altura-coffee-website
   ```

### Updating the app

After code changes, rebuild and push:

```bash
npm run build
cf push
```

Env vars persist across pushes. If you only change env vars, `cf restage altura-coffee-website` picks them up without redeploying code.

### Deployment files

| File           | Purpose                                                             |
| -------------- | ------------------------------------------------------------------- |
| `manifest.yml` | CF app definition — `nodejs_buildpack`, `npm start`, 128M memory    |
| `.cfignore`    | Excludes `src/`, `node_modules/`, TS/Vite config from the CF upload |
| `server.js`    | Express app: serves `dist/` + `POST /api/support-request`           |
