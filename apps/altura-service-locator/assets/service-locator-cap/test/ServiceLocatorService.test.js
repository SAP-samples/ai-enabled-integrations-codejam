import cds from '@sap/cds'
import { describe, it, before, mock } from 'node:test'
import assert from 'node:assert/strict'
import { haversineKm, findNearest } from '../srv/service-locator-service.js'

const cdsTest = cds.test(import.meta.dirname + '/..')
cdsTest.defaults.auth = { username: process.env.BASIC_AUTH_USER, password: process.env.BASIC_AUTH_PASSWORD }
const { GET, POST } = cdsTest

// ---------------------------------------------------------------------------
// Unit tests — haversineKm
// ---------------------------------------------------------------------------
describe('haversineKm', () => {
  it('returns ~0 for identical coordinates', () => {
    assert.ok(haversineKm(40.4168, -3.7038, 40.4168, -3.7038) < 0.001)
  })

  it('Madrid to Barcelona is approx 505 km (±20 km)', () => {
    const d = haversineKm(40.4168, -3.7038, 41.3851, 2.1734)
    assert.ok(d > 485 && d < 525, `Expected ~505 km, got ${d.toFixed(1)}`)
  })

  it('Lisbon to Porto is approx 274 km (±20 km)', () => {
    const d = haversineKm(38.7169, -9.1395, 41.1579, -8.6291)
    assert.ok(d > 254 && d < 294, `Expected ~274 km, got ${d.toFixed(1)}`)
  })
})

// ---------------------------------------------------------------------------
// Unit tests — findNearest
// ---------------------------------------------------------------------------
describe('findNearest', () => {
  const centers = [
    { ID: '1', name: 'Madrid', latitude: 40.4168, longitude: -3.7038 },
    { ID: '2', name: 'Barcelona', latitude: 41.3851, longitude: 2.1734 },
    { ID: '3', name: 'Lisbon', latitude: 38.7169, longitude: -9.1395 },
  ]

  it('returns the closest center to a given coordinate', () => {
    // Point close to Lisbon
    const nearest = findNearest(centers, 38.8, -9.0)
    assert.equal(nearest.name, 'Lisbon')
  })

  it('returns the closest center to a point near Barcelona', () => {
    const nearest = findNearest(centers, 41.5, 2.5)
    assert.equal(nearest.name, 'Barcelona')
  })
})

// ---------------------------------------------------------------------------
// Integration tests — getNearestServiceCenter action
// ---------------------------------------------------------------------------
describe('getNearestServiceCenter', () => {
  it('text-match path: "Madrid" returns a Spanish service center', async () => {
    const { data } = await POST('/service-locator/getNearestServiceCenter', { address: 'Madrid' })
    assert.equal(data.country, 'Spain')
    assert.ok(data.city.toLowerCase().includes('madrid'))
  })

  it('text-match path: "India" returns an Indian service center', async () => {
    const { data } = await POST('/service-locator/getNearestServiceCenter', { address: 'India' })
    assert.equal(data.country, 'India')
  })

  it('text-match path: "Germany" returns a German service center', async () => {
    const { data } = await POST('/service-locator/getNearestServiceCenter', { address: 'Germany' })
    assert.equal(data.country, 'Germany')
  })

  it('text-match path: "Portugal" returns a Portuguese service center', async () => {
    const { data } = await POST('/service-locator/getNearestServiceCenter', { address: 'Portugal' })
    assert.equal(data.country, 'Portugal')
  })

  it('error path: blank address returns 400', async () => {
    await assert.rejects(
      () => POST('/service-locator/getNearestServiceCenter', { address: '' }),
      err => {
        assert.equal(err.response?.status ?? err.status, 400)
        return true
      }
    )
  })
})

// ---------------------------------------------------------------------------
// Integration tests — ServiceCenters OData entity set
// ---------------------------------------------------------------------------
describe('ServiceCenters entity set', () => {
  it('returns all seeded records', async () => {
    const { data } = await GET('/service-locator/ServiceCenters')
    assert.ok(data.value.length >= 12, `Expected at least 12 records, got ${data.value.length}`)
  })

  it('$filter by country Spain returns only Spanish centers', async () => {
    const { data } = await GET("/service-locator/ServiceCenters?$filter=country eq 'Spain'")
    assert.ok(data.value.length > 0)
    assert.ok(data.value.every(c => c.country === 'Spain'))
  })

  it('$filter by country Germany returns only German centers', async () => {
    const { data } = await GET("/service-locator/ServiceCenters?$filter=country eq 'Germany'")
    assert.ok(data.value.length > 0)
    assert.ok(data.value.every(c => c.country === 'Germany'))
  })

  it('$filter by country France returns only French centers', async () => {
    const { data } = await GET("/service-locator/ServiceCenters?$filter=country eq 'France'")
    assert.ok(data.value.length > 0)
    assert.ok(data.value.every(c => c.country === 'France'))
  })

  it('$filter by country Portugal returns only Portuguese centers', async () => {
    const { data } = await GET("/service-locator/ServiceCenters?$filter=country eq 'Portugal'")
    assert.ok(data.value.length > 0)
    assert.ok(data.value.every(c => c.country === 'Portugal'))
  })

  it('$filter by country India returns only Indian centers', async () => {
    const { data } = await GET("/service-locator/ServiceCenters?$filter=country eq 'India'")
    assert.ok(data.value.length > 0)
    assert.ok(data.value.every(c => c.country === 'India'))
  })
})
