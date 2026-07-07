export async function publishSupportRequest(payload) {
    const response = await fetch('/api/support-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        const body = await response.text().catch(() => '');
        throw new Error(`Publish failed (${response.status}): ${body}`);
    }
    const data = (await response.json().catch(() => ({})));
    return data.topic ?? '';
}
