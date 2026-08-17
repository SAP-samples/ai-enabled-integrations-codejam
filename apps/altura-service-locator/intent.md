# Altura Coffee Co. Service Center Locator

Altura Coffee Co. — a Spain-headquartered coffee company — needs a CAP application to manage and expose service center data worldwide.

## Business challenge

Build a CAP application that maintains a catalog of Altura Coffee Co. service centers across Spain, France, Germany, Portugal, and India. The application must expose an OData API that lets consumers (1) filter service centers by country and (2) find the nearest service center to a given address. Each service center record includes name, address, city, country, phone number, and email address. Seed data should reflect SAP office locations in each supported country.

## Key Milestones

1. Service center catalog seeded with fictional data based on SAP office locations in Spain, France, Germany, Portugal, and India (1–4 centers per country)
2. Country-filter API endpoint returns correct subset of service centers
3. Nearest-center endpoint accepts a free-form address and returns the closest service center using distance calculation
4. Application deploys and is reachable via OData v4 URL

## Business Architecture (RBA)

### End-to-End Process

Field Service (E2E)

### Process Hierarchy

```
Field Service (E2E)
└── Request to Quote (field service)
    └── Provide customer service and support (field service) [BPS-365_007]
        └── Enable omnichannel customer service
    └── Sell service (field service) [BPS-360_012]
        └── Manage service booking via self-service
└── Order to Fulfill (field service)
    └── Manage customer orders and contracts (field service) [BPS-361_017]
        └── Manage service contracts and SLAs
```

### Summary

The service center locator maps to the Field Service E2E, specifically the self-service customer engagement sub-processes. The core need — helping customers locate and reach the right service center — is the entry point to the broader field service lifecycle.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ------------------ | ---- | ------------------- |
| Service center data storage and retrieval | No standard SAP product covers a lightweight, custom service center registry | — | — | — | Yes | Custom CAP entity required; no S/4HANA or FSM product covers this exact use case without significant overkill |
| Filter service centers by country | Standard OData $filter covers this at the framework level | `sap.s4:apiResource:CE_MANAGELOCATION_0001:v1` (reference only) | — | — | No | Addressed natively by CAP OData $filter; S/4 Location API is reference only, not reused |
| Find nearest service center by address | No standard SAP product provides a distance-based nearest-center lookup | — | — | — | Yes | Requires geocoding logic (Haversine formula or external geocoding API) within a CAP custom action |
| Self-service customer engagement channel | SAP Field Service Management — Self-Service Engagement (SC952) | — | — | — | Maybe | FSM provides self-service but is far heavier than needed; CAP API is sufficient for this scope |
| Omnichannel customer service support | SAP Service Cloud V2 — Omnichannel Customer Engagement (SC3409) | — | — | — | Maybe | Out of scope for this request; the locator app is a data/API layer, not a service management platform |

### Key findings

- No standard SAP product provides a lightweight service center registry with nearest-location search; custom CAP development is the correct approach.
- The Location API (`CE_MANAGELOCATION_0001`) exists in S/4HANA but is designed for internal logistics locations, not customer-facing service center directories — not reused.
- No MCP server is available for the discovered Location API ORD ID.
- Distance-based nearest-center logic requires either a built-in Haversine calculation (using pre-stored coordinates per service center) or integration with an external geocoding service; coordinates should be stored alongside the service center record.
- SAP Field Service Management and SAP Service Cloud cover the broader field service lifecycle but are disproportionate for this standalone locator requirement.
- Seed data for service centers should be based on published SAP office locations in Spain, France, Germany, Portugal, and India (1–4 per country).

## Recommendations

### CAP Application for Altura Coffee Co. Service Center Locator

#### Executive Summary

Custom CAP app exposes OData API for service center lookup.

#### Recommended Solution

Build a CAP (Cloud Application Programming Model) Node.js application with:
- A `ServiceCenters` entity with fields: name, address, city, country, phone, email, latitude, longitude
- An OData v4 service exposing `ServiceCenters` with standard `$filter=country eq '...'` support
- A custom CAP action `getNearestServiceCenter(address)` that accepts a free-form address, resolves it to coordinates (via Haversine against stored lat/long), and returns the nearest center
- Seed data (`data/ServiceCenters.csv`) with 1–4 fictional service centers per country (Spain, France, Germany, Portugal, India), locations based on SAP office cities
- SQLite persistence for local development; SAP HANA Cloud-compatible for production

#### Recommended solution category

CAP App

#### Intent fit
95%
