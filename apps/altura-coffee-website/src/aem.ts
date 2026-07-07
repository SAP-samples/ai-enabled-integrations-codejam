export interface SupportPayload {
  customer_id: string
  contact_name: string
  contact_email: string
  country: string
  customer_request: string
}

export async function publishSupportRequest(payload: SupportPayload): Promise<string> {
  const response = await fetch('/api/support-request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const body = await response.text().catch(() => '')
    throw new Error(`Publish failed (${response.status}): ${body}`)
  }

  const data = (await response.json().catch(() => ({}))) as { topic?: string }
  return data.topic ?? ''
}
