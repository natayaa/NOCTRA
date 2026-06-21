/**
 * NOCTRA Inquiry Wizard
 * Multi-step form with API integration for customer inquiries.
 *
 * Refactored to be modular, maintainable, and performant.
 * All logic is encapsulated in a single class.
 */
(function() {
    'use strict';

    // ─── Constants ──────────────────────────────────────────────
    const API_BASE = '/api/customer/inquiry/';
    const PHONE_REGEX = /^(\+62|62|08)\d{8,13}$/;
    const YEAR_MIN = 1950;
    const MAX_PHOTOS = 10;
    const MIN_DESCRIPTION_LENGTH = 20;
    const MIN_NAME_LENGTH = 3;

    const MOTORCYCLE_DATA = {
        Honda: ['Astrea Grand','Supra','Supra X','Revo','Blade','Beat','Scoopy','Genio','Vario 125','Vario 160','PCX 160','ADV 160','CB150R','Verza','Mega Pro','Tiger','CBR150R','CBR250RR','CRF150L'],
        Yamaha: ['Mio','Mio Sporty','Mio Soul','Fino','Xeon','Lexi','Aerox','NMAX','XMAX','Jupiter Z','Jupiter MX','Vega','Vixion','Byson','R15','R25','MT-15','XSR 155'],
        Suzuki: ['Crystal','Shogun','Smash','Satria','Satria F150','Nex','Address','Burgman Street','GSX-R150','GSX-S150'],
        Kawasaki: ['Kaze','Athlete','Ninja 150RR','Ninja 250R','Ninja ZX-25R','KLX 150','D-Tracker','W175','Versys X250']
    };

    // ─── Main Class ──────────────────────────────────────────────
    class InquiryWizard {
        // ─── Private fields ──────────────────────────────────────
        #dom = {};
        #state = {
            currentStep: 0,
            isSubmitting: false
        };

        // ─── Constructor ──────────────────────────────────────────
        constructor() {
            // Guard: ensure form exists
            const form = document.getElementById('inquiryForm');
            if (!form) {
                console.warn('Inquiry form not found. Wizard not initialized.');
                return;
            }
            this.#dom.form = form;
            this.#cacheDomRefs();
            this.#bindEvents();
            this.#initWizard();
        }

        // ─── DOM Caching ──────────────────────────────────────────
        #cacheDomRefs() {
            const ids = [
                'fullname', 'phone_number', 'email',
                'bike_brand', 'bike_model', 'bike_year',
                'plate_number', 'body_condition',
                'estimated_budget', 'target_result',
                'project_details', 'reference_link', 'project_photos',
                'nextBtn', 'prevBtn', 'submitBtn',
                'progressLine'
            ];
            const refs = {};
            ids.forEach(id => {
                refs[id] = document.getElementById(id);
            });
            // Additional: wizard pages and steps (collections)
            refs.pages = document.querySelectorAll('.wizard-page');
            refs.steps = document.querySelectorAll('.step');
            refs.serviceCards = document.querySelectorAll('.service-card');
            // Upload zone paragraph (for photo preview)
            const uploadZone = this.#dom.projectPhotos?.closest('.upload-zone');
            if (uploadZone) refs.uploadParagraph = uploadZone.querySelector('p');
            this.#dom = { ...this.#dom, ...refs };
        }

        // ─── Event Binding ────────────────────────────────────────
        #bindEvents() {
            const { form, nextBtn, prevBtn, submitBtn, phone_number, plate_number,
                    bike_brand, bike_model, project_photos } = this.#dom;

            // Navigation
            nextBtn?.addEventListener('click', () => this.#goNext());
            prevBtn?.addEventListener('click', () => this.#goPrev());

            // Form submission
            form?.addEventListener('submit', (e) => this.#handleSubmit(e));

            // Auto-format phone and plate
            phone_number?.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9+]/g, '');
            });
            plate_number?.addEventListener('input', (e) => {
                e.target.value = e.target.value.toUpperCase();
            });

            // Motorcycle brand → model dependency
            bike_brand?.addEventListener('change', () => this.#populateModels());

            // Service cards toggle
            this.#dom.serviceCards.forEach(card => {
                const checkbox = card.querySelector('input[type="checkbox"]');
                if (!checkbox) return;
                const sync = () => card.classList.toggle('selected', checkbox.checked);
                checkbox.addEventListener('change', sync);
                sync(); // initial state
            });

            // Photo preview
            project_photos?.addEventListener('change', () => this.#updatePhotoPreview());
        }

        // ─── Wizard Navigation ────────────────────────────────────
        #goNext() {
            if (!this.#validateStep(this.#state.currentStep)) return;
            if (this.#state.currentStep < this.#dom.pages.length - 1) {
                this.#state.currentStep++;
                this.#updateWizard();
            }
        }

        #goPrev() {
            if (this.#state.currentStep > 0) {
                this.#state.currentStep--;
                this.#updateWizard();
            }
        }

        #initWizard() {
            this.#updateWizard();
        }

        #updateWizard() {
            const { pages, steps, prevBtn, nextBtn, submitBtn, progressLine } = this.#dom;
            const current = this.#state.currentStep;
            const total = pages.length - 1;

            pages.forEach((page, index) => {
                page.classList.toggle('active', index === current);
            });
            steps.forEach((step, index) => {
                step.classList.toggle('active', index <= current);
            });

            if (prevBtn) prevBtn.style.display = current === 0 ? 'none' : 'inline-flex';
            if (nextBtn) nextBtn.style.display = current === total ? 'none' : 'inline-flex';
            if (submitBtn) submitBtn.style.display = current === total ? 'inline-flex' : 'none';

            // Progress line
            if (progressLine) {
                const percentage = total <= 0 ? 0 : (current / total) * 100;
                progressLine.style.background =
                    `linear-gradient(90deg, var(--primary) ${percentage}%, rgba(255,255,255,.08) ${percentage}%)`;
            }
        }

        // ─── Validation ───────────────────────────────────────────
        #validateStep(step) {
            this.#clearErrors();
            switch (step) {
                case 0: return this.#validateStepOne();
                case 1: return this.#validateStepTwo();
                case 2: return this.#validateStepThree();
                default: return true;
            }
        }

        #validateStepOne() {
            const { fullname, phone_number, email } = this.#dom;
            let valid = true;
            const name = fullname.value.trim();
            const phone = phone_number.value.trim();
            const mail = email.value.trim();

            if (name.length < MIN_NAME_LENGTH) {
                this.#showError(fullname, `Full name must be at least ${MIN_NAME_LENGTH} characters.`);
                valid = false;
            }
            if (!PHONE_REGEX.test(phone)) {
                this.#showError(phone_number, 'Please enter a valid WhatsApp number.');
                valid = false;
            }
            if (!mail || !mail.includes('@')) {
                this.#showError(email, 'Please enter a valid email address.');
                valid = false;
            }
            return valid;
        }

        #validateStepTwo() {
            const { bike_brand, bike_model, bike_year, body_condition } = this.#dom;
            let valid = true;
            if (!bike_brand.value) {
                this.#showError(bike_brand, 'Please select a motorcycle brand.');
                valid = false;
            }
            if (!bike_model.value || bike_model.value.trim().length < 2) {
                this.#showError(bike_model, 'Motorcycle model is required.');
                valid = false;
            }
            if (bike_year.value) {
                const year = parseInt(bike_year.value, 10);
                const currentYear = new Date().getFullYear();
                if (isNaN(year) || year < YEAR_MIN || year > currentYear + 1) {
                    this.#showError(bike_year, `Please enter a valid production year (${YEAR_MIN} - ${currentYear + 1}).`);
                    valid = false;
                }
            }
            if (!body_condition.value) {
                this.#showError(body_condition, 'Please select the vehicle condition.');
                valid = false;
            }
            return valid;
        }

        #validateStepThree() {
            const { project_details, reference_link, project_photos } = this.#dom;
            let valid = true;

            const services = this.#getSelectedServices();
            if (!services.length) {
                alert('Please select at least one service.');
                valid = false;
            }
            const desc = project_details.value.trim();
            if (desc.length < MIN_DESCRIPTION_LENGTH) {
                this.#showError(project_details, `Project description must be at least ${MIN_DESCRIPTION_LENGTH} characters.`);
                valid = false;
            }
            const ref = reference_link.value.trim();
            if (ref && !this.#isValidUrl(ref)) {
                this.#showError(reference_link, 'Please enter a valid URL.');
                valid = false;
            }
            if (project_photos.files && project_photos.files.length > MAX_PHOTOS) {
                this.#showError(project_photos, `Maximum ${MAX_PHOTOS} photos allowed.`);
                valid = false;
            }
            return valid;
        }

        // ─── Helpers ──────────────────────────────────────────────
        #clearErrors() {
            document.querySelectorAll('.error-message').forEach(el => el.remove());
            document.querySelectorAll('input, textarea, select').forEach(field => {
                field.style.borderColor = '';
            });
        }

        #showError(field, message) {
            if (!field) return;
            field.style.borderColor = '#ff4d4f';
            const parent = field.parentElement;
            if (!parent) return;
            const existing = parent.querySelector('.error-message');
            if (existing) existing.remove();
            const error = document.createElement('small');
            error.className = 'error-message';
            error.textContent = message;
            parent.appendChild(error);
        }

        #isValidUrl(url) {
            try {
                new URL(url);
                return true;
            } catch { return false; }
        }

        #getSelectedServices() {
            return Array.from(document.querySelectorAll('.service-card input[type="checkbox"]:checked'))
                .map(cb => cb.value);
        }

        #parseBudgetValue() {
            const select = this.#dom.estimated_budget;
            if (!select || !select.value) return null;
            const text = select.options[select.selectedIndex]?.text || '';
            const matches = text.match(/\d{1,3}(?:\.\d{3})*|\d+/g);
            if (matches && matches.length > 0) {
                const num = parseInt(matches[0].replace(/\./g, ''), 10);
                return isNaN(num) ? null : num;
            }
            return null;
        }

        #populateModels() {
            const brand = this.#dom.bike_brand?.value;
            const modelSelect = this.#dom.bike_model;
            if (!modelSelect) return;
            modelSelect.innerHTML = '<option value="">Select Model</option>';
            if (!brand || !MOTORCYCLE_DATA[brand]) return;
            MOTORCYCLE_DATA[brand].forEach(model => {
                const opt = document.createElement('option');
                opt.value = model;
                opt.textContent = model;
                modelSelect.appendChild(opt);
            });
        }

        #updatePhotoPreview() {
            const files = this.#dom.project_photos?.files;
            const paragraph = this.#dom.uploadParagraph;
            if (!paragraph) return;
            const count = files?.length || 0;
            paragraph.textContent = count ? `${count} photo${count > 1 ? 's' : ''} selected` : 'Drag & drop photos here or click to browse.';
        }

        // ─── API ──────────────────────────────────────────────────
        async #createInquiry(payload) {
            const response = await fetch(API_BASE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data?.message || 'Failed to create inquiry');
            return data;
        }

        async #uploadPhotos(inquiryId, files) {
            const formData = new FormData();
            Array.from(files).forEach(file => formData.append('photos', file));
            const response = await fetch(`${API_BASE}${inquiryId}/photos`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data?.message || 'Failed to upload photos');
            return data;
        }

        // ─── Form Submission ──────────────────────────────────────
        async #handleSubmit(event) {
            event.preventDefault();
            if (!this.#validateStep(2)) return;
            if (this.#state.isSubmitting) return;

            this.#state.isSubmitting = true;
            const submitBtn = this.#dom.submitBtn;
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Submitting...';
            }

            try {
                const payload = {
                    customer_name: this.#dom.fullname.value.trim(),
                    customer_phone_number: this.#dom.phone_number.value.trim(),
                    customer_email: this.#dom.email.value.trim(),
                    vehicle_brand: this.#dom.bike_brand.value,
                    vehicle_model: this.#dom.bike_model.value.trim(),
                    vehicle_license_plate: this.#dom.plate_number.value.trim() || '',
                    vehicle_condition: this.#dom.body_condition.value || '',
                    project_type: this.#getSelectedServices().join(', '),
                    project_description: this.#dom.project_details.value.trim(),
                    project_target: this.#dom.target_result.value || '',
                    reference_link: this.#dom.reference_link.value.trim() || '',
                    estimated_budget: this.#parseBudgetValue()
                };

                const response = await this.#createInquiry(payload);
                const inquiryId = response?.data?.id;
                if (!inquiryId) throw new Error('No inquiry ID returned');

                const files = this.#dom.project_photos?.files;
                if (files && files.length > 0) {
                    await this.#uploadPhotos(inquiryId, files);
                }

                alert('✅ Project inquiry submitted successfully. Our team will contact you shortly.');
                this.#resetForm();
            } catch (err) {
                console.error('Submission error:', err);
                alert('❌ Something went wrong. Please try again.');
            } finally {
                this.#state.isSubmitting = false;
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Start My Project';
                }
            }
        }

        #resetForm() {
            const form = this.#dom.form;
            if (form) form.reset();
            // Reset service cards
            document.querySelectorAll('.service-card').forEach(c => c.classList.remove('selected'));
            // Reset photo preview text
            const p = this.#dom.uploadParagraph;
            if (p) p.textContent = 'Drag & drop photos here or click to browse.';
            // Reset to first step
            this.#state.currentStep = 0;
            this.#clearErrors();
            this.#updateWizard();
        }
    }

    // ─── Instantiate ─────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        new InquiryWizard();
    });

})();