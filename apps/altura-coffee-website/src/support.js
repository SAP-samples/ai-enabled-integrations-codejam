import './style.css';
import { publishSupportRequest } from './aem';
const form = document.getElementById('support-form');
const submitBtn = document.getElementById('submit-btn');
const toast = document.getElementById('toast');
const toastTitle = document.getElementById('toast-title');
const toastBody = document.getElementById('toast-body');
const fields = ['customer_id', 'contact_name', 'contact_email', 'country', 'customer_request'];
function getFieldEl(name) {
    return document.getElementById(name);
}
function getErrorEl(name) {
    return document.getElementById(`${name}-error`);
}
function validateField(name) {
    const el = getFieldEl(name);
    const error = getErrorEl(name);
    const valid = el.value.trim().length > 0;
    el.classList.toggle('invalid', !valid);
    error.classList.toggle('visible', !valid);
    return valid;
}
function validateAll() {
    return fields.map(validateField).every(Boolean);
}
function showToast(title, body, isError = false) {
    toastTitle.textContent = title;
    toastBody.textContent = body;
    toast.classList.toggle('toast--error', isError);
    toast.classList.add('visible');
    setTimeout(() => toast.classList.remove('visible'), 15000);
}
fields.forEach(name => {
    getFieldEl(name).addEventListener('blur', () => validateField(name));
    getFieldEl(name).addEventListener('input', () => {
        if (getFieldEl(name).classList.contains('invalid'))
            validateField(name);
    });
});
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateAll())
        return;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending…';
    const payload = {
        customer_id: getFieldEl('customer_id').value.trim(),
        contact_name: getFieldEl('contact_name').value.trim(),
        contact_email: getFieldEl('contact_email').value.trim(),
        country: getFieldEl('country').value.trim(),
        customer_request: getFieldEl('customer_request').value.trim(),
    };
    try {
        const resolvedTopic = await publishSupportRequest(payload);
        showToast('Request sent', `Your support request has been received. Our team will be in touch shortly.\n\nPublished to: ${resolvedTopic}`);
    }
    catch (err) {
        console.error('[support] publish error:', err);
        showToast('Something went wrong', err instanceof Error ? err.message : 'Could not send your request. Please try again.', true);
    }
    finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send request';
    }
});
