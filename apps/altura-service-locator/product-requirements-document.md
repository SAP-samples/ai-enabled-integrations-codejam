# Product Requirements Document (PRD)

**Title:** Altura Coffee Co. Service Center Locator  
**Date:** 2026-08-14  
**Owner:** Altura Coffee Co.  
**Solution Category:** CAP App

## Product Purpose & Value Proposition

**Elevator Pitch:**  
Altura Coffee Co. customers worldwide need to find the nearest authorized service center quickly. Today there is no centralized, machine-readable registry. This CAP application provides a lightweight OData API that any channel — web, mobile, or chatbot — can query to locate service centers by country or by proximity to a given address.

**Business Need:**  
Altura Coffee Co. operates service centers across Spain, France, Germany, Portugal, and India, with headquarters in Spain. Without a dedicated service center directory exposed as an API, downstream systems and customer-facing channels cannot surface this information reliably. The gap is a custom-built catalog and proximity search capability.

**Expected Value:**  
- Customers can self-serve to find the correct service center, reducing inbound contact-center volume.
- Downstream integrations (websites, mobile apps, service booking flows) have a single, authoritative data source for service center information.
- The API-first approach allows future channels to consume the data without additional backend work.

**Product Objectives (Prioritized):**

1. Expose a queryable OData v4 API for service center data, filterable by country.
2. Provide a nearest-service-center action that accepts a free-form address and returns the closest center.
3. Seed the catalog with accurate, representative data (based on SAP office locations) for all five supported countries.

## User Profiles & Personas

### Primary Persona: Customer (End Consumer)

Maria is a 38-year-old coffee enthusiast based in Lisbon, Portugal. She purchased an Altura Coffee machine 18 months ago and needs it serviced. She visits the Altura Coffee website to find a nearby service center. She is comfortable using web and mobile apps but does not interact with APIs directly — she depends on the frontend to surface the right location for her.

**Pain point:** Without a locator feature, Maria must contact support by phone or email to find a service center, adding delay and friction to her service experience.

### Secondary Persona: Application Developer / System Integrator

Carlos is a 32-year-old developer at Altura Coffee Co. He builds and maintains the customer-facing website and internal tools. He needs a reliable, documented OData API to integrate service center data into multiple surfaces (website store locator, chatbot, service booking page). He values standard protocols, clear data contracts, and minimal maintenance overhead.

**Pain point:** Without a central API, Carlos must hardcode service center data in each application and manually update it whenever a center opens, closes, or changes contact details.

### Other User Types

- **Service Operations Manager**: Responsible for the service center network; indirectly benefits from accurate, up-to-date data being exposed through the API.

## User Goals & Tasks

### For Maria (Customer):

**Goals:**
- Find the service center closest to her home or current location.
- Retrieve contact details (phone, email) for a service center in her country.

**Key Tasks:**
- Enter her address or select her country on the website to get a filtered list of service centers.
- View the nearest service center result with name, address, and contact details.

### For Carlos (Application Developer):

**Goals:**
- Integrate service center data into the Altura Coffee website and other channels via a stable API.
- Query service centers by country for country-specific pages.
- Call a nearest-center endpoint with a customer-supplied address to power a store locator widget.

**Key Tasks:**
- Call `GET /ServiceCenters?$filter=country eq 'Portugal'` to retrieve all centers in a given country.
- Call the `getNearestServiceCenter` action with an address string to receive the single nearest center record.

## Product Principles

1. **API-First**: The application is a data and logic layer; it does not own a UI. All value is delivered through the OData API.
2. **Standard Before Custom**: Use CAP's built-in OData $filter for country queries; custom code only where the framework does not provide a solution (proximity search).
3. **Seed Data as Ground Truth**: The initial seed data is the authoritative source for service center locations; no external system feeds it at launch.

## Business Context

**Current State:**  
No machine-readable service center registry exists. Service center information is either embedded in static web pages or managed in unstructured documents. Customers and internal systems cannot query it programmatically.

**Strategic Alignment:**  
A customer-facing service locator is a foundational capability for the Field Service self-service sub-process. It is the first step in the customer's service journey — before booking, before a technician visit, before any warranty claim.

**Success Criteria:**

- All five countries return results when queried via `$filter=country eq '...'`.
- `getNearestServiceCenter` returns the correct nearest center for a test address in each supported country.
- Application starts and serves OData responses locally without errors.
- Seed data contains 1–4 service centers per country (total: 5–20 centers).

## Goals and Non-Goals

### Goals (In Scope)

- Maintain a `ServiceCenters` entity with fields: name, address, city, country, phone, email, latitude, longitude.
- Expose an OData v4 service with standard `$filter` support for country-based queries.
- Implement a `getNearestServiceCenter(address: String)` custom action that returns the closest service center using Haversine distance against stored coordinates.
- Seed the database with fictional service centers based on SAP office cities in Spain, France, Germany, Portugal, and India (1–4 per country).
- Support SQLite for local development.

### Non-Goals (Out of Scope)

- A user interface or frontend application.
- External geocoding as the sole lookup strategy — text-match against city/country fields is the primary path; geocoding is a fallback only.
- Service booking, appointment scheduling, or CRM integration.
- Authentication or authorization on the API.
- SAP Field Service Management or SAP Service Cloud integration.
- Support for countries beyond the five listed.

## Requirements

### Must-Have Requirements

**R1: Service Center Entity and OData Exposure**

- **Problem to Solve**: Developers have no API to query service center data.
- **User Story**: As a developer, I need an OData v4 endpoint that lists all service centers so that I can integrate this data into any channel.
- **Acceptance Criteria**:
  - Given the service is running, when I call `GET /odata/v4/service-locator/ServiceCenters`, then I receive a JSON response with all seeded service centers.
  - Each record contains: name, address, city, country, phone, email, latitude, longitude.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 1

**R2: Country Filter**

- **Problem to Solve**: Channels need to display service centers relevant to a specific country.
- **User Story**: As a developer, I need to filter service centers by country so that I can show only relevant results to customers in a given market.
- **Acceptance Criteria**:
  - Given service centers exist for Spain and Portugal, when I call `GET /ServiceCenters?$filter=country eq 'Spain'`, then only Spanish service centers are returned.
  - The filter works for all five supported countries.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 2

**R3: Nearest Service Center Action**

- **Problem to Solve**: Customers need to find the closest service center to their location using a free-form address.
- **User Story**: As a developer, I need a nearest-center action that accepts a free-form address string and returns the single closest service center so that I can power a store locator feature.
- **Acceptance Criteria**:
  - Given a free-form address string is provided, when I call the `getNearestServiceCenter` action, the system first attempts a text match against city and country fields of all service centers.
  - If a text match is found, the nearest center is determined from that matched subset using Haversine distance.
  - If no text match is found, the action calls the Nominatim (OpenStreetMap) geocoding API to resolve the address to latitude/longitude coordinates, then runs Haversine distance against all stored centers.
  - The single nearest service center is returned in both paths.
  - If geocoding fails or returns no result, the action returns an informative error.
  - If no centers exist, the action returns an informative error.
- **Maps to Objective**: Objective 2
- **Priority Rank**: 3

**R4: Seed Data**

- **Problem to Solve**: The catalog must be pre-populated so the API returns useful data immediately.
- **User Story**: As a service operations manager, I need the application to ship with representative service center data so that the API is usable from day one.
- **Acceptance Criteria**:
  - Seed data file contains 1–4 service centers for each of: Spain, France, Germany, Portugal, India.
  - Each center's city is based on a city where SAP has an office presence.
  - Each record includes realistic (fictional) name, address, phone, email, and valid latitude/longitude coordinates.
- **Maps to Objective**: Objective 3
- **Priority Rank**: 4

## Solution Architecture

**Architecture Overview:**  
A single CAP Node.js application exposing one OData v4 service. The service is backed by SQLite for local development. Seed data is loaded from a CSV file at startup. One custom action handles nearest-center proximity logic.

**Key Components:**

- **CDS Data Model** (`db/schema.cds`): Defines the `ServiceCenters` entity with all required fields including coordinates.
- **OData Service Definition** (`srv/service.cds`): Exposes `ServiceCenters` as a read-only entity set and declares the `getNearestServiceCenter` unbound action.
- **Service Handler** (`srv/service.js`): Implements the `getNearestServiceCenter` action. Uses a two-step strategy: (1) text-match against city/country fields; (2) if no match, calls Nominatim (OpenStreetMap) geocoding API to resolve the address to coordinates, then applies Haversine distance against all stored centers.
- **Seed Data** (`db/data/ServiceCenters.csv`): CSV file with 1–4 rows per supported country, coordinates based on SAP office city locations.

**Integration Points:**

- **Nominatim (OpenStreetMap) Geocoding API** (`https://nominatim.openstreetmap.org/search`): Called as a fallback from the `getNearestServiceCenter` action when the text-match step finds no matching service centers. Read-only. Requires a `User-Agent` header per Nominatim usage policy. No API key required. Rate limit: 1 request/second.

**Deployment Environments:**

- **Local (dev)**: SQLite in-memory or file-based; `cds watch` for live reload.
- **Production (target)**: SAP HANA Cloud as persistence layer; deployed to SAP BTP Cloud Foundry or Kyma.

### Configuration & Data

**Configuration Scope:**  
Standard CAP project configuration (`package.json` + `cdsrc`). No external system credentials required at launch.

**Organisational & Master Data:**

- Service center records are the only master data. They are owned by the service operations team and seeded from the CSV at first deployment.

**Data Migration & Cutover:**

- Not applicable at launch. Seed data is the initial state; future updates are handled via standard CAP database migrations.

## Milestones

### M1: Seed Data Loaded

- **Description**: The service center catalog is populated with representative data for all five countries.
- **Achieved when**: The application starts and `GET /ServiceCenters` returns at least one record for each of Spain, France, Germany, Portugal, and India.
- **Log on achievement**: `M1.achieved: seed data loaded — service centers available for all 5 countries`
- **Log on miss**: `M1.missed: seed data load failed or missing countries in catalog`

### M2: Country Filter Operational

- **Description**: The OData `$filter` by country returns correct, non-empty results.
- **Achieved when**: A `$filter=country eq '<country>'` query for each supported country returns at least one record.
- **Log on achievement**: `M2.achieved: country filter validated for all supported countries`
- **Log on miss**: `M2.missed: country filter returned empty or incorrect results for one or more countries`

### M3: Nearest Service Center Action Operational

- **Description**: The `getNearestServiceCenter` action returns the correct nearest center for a test address.
- **Achieved when**: Calling the action with a known address returns the expected nearest service center based on Haversine distance.
- **Log on achievement**: `M3.achieved: getNearestServiceCenter action returns correct nearest center`
- **Log on miss**: `M3.missed: getNearestServiceCenter action failed or returned incorrect result`

### M4: Application Reachable via OData v4 URL

- **Description**: The application is running and its OData service metadata is accessible.
- **Achieved when**: `GET /odata/v4/service-locator/$metadata` returns a valid EDMX document without errors.
- **Log on achievement**: `M4.achieved: OData v4 service metadata endpoint reachable`
- **Log on miss**: `M4.missed: service failed to start or metadata endpoint unreachable`

## Risks, Assumptions, and Dependencies

### Risks

- **Coordinate accuracy**: Seed data uses fictional service center locations approximated from SAP office cities. If coordinates are incorrect, the nearest-center calculation will produce wrong results. Mitigation: validate coordinates against a map before seeding.
- **Nominatim availability**: The fallback geocoding path depends on the public Nominatim service. If it is unreachable, addresses that do not match any city/country text will fail to resolve. Mitigation: return a clear error to the caller; do not silently return wrong results.
- **Nominatim rate limit**: Nominatim enforces 1 request/second. At low call volume this is not a concern, but burst usage could trigger throttling. Mitigation: acceptable at current scope; revisit if call volume grows.

### Assumptions

- The `getNearestServiceCenter` action accepts a free-form address string. The text-match step covers the common case (city or country name in the input); Nominatim geocoding handles the rest.
- SQLite is sufficient for local development and demonstration; production deployment to SAP HANA Cloud is a future step.
- No authentication is required on the API for the initial release.
- Nominatim's acceptable-use policy (1 req/s, descriptive `User-Agent`) is sufficient for the expected call volume.

### Dependencies

- CAP SDK (`@sap/cds`) and Node.js runtime.
- Nominatim (OpenStreetMap) public geocoding API — no key required; used as fallback only.
