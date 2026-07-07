import './style.css'
import { publishSupportRequest, type SupportPayload } from './aem'

const form = document.getElementById('support-form') as HTMLFormElement
const submitBtn = document.getElementById('submit-btn') as HTMLButtonElement
const toast = document.getElementById('toast') as HTMLDivElement
const toastTitle = document.getElementById('toast-title') as HTMLDivElement
const toastBody = document.getElementById('toast-body') as HTMLDivElement

const fields = ['customer_id', 'contact_name', 'contact_email', 'country', 'customer_request'] as const

function getFieldEl(name: string): HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement {
  return document.getElementById(name) as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
}

function getErrorEl(name: string): HTMLSpanElement {
  return document.getElementById(`${name}-error`) as HTMLSpanElement
}

function validateField(name: string): boolean {
  const el = getFieldEl(name)
  const error = getErrorEl(name)
  const valid = el.value.trim().length > 0
  el.classList.toggle('invalid', !valid)
  error.classList.toggle('visible', !valid)
  return valid
}

function validateAll(): boolean {
  return fields.map(validateField).every(Boolean)
}

function showToast(title: string, body: string, isError = false): void {
  toastTitle.textContent = title
  toastBody.textContent = body
  toast.classList.toggle('toast--error', isError)
  toast.classList.add('visible')
  setTimeout(() => toast.classList.remove('visible'), 15000)
}

fields.forEach(name => {
  getFieldEl(name).addEventListener('blur', () => validateField(name))
  getFieldEl(name).addEventListener('input', () => {
    if (getFieldEl(name).classList.contains('invalid')) validateField(name)
  })
})

form.addEventListener('submit', async (e) => {
  e.preventDefault()
  if (!validateAll()) return

  submitBtn.disabled = true
  submitBtn.textContent = 'Sending…'

  const payload: SupportPayload = {
    customer_id: getFieldEl('customer_id').value.trim(),
    contact_name: getFieldEl('contact_name').value.trim(),
    contact_email: getFieldEl('contact_email').value.trim(),
    country: getFieldEl('country').value.trim(),
    customer_request: getFieldEl('customer_request').value.trim(),
  }

  try {
    const resolvedTopic = await publishSupportRequest(payload)
    showToast(
      'Request sent',
      `Your support request has been received. Our team will be in touch shortly.\n\nPublished to: ${resolvedTopic}`
    )
  } catch (err) {
    console.error('[support] publish error:', err)
    showToast(
      'Something went wrong',
      err instanceof Error ? err.message : 'Could not send your request. Please try again.',
      true
    )
  } finally {
    submitBtn.disabled = false
    submitBtn.textContent = 'Send request'
  }
})
