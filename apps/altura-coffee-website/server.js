import express from 'express'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const app = express()
const port = process.env.PORT || 3000

const AEM_USERNAME = process.env.AEM_USERNAME
const AEM_PASSWORD = process.env.AEM_PASSWORD
const AEM_BASE_URL = process.env.AEM_BASE_URL
const AEM_TOPIC = process.env.AEM_TOPIC

if (!AEM_USERNAME || !AEM_PASSWORD || !AEM_BASE_URL || !AEM_TOPIC) {
  console.error('Missing AEM_* environment variables')
  process.exit(1)
}

app.use(express.json({ limit: '64kb' }))

const REQUIRED_FIELDS = ['customer_id', 'contact_name', 'contact_email', 'country', 'customer_request']

app.post('/api/support-request', async (req, res) => {
  const payload = req.body || {}
  for (const field of REQUIRED_FIELDS) {
    if (typeof payload[field] !== 'string' || payload[field].trim().length === 0) {
      return res.status(400).json({ error: `Missing or empty field: ${field}` })
    }
  }

  const sanitized = Object.fromEntries(
    REQUIRED_FIELDS.map(f => [f, String(payload[f]).trim()])
  )
  const resolvedTopic = `${AEM_TOPIC}/${encodeURIComponent(sanitized.customer_id)}`
  const topicEncoded = encodeURIComponent(resolvedTopic)
  const url = `${AEM_BASE_URL}/${topicEncoded}`
  const credentials = Buffer.from(`${AEM_USERNAME}:${AEM_PASSWORD}`).toString('base64')

  console.log(`[aem] publishing to topic '${resolvedTopic}'`)

  const cloudEvent = {
    specversion: '1.0',
    type: 'altura.coffee.support.request.created.v1',
    source: '/altura-coffee-website/support-form',
    id: randomUUID(),
    time: new Date().toISOString(),
    datacontenttype: 'application/json',
    data: sanitized,
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Basic ${credentials}`,
        'Content-Type': 'application/cloudevents+json',
        'x-qos': '0',
      },
      body: JSON.stringify(cloudEvent),
    })
    if (!response.ok) {
      const body = await response.text().catch(() => '')
      console.error(`[aem] publish failed ${response.status}: ${body}`)
      return res.status(502).json({ error: `Upstream publish failed (${response.status})` })
    }
    return res.json({ topic: resolvedTopic })
  } catch (err) {
    console.error('[aem] publish error:', err)
    return res.status(502).json({ error: 'Upstream publish error' })
  }
})

app.use(express.static(path.join(__dirname, 'dist')))

app.listen(port, () => {
  console.log(`altura-coffee-website listening on ${port}`)
})
