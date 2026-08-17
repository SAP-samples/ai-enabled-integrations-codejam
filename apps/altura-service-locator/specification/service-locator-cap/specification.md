# Specification: service-locator-cap

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-cap.md](../guidelines-cap.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` before starting any implementation task
- [x] Invoke the `cap-development` skill from `assets/service-locator-cap/` to set up the CAP project structure
- [x] Install dependencies (`npm install`), validate the project starts (`cds watch`) and responds

## Data Model (R1)

- [x] Create `db/schema.cds` defining a `ServiceCenters` entity in namespace `altura.servicelocator` with the following fields:
  - `ID` — `UUID` key, managed
  - `name` — `String(100)` not null
  - `address` — `String(200)` not null
  - `city` — `String(100)` not null
  - `country` — `String(100)` not null
  - `phone` — `String(30)`
  - `email` — `String(100)`
  - `latitude` — `Decimal(10,7)` not null
  - `longitude` — `Decimal(10,7)` not null
- [x] Run `cds compile db/` to confirm the model compiles without errors

## OData Service Definition (R1, R2)

- [x] Create `srv/service.cds` defining a service named `ServiceLocatorService` at path `/service-locator`
- [x] Expose `ServiceCenters` as a read-only entity (no create/update/delete via OData)
- [x] Declare an unbound action `getNearestServiceCenter` that accepts parameter `address : String` and returns the `ServiceCenters` type (single entity, not a collection)
- [x] Run `cds compile srv/` to confirm the service definition compiles without errors

## Seed Data (R4)

- [x] Create `db/data/altura.servicelocator-ServiceCenters.csv` with the following columns:
  `ID,name,address,city,country,phone,email,latitude,longitude`
- [x] Populate with 1–4 fictional service centers per country, cities based on SAP office locations:
  - **Spain** (SAP offices: Madrid, Barcelona): 2–3 centers
  - **France** (SAP offices: Paris, Mougins/Sophia Antipolis): 2 centers
  - **Germany** (SAP offices: Walldorf, Berlin, Munich, Frankfurt): 3–4 centers
  - **Portugal** (SAP offices: Lisbon, Porto): 2 centers
  - **India** (SAP offices: Bangalore, Mumbai, Pune, Hyderabad): 3–4 centers
- [x] Each record must include a realistic (fictional) name (e.g. "Altura Coffee Service — Madrid Centro"), street address, valid phone number, email address in the format `service.<city>@alturacoffe.com`, and accurate latitude/longitude for the city
- [x] Verify total row count is between 12 and 17 (1–4 per country × 5 countries)

## Nearest Service Center Action — Text-Match Path (R3)

- [x] Create `srv/service.js` (or `srv/service-locator-service.js`) as the CAP service handler
- [x] Implement the `getNearestServiceCenter` handler:
  - [x] Step 1 — Text match: query all `ServiceCenters`; filter to records where `city` or `country` contains the input `address` (case-insensitive substring match)
  - [x] If one or more matches found, run Haversine distance calculation against each matched record using a centroid coordinate for the matched city/country (use the matched records' own stored `latitude`/`longitude`) and return the record with the minimum distance
  - [x] If exactly one matched record exists, return it directly without Haversine (distance is zero — it's an exact city/country hit)

## Nearest Service Center Action — Geocoding Fallback Path (R3)

- [x] If the text-match step returns zero results, call the Nominatim geocoding API:
  - URL: `https://nominatim.openstreetmap.org/search`
  - Query params: `q=<address>&format=json&limit=1`
  - Set a descriptive `User-Agent` header: `AlturaServiceLocator/1.0`
  - Use Node.js built-in `fetch` (Node 18+) — no external HTTP client libraries
- [x] Parse the response: extract `lat` and `lon` from the first result
- [x] If Nominatim returns an empty array or an HTTP error, throw a CAP `Error` with status 404 and message `"No service center found for the provided address"`
- [x] Run Haversine distance from the geocoded coordinates against all stored `ServiceCenters`; return the record with minimum distance

## Haversine Helper (R3)

- [x] Implement a `haversineKm(lat1, lon1, lat2, lon2)` helper function in `srv/service.js` (or a shared `srv/lib/haversine.js` module)
- [x] Formula: standard Haversine using Earth radius 6371 km; return distance in km as a number
- [x] The helper must be a pure function with no side effects

## Error Handling (R3)

- [x] If `ServiceCenters` table is empty (zero records), return a CAP `Error` with status 404 and message `"No service centers available"`
- [x] If `address` parameter is missing or blank, return a CAP `Error` with status 400 and message `"address parameter is required"`
- [x] Nominatim network errors (timeout, DNS failure) must be caught and returned as a CAP `Error` with status 503 and message `"Geocoding service unavailable — please try again later"`

## OData $filter by Country (R2)

- [x] Confirm that `$filter=country eq 'Spain'` (and for each other supported country) returns only the matching records — this is handled by CAP's built-in OData filter; no custom handler code required
- [x] Manually verify with `curl` during `cds watch` that filtered results are correct for at least two countries

## Tests

- [x] Write unit tests for the `haversineKm` helper: known coordinate pairs with expected distances (tolerance ±1 km)
- [x] Write integration tests for the `getNearestServiceCenter` action:
  - [x] Text-match path: input `"Madrid"` returns a Spanish service center
  - [x] Text-match path: input `"India"` returns an Indian service center
  - [x] Geocoding fallback path: mock Nominatim to return coordinates for a known city not in any center's city/country field; verify the nearest center by distance is returned
  - [x] Error path: mock empty `ServiceCenters` table; verify 404 error
  - [x] Error path: blank `address`; verify 400 error
  - [x] Error path: mock Nominatim failure; verify 503 error
- [x] Run all tests and confirm they pass

## MTA Deployment File

- [x] Create `mta.yaml` at `assets/service-locator-cap/mta.yaml` with:
  - `ID: altura-service-locator` and `version: 1.0.0`
  - One module of type `nodejs` named `altura-service-locator-srv`:
    - `path: .`
    - Build parameter: `builder: npm`, `build-result: gen/srv`
    - `command: npm start`
    - Properties: `NODE_ENV: production`
    - CF resource limits: `memory: 256M`, `disk-quota: 512M`
  - No HDI deployer module, no `hana` resource — SQLite/in-memory persistence only
- [x] Confirm `package.json` has a `"start": "cds-serve"` script so the CF runtime can start the application

## Validation

- [x] Run `cds compile srv/` — zero errors
- [x] Run `cds watch` and confirm:
  - [x] `GET /odata/v4/service-locator/$metadata` returns EDMX without error (M4 achieved)
  - [x] `GET /odata/v4/service-locator/ServiceCenters` returns all seeded records (M1 achieved)
  - [x] `GET /odata/v4/service-locator/ServiceCenters?$filter=country eq 'Germany'` returns only German centers (M2 achieved)
  - [x] `POST /odata/v4/service-locator/getNearestServiceCenter` with body `{"address":"Lisbon"}` returns a Portuguese service center (M3 achieved)
