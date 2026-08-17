/**
 * Haversine formula — returns distance in km between two lat/lon points.
 * Earth radius: 6371 km.
 */
export function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Return the center with the minimum Haversine distance from (lat, lon).
 */
export function findNearest(centers, lat, lon) {
  let nearest = null;
  let minDist = Infinity;
  for (const c of centers) {
    const d = haversineKm(lat, lon, Number(c.latitude), Number(c.longitude));
    if (d < minDist) { minDist = d; nearest = c; }
  }
  return nearest;
}

export default function (srv) {
  const { ServiceCenters } = srv.entities;

  srv.on('getNearestServiceCenter', async req => {
    const { address } = req.data;

    if (!address || !address.trim()) {
      return req.reject(400, 'address parameter is required');
    }

    const all = await SELECT.from(ServiceCenters).columns(
      'ID', 'name', 'address', 'city', 'country', 'phone', 'email', 'latitude', 'longitude'
    );

    if (!all.length) {
      return req.reject(404, 'No service centers available');
    }

    // Step 1 — text match against city and country (case-insensitive)
    const term = address.trim().toLowerCase();
    const matched = all.filter(c =>
      c.city.toLowerCase().includes(term) ||
      c.country.toLowerCase().includes(term)
    );

    if (matched.length === 1) return matched[0];

    if (matched.length > 1) {
      const avgLat = matched.reduce((s, c) => s + Number(c.latitude), 0) / matched.length;
      const avgLon = matched.reduce((s, c) => s + Number(c.longitude), 0) / matched.length;
      return findNearest(matched, avgLat, avgLon);
    }

    // Step 2 — Nominatim geocoding fallback
    let geocoded;
    try {
      const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address)}&format=json&limit=1`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'AlturaServiceLocator/1.0' }
      });
      if (!res.ok) throw new Error(`Nominatim HTTP ${res.status}`);
      geocoded = await res.json();
    } catch {
      return req.reject(503, 'Geocoding service unavailable — please try again later');
    }

    if (!geocoded.length) {
      return req.reject(404, 'No service center found for the provided address');
    }

    const lat = parseFloat(geocoded[0].lat);
    const lon = parseFloat(geocoded[0].lon);
    return findNearest(all, lat, lon);
  });
}
