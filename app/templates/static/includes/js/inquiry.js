/* =========================================================
   inquiry.js – Wizard with API integration
   ========================================================= */

(function() {
  'use strict';

  const form = document.getElementById('inquiryForm');
  if (!form) {
    console.warn('Inquiry form not found.');
    return;
  }

  // --- DOM refs ---
  const fullName = document.getElementById('fullname');
  const phoneNumber = document.getElementById('phone_number');
  const email = document.getElementById('email');
  const bikeBrand = document.getElementById('bike_brand');
  const bikeModel = document.getElementById('bike_model');
  const bikeYear = document.getElementById('bike_year');
  const plateNumber = document.getElementById('plate_number');
  const bodyCondition = document.getElementById('body_condition');
  const estimatedBudget = document.getElementById('estimated_budget');
  const targetResult = document.getElementById('target_result');
  const projectDetails = document.getElementById('project_details');
  const referenceLink = document.getElementById('reference_link');
  const projectPhotos = document.getElementById('project_photos');

  const pages = document.querySelectorAll('.wizard-page');
  const steps = document.querySelectorAll('.step');
  const nextBtn = document.getElementById('nextBtn');
  const prevBtn = document.getElementById('prevBtn');
  const submitBtn = document.getElementById('submitBtn');
  const progressLine = document.querySelector('.progress-line');

  let currentStep = 0;

  // --- Helpers ---
  function createError(message) {
    const error = document.createElement('small');
    error.className = 'error-message';
    error.textContent = message;
    return error;
  }

  function clearErrors() {
    document.querySelectorAll('.error-message').forEach(el => el.remove());
    document.querySelectorAll('input, textarea, select').forEach(field => {
      field.style.borderColor = '';
    });
  }

  function showError(field, message) {
    if (!field) return;
    field.style.borderColor = '#ff4d4f';
    const parent = field.parentElement;
    const existing = parent.querySelector('.error-message');
    if (existing) existing.remove();
    parent.appendChild(createError(message));
  }

  function isValidPhone(phone) {
    return /^(\+62|62|08)\d{8,13}$/.test(phone);
  }

  function isValidUrl(url) {
    try {
      new URL(url);
      return true;
    } catch { return false; }
  }

  function getSelectedServices() {
    return Array.from(document.querySelectorAll('.service-card input[type="checkbox"]:checked'))
      .map(cb => cb.value);
  }

  /**
   * Parse numeric budget from the selected option text.
   * Examples:
   *   "Below Rp 2.000.000"       → 2000000
   *   "Rp 2.000.000 - Rp 5.000.000" → 2000000 (takes the first number)
   *   "Above Rp 10.000.000"      → 10000000
   */
  function parseBudgetValue(selectEl) {
    if (!selectEl || !selectEl.value) return null;
    const text = selectEl.options[selectEl.selectedIndex]?.text || '';
    // Extract all numbers, ignoring thousands separators (dots)
    const matches = text.match(/\d{1,3}(?:\.\d{3})*|\d+/g);
    if (matches && matches.length > 0) {
      // Remove dots and convert to integer
      const num = parseInt(matches[0].replace(/\./g, ''), 10);
      return isNaN(num) ? null : num;
    }
    return null;
  }

  function updateProgressLine() {
    if (!progressLine) return;
    const total = steps.length - 1;
    const percentage = total <= 0 ? 0 : (currentStep / total) * 100;
    progressLine.style.background =
      `linear-gradient(90deg, var(--primary) ${percentage}%, rgba(255,255,255,.08) ${percentage}%)`;
  }

  // --- Wizard ---
  function updateWizard() {
    pages.forEach((page, index) => {
      page.classList.toggle('active', index === currentStep);
    });
    steps.forEach((step, index) => {
      step.classList.toggle('active', index <= currentStep);
    });
    prevBtn.style.display = currentStep === 0 ? 'none' : 'inline-flex';
    nextBtn.style.display = currentStep === pages.length - 1 ? 'none' : 'inline-flex';
    submitBtn.style.display = currentStep === pages.length - 1 ? 'inline-flex' : 'none';
    updateProgressLine();
  }

  // --- Validation ---
  function validateStepOne() {
    let valid = true;
    const name = fullName.value.trim();
    const phone = phoneNumber.value.trim();
    const mail = email.value.trim();

    if (name.length < 3) {
      showError(fullName, 'Full name must be at least 3 characters.');
      valid = false;
    }
    if (!isValidPhone(phone)) {
      showError(phoneNumber, 'Please enter a valid WhatsApp number.');
      valid = false;
    }
    if (!mail || !mail.includes('@')) {
      showError(email, 'Please enter a valid email address.');
      valid = false;
    }
    return valid;
  }

  function validateStepTwo() {
    let valid = true;
    if (!bikeBrand.value) {
      showError(bikeBrand, 'Please select a motorcycle brand.');
      valid = false;
    }
    if (!bikeModel.value || bikeModel.value.trim().length < 2) {
      showError(bikeModel, 'Motorcycle model is required.');
      valid = false;
    }
    if (bikeYear.value) {
      const year = parseInt(bikeYear.value, 10);
      if (isNaN(year) || year < 1950 || year > new Date().getFullYear() + 1) {
        showError(bikeYear, 'Please enter a valid production year (1950 - current).');
        valid = false;
      }
    }
    if (!bodyCondition.value) {
      showError(bodyCondition, 'Please select the vehicle condition.');
      valid = false;
    }
    return valid;
  }

  function validateStepThree() {
    let valid = true;
    const services = getSelectedServices();
    if (!services.length) {
      alert('Please select at least one service.');
      valid = false;
    }
    const desc = projectDetails.value.trim();
    if (desc.length < 20) {
      showError(projectDetails, 'Project description must be at least 20 characters.');
      valid = false;
    }
    const ref = referenceLink.value.trim();
    if (ref && !isValidUrl(ref)) {
      showError(referenceLink, 'Please enter a valid URL.');
      valid = false;
    }
    if (projectPhotos.files && projectPhotos.files.length > 10) {
      showError(projectPhotos, 'Maximum 10 photos allowed.');
      valid = false;
    }
    return valid;
  }

  function validateStep(step) {
    clearErrors();
    switch (step) {
      case 0: return validateStepOne();
      case 1: return validateStepTwo();
      case 2: return validateStepThree();
      default: return true;
    }
  }

  // --- Navigation ---
  nextBtn.addEventListener('click', () => {
    if (!validateStep(currentStep)) return;
    currentStep++;
    updateWizard();
  });

  prevBtn.addEventListener('click', () => {
    currentStep--;
    updateWizard();
  });

  // --- Service cards ---
  document.querySelectorAll('.service-card').forEach(card => {
    const checkbox = card.querySelector('input[type="checkbox"]');
    if (!checkbox) return;
    function syncState() { card.classList.toggle('selected', checkbox.checked); }
    checkbox.addEventListener('change', syncState);
    syncState();
  });

  // --- Photo preview ---
  projectPhotos.addEventListener('change', () => {
    const uploadZone = projectPhotos.closest('.upload-zone');
    if (!uploadZone) return;
    const paragraph = uploadZone.querySelector('p');
    if (!paragraph) return;
    const count = projectPhotos.files.length;
    paragraph.textContent = count ? `${count} photo${count > 1 ? 's' : ''} selected` : 'Drag & drop photos here or click to browse.';
  });

  // --- Auto format ---
  phoneNumber.addEventListener('input', (e) => {
    e.target.value = e.target.value.replace(/[^0-9+]/g, '');
  });
  plateNumber.addEventListener('input', (e) => {
    e.target.value = e.target.value.toUpperCase();
  });

  // --- Motorcycle brand → model ---
  const motorcycleData = {
    Honda: ['Astrea Grand','Supra','Supra X','Revo','Blade','Beat','Scoopy','Genio','Vario 125','Vario 160','PCX 160','ADV 160','CB150R','Verza','Mega Pro','Tiger','CBR150R','CBR250RR','CRF150L'],
    Yamaha: ['Mio','Mio Sporty','Mio Soul','Fino','Xeon','Lexi','Aerox','NMAX','XMAX','Jupiter Z','Jupiter MX','Vega','Vixion','Byson','R15','R25','MT-15','XSR 155'],
    Suzuki: ['Crystal','Shogun','Smash','Satria','Satria F150','Nex','Address','Burgman Street','GSX-R150','GSX-S150'],
    Kawasaki: ['Kaze','Athlete','Ninja 150RR','Ninja 250R','Ninja ZX-25R','KLX 150','D-Tracker','W175','Versys X250']
  };

  bikeBrand.addEventListener('change', () => {
    const brand = bikeBrand.value;
    bikeModel.innerHTML = '<option value="">Select Model</option>';
    if (!motorcycleData[brand]) return;
    motorcycleData[brand].forEach(model => {
      const opt = document.createElement('option');
      opt.value = model;
      opt.textContent = model;
      bikeModel.appendChild(opt);
    });
  });

  // --- API ---
  const API_BASE = '/api/customer/inquiry/';

  async function createCustomerInquiry(payload) {
    const res = await fetch(API_BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.message || 'Failed to create inquiry');
    return data;
  }

  async function uploadInquiryPhotos(inquiryId, files) {
    const formData = new FormData();
    Array.from(files).forEach(file => formData.append('photos', file));
    const res = await fetch(`${API_BASE}${inquiryId}/photos`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.message || 'Failed to upload photos');
    return data;
  }

  // --- Submit ---
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!validateStepThree()) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    try {
      const payload = {
        customer_name: fullName.value.trim(),
        customer_phone_number: phoneNumber.value.trim(),
        customer_email: email.value.trim(),
        vehicle_brand: bikeBrand.value,
        vehicle_model: bikeModel.value.trim(),
        vehicle_license_plate: plateNumber.value.trim() || '',
        vehicle_condition: bodyCondition.value || '',
        project_type: getSelectedServices().join(', '),
        project_description: projectDetails.value.trim(),
        project_target: targetResult.value || '',
        reference_link: referenceLink.value.trim() || '',
        estimated_budget: parseBudgetValue(estimatedBudget)   // <-- FIXED
      };

      const res = await createCustomerInquiry(payload);
      const inquiryId = res?.data?.id;
      if (!inquiryId) throw new Error('No inquiry ID returned');

      const files = projectPhotos.files;
      if (files && files.length > 0) {
        await uploadInquiryPhotos(inquiryId, files);
      }

      alert('✅ Project inquiry submitted successfully. Our team will contact you shortly.');
      form.reset();
      document.querySelectorAll('.service-card').forEach(c => c.classList.remove('selected'));
      currentStep = 0;
      clearErrors();
      updateWizard();
      const p = document.querySelector('.upload-zone p');
      if (p) p.textContent = 'Drag & drop photos here or click to browse.';

    } catch (err) {
      console.error(err);
      alert('❌ Something went wrong. Please try again.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Start My Project';
    }
  });

  // --- Init ---
  updateWizard();
})();