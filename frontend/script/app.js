'use strict';

const CONFIG = {
  // Change this to your Flask backend URL when running locally:
  // e.g. 'http://127.0.0.1:5000/upload'
  API_ENDPOINT: 'http://127.0.0.1:5000/upload',

  // Allowed MIME types + extensions
  ALLOWED_TYPES: ['application/pdf', 'image/jpeg', 'image/png'],
  ALLOWED_EXTS:  ['.pdf', '.jpg', '.jpeg', '.png'],

  // Max file size: 10 MB
  MAX_SIZE_BYTES: 10 * 1024 * 1024,

  // Request timeout in ms (15 s — OCR can be slow)
  TIMEOUT_MS: 15_000,
};

const $  = (id) => document.getElementById(id);

const dropzone        = $('dropzone');
const fileInput       = $('file-input');
const filePreview     = $('file-preview');
const fileNameDisplay = $('file-name-display');
const fileRemoveBtn   = $('file-remove-btn');
const extractBtn      = $('extract-btn');
const btnText         = extractBtn.querySelector('.btn__text');
const btnSpinner      = extractBtn.querySelector('.btn__spinner');
const uploadError     = $('upload-error');
const uploadErrorMsg  = $('upload-error-msg');

const processingSection = $('processing-section');
const uploadSection     = document.querySelector('.upload-section');
const resultsSection    = $('results-section');

const resultCards   = $('result-cards');
const rawJsonBlock  = $('raw-json-block');
const rawJsonDetails= $('raw-json-details');
const resultError   = $('result-error');
const resultErrorMsg= $('result-error-msg');
const newUploadBtn  = $('new-upload-btn');

const PROC_STEPS = ['step-upload', 'step-ocr', 'step-nlp', 'step-done'];

let selectedFile = null;

const FIELD_META = {
  company_name:   { label: 'Company Name',  icon: '🏢', cardClass: 'result-card--company' },
  date:           { label: 'Date',           icon: '📅', cardClass: 'result-card--date'    },
  total_amount:   { label: 'Total Amount',  icon: '💰', cardClass: 'result-card--total'   },
  invoice_number: { label: 'Invoice No.',   icon: '🔖', cardClass: 'result-card--extra'   },
  tax_amount:     { label: 'Tax',           icon: '🧾', cardClass: 'result-card--extra'   },
  vendor_address: { label: 'Address',       icon: '📍', cardClass: 'result-card--extra'   },
};

function validateFile(file) {
  if (!file) return 'No file selected.';

  const ext = '.' + file.name.split('.').pop().toLowerCase();
  const typeOk = CONFIG.ALLOWED_TYPES.includes(file.type) || CONFIG.ALLOWED_EXTS.includes(ext);
  if (!typeOk) {
    return `Unsupported file type "${ext}". Please upload a PDF, JPG, or PNG.`;
  }

  if (file.size === 0) return 'The selected file is empty. Please choose a valid document.';
  if (file.size > CONFIG.MAX_SIZE_BYTES) {
    return `File is too large (${formatBytes(file.size)}). Maximum allowed size is 10 MB.`;
  }

  return null; // valid
}

function handleFileSelection(file) {
  const err = validateFile(file);
  if (err) {
    showUploadError(err);
    clearFile();
    return;
  }

  hideUploadError();
  selectedFile = file;

  // Show file preview
  fileNameDisplay.textContent = file.name;
  filePreview.hidden = false;
  dropzone.classList.add('has-file');

  // Enable the extract button
  extractBtn.disabled = false;
  extractBtn.removeAttribute('aria-disabled');
}

function clearFile() {
  selectedFile = null;
  fileInput.value = '';
  filePreview.hidden = true;
  fileNameDisplay.textContent = '';
  dropzone.classList.remove('has-file');
  extractBtn.disabled = true;
  extractBtn.setAttribute('aria-disabled', 'true');
}

dropzone.addEventListener('click', (e) => {
  if (e.target === fileRemoveBtn) return;
  fileInput.click();
});

dropzone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    fileInput.click();
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) handleFileSelection(fileInput.files[0]);
});

fileRemoveBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  clearFile();
  hideUploadError();
});

// Drag events
dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.classList.add('dragover');
});
['dragleave', 'dragend'].forEach((evt) => {
  dropzone.addEventListener(evt, () => dropzone.classList.remove('dragover'));
});
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFileSelection(file);
});

let stepTimers = [];

function resetSteps() {
  stepTimers.forEach(clearTimeout);
  stepTimers = [];
  PROC_STEPS.forEach((id) => {
    const el = $(id);
    el.classList.remove('active', 'done');
  });
}

function animateSteps() {
  resetSteps();
  const delays = [0, 800, 2200, 4000]; // ms per step activation
  PROC_STEPS.forEach((id, i) => {
    const t = setTimeout(() => {
      // Mark previous as done
      if (i > 0) {
        $(PROC_STEPS[i - 1]).classList.remove('active');
        $(PROC_STEPS[i - 1]).classList.add('done');
      }
      $(id).classList.add('active');
    }, delays[i]);
    stepTimers.push(t);
  });
}

function completeSteps() {
  stepTimers.forEach(clearTimeout);
  stepTimers = [];
  PROC_STEPS.forEach((id) => {
    const el = $(id);
    el.classList.remove('active');
    el.classList.add('done');
  });
}

function showSection(section) {
  uploadSection.hidden     = section !== 'upload';
  processingSection.hidden = section !== 'processing';
  resultsSection.hidden    = section !== 'results';
}

function setLoadingState(loading) {
  extractBtn.disabled = loading;
  if (loading) {
    extractBtn.setAttribute('aria-disabled', 'true');
    btnText.textContent = 'Processing…';
    btnSpinner.hidden = false;
  } else {
    extractBtn.removeAttribute('aria-disabled');
    btnText.textContent = 'Extract Data';
    btnSpinner.hidden = true;
  }
}

function showUploadError(msg) {
  uploadErrorMsg.textContent = msg;
  uploadError.hidden = false;
}
function hideUploadError() {
  uploadError.hidden = true;
}
function showResultError(msg) {
  resultErrorMsg.textContent = msg;
  resultError.hidden = false;
  $('results-success').hidden = true;
}

function renderResults(data) {
  resultCards.innerHTML = '';

  // Render known fields first (preserves order)
  const renderedKeys = new Set();
  for (const [key, meta] of Object.entries(FIELD_META)) {
    if (key in data) {
      resultCards.appendChild(createCard(meta, data[key]));
      renderedKeys.add(key);
    }
  }

  // Render any extra fields the backend returned (future-proof)
  for (const [key, value] of Object.entries(data)) {
    if (!renderedKeys.has(key) && key !== 'error' && key !== 'status') {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      resultCards.appendChild(createCard(
        { label, icon: '📌', cardClass: 'result-card--extra' },
        value
      ));
    }
  }

  // Show raw JSON
  rawJsonBlock.textContent = JSON.stringify(data, null, 2);
  rawJsonDetails.open = false;
}

function createCard(meta, value) {
  const card = document.createElement('div');
  card.className = `result-card ${meta.cardClass}`;
  card.setAttribute('role', 'article');

  const isEmpty = value === null || value === undefined || String(value).trim() === '' || value === 'N/A';

  card.innerHTML = `
    <div class="result-card__label">
      <span class="result-card__icon" aria-hidden="true">${meta.icon}</span>
      ${escapeHtml(meta.label)}
    </div>
    <div class="result-card__value ${isEmpty ? 'not-found' : ''}">
      ${isEmpty ? 'Not found' : escapeHtml(String(value))}
    </div>
  `;
  return card;
}

async function uploadFile() {
  if (!selectedFile) return;

  const validationError = validateFile(selectedFile);
  if (validationError) {
    showUploadError(validationError);
    return;
  }

  hideUploadError();
  setLoadingState(true);
  showSection('processing');
  animateSteps();

  const formData = new FormData();
  formData.append('file', selectedFile);

  // AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);

  try {
    const response = await fetch(CONFIG.API_ENDPOINT, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    completeSteps();

    // Small delay so user sees "Finalising results" step complete
    await delay(400);

    if (!response.ok) {
      // Try to parse backend error message
      let backendMsg = `Server error (HTTP ${response.status})`;
      try {
        const errData = await response.json();
        if (errData.error) backendMsg = errData.error;
      } catch { /* ignore */ }
      throw new Error(backendMsg);
    }

    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error('Could not parse server response. Is the backend running?');
    }

    // Render results
    showSection('results');
    resultError.hidden = true;
    $('results-success').hidden = false;
    renderResults(data);

  } catch (err) {
    clearTimeout(timeoutId);
    completeSteps();
    await delay(200);
    showSection('results');

    if (err.name === 'AbortError') {
      showResultError(`Request timed out after ${CONFIG.TIMEOUT_MS / 1000} s. The server may be busy — try again.`);
    } else if (!navigator.onLine) {
      showResultError('No internet connection. Please check your network and try again.');
    } else {
      showResultError(err.message || 'An unexpected error occurred. Please try again.');
    }

    // Still show the raw error in the JSON block for debugging
    rawJsonBlock.textContent = JSON.stringify({ error: err.message }, null, 2);
    rawJsonDetails.open = true;
  } finally {
    setLoadingState(false);
  }
}

extractBtn.addEventListener('click', uploadFile);

newUploadBtn.addEventListener('click', () => {
  clearFile();
  hideUploadError();
  resultError.hidden = true;
  resultCards.innerHTML = '';
  rawJsonBlock.textContent = '';
  rawJsonDetails.open = false;
  resetSteps();
  showSection('upload');
});

function delay(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
