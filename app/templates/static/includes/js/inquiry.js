// inquiry.js - NOCTRA AUTOWORKS Inquiry Form
// Complete implementation with 2-step submission (JSON + Photo Upload)

(function () {
  "use strict";

  // ===== STATE MANAGEMENT =====
  const state = {
    currentStep: 1,
    totalSteps: 0,
    selectedFiles: [],
    maxFiles: 10,
    isSubmitting: false,
    abortController: null,
  };

  // ===== DOM CACHE =====
  const dom = {};

  function cacheDom() {
    dom.form = document.getElementById("inquiryForm");
    dom.pages = document.querySelectorAll(".wizard-page");
    dom.steps = document.querySelectorAll(".step");
    dom.prevBtn = document.getElementById("prevBtn");
    dom.nextBtn = document.getElementById("nextBtn");
    dom.submitBtn = document.getElementById("submitBtn");
    dom.progressLine = document.querySelector(".progress-line");
    dom.uploadZone = document.getElementById("uploadZone");
    dom.photoInput = document.getElementById("project_photos");
    dom.photoPreviewGrid = document.getElementById("photoPreviewGrid");
    dom.agreementCheck = document.getElementById("agreementCheck");
    dom.brandSelect = document.getElementById("bike_brand");
    dom.modelSelect = document.getElementById("bike_model");

    state.totalSteps = dom.pages.length;
  }

  // ===== CLEANUP UTILITIES =====
  function removeElement(element) {
    if (element && element.parentNode) {
      element.parentNode.removeChild(element);
    }
  }

  function clearErrors(container) {
    if (!container) return;
    container.querySelectorAll(".error-message").forEach(removeElement);
    container
      .querySelectorAll(".error")
      .forEach((el) => el.classList.remove("error"));
  }

  function revokeObjectURLs() {
    dom.photoPreviewGrid?.querySelectorAll("img").forEach((img) => {
      if (img.src && img.src.startsWith("blob:")) {
        URL.revokeObjectURL(img.src);
      }
    });
  }

  function abortPendingRequest() {
    if (state.abortController) {
      state.abortController.abort();
      state.abortController = null;
    }
  }

  // ===== STEP MANAGEMENT =====
  function updateStep(step) {
    const progressPercent = ((step - 1) / (state.totalSteps - 1)) * 100;

    dom.pages.forEach((page, index) => {
      page.classList.toggle("active", index === step - 1);
    });

    dom.steps.forEach((s, index) => {
      s.classList.toggle("active", index <= step - 1);
    });

    dom.progressLine.style.background = `linear-gradient(90deg, #ff6b00 ${progressPercent}%, rgba(255,255,255,0.08) ${progressPercent}%)`;

    dom.prevBtn.style.display = step === 1 ? "none" : "inline-block";
    dom.nextBtn.style.display =
      step === state.totalSteps ? "none" : "inline-block";
    dom.submitBtn.style.display =
      step === state.totalSteps ? "inline-block" : "none";

    dom.form?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function goToStep(step) {
    if (step < 1 || step > state.totalSteps) return;

    if (step > state.currentStep && !validateStep(state.currentStep)) {
      return;
    }

    state.currentStep = step;
    updateStep(state.currentStep);
  }

  // ===== VALIDATION =====
  function validateStep(step) {
    const page = dom.pages[step - 1];
    if (!page) return false;

    clearErrors(page);
    let isValid = true;

    const inputs = page.querySelectorAll(
      "input[required], select[required], textarea[required]",
    );

    inputs.forEach((input) => {
      if (input.offsetParent === null || input.disabled) return;

      if (input.type === "checkbox") {
        if (!input.checked) {
          isValid = false;
          input.classList.add("error");
          const label = input.closest(".checkbox-label");
          if (label && !label.querySelector(".error-message")) {
            const error = document.createElement("span");
            error.className = "error-message";
            error.textContent = "Please confirm the agreement";
            label.appendChild(error);
          }
        }
        return;
      }

      if (input.type === "file") return;

      const value = input.value.trim();

      if (input.type === "email" && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
          isValid = false;
          input.classList.add("error");
          showError(input, "Please enter a valid email address");
        }
        return;
      }

      if (input.id === "phone_number" && value) {
        const phoneRegex = /^(\+62|62|08)\d{8,13}$/;
        if (!phoneRegex.test(value.replace(/\s/g, ""))) {
          isValid = false;
          input.classList.add("error");
          showError(
            input,
            "Format nomor telepon tidak valid (contoh: 081234567890 atau +6281234567890)",
          );
        }
        return;
      }

      if (!value) {
        isValid = false;
        input.classList.add("error");
        showError(input, "This field is required");
      }
    });

    if (step === 2) {
      const brand = dom.brandSelect?.value;
      const model = dom.modelSelect?.value;
      if (brand && model) {
        const validModels = Array.from(dom.modelSelect.options).filter(
          (opt) => opt.dataset.brand === brand && opt.value,
        );
        const isValidModel = validModels.some((opt) => opt.value === model);
        if (!isValidModel) {
          isValid = false;
          dom.modelSelect.classList.add("error");
          showError(
            dom.modelSelect,
            "Please select a valid model for the selected brand",
          );
        }
      }
    }

    if (step === 3) {
      const services = page.querySelectorAll('input[name="services"]:checked');
      if (services.length === 0) {
        isValid = false;
        const grid = page.querySelector(".service-grid");
        if (grid && !grid.parentNode.querySelector(".error-message")) {
          const error = document.createElement("span");
          error.className = "error-message";
          error.textContent = "Please select at least one service";
          grid.parentNode.appendChild(error);
        }
      }
    }

    return isValid;
  }

  function showError(input, message) {
    if (!input || input.parentNode.querySelector(".error-message")) return;
    const error = document.createElement("span");
    error.className = "error-message";
    error.textContent = message;
    input.parentNode.appendChild(error);
  }

  // ===== FORM DATA COLLECTION =====
  function collectFormData() {
    const getValue = (id) => {
      const el = document.getElementById(id);
      return el ? el.value.trim() : "";
    };
    const getSelectValue = (id) => {
      const el = document.getElementById(id);
      return el ? el.value : "";
    };
    const getCheckboxValues = (name) => {
      return Array.from(
        document.querySelectorAll(`input[name="${name}"]:checked`),
      )
        .map((cb) => cb.value)
        .join(", ");
    };

    return {
      customer_name: getValue("fullname"),
      customer_phone_number: getValue("phone_number"),
      customer_email: getValue("email") || null,
      province: getValue("province") || null,
      city: getValue("city") || null,
      vehicle_brand: getSelectValue("bike_brand"),
      vehicle_model: getSelectValue("bike_model"),
      vehicle_year: parseInt(getValue("bike_year")) || null,
      vehicle_license_plate: getValue("plate_number") || null,
      previous_repaint: getSelectValue("previous_repaint") || null,
      bike_modified: getSelectValue("bike_modified") || null,
      vehicle_condition: getCheckboxValues("condition") || null,
      project_type: getSelectValue("project_type"),
      services: getCheckboxValues("services") || null,
      desired_finish: getSelectValue("desired_finish") || null,
      desired_color: getValue("desired_color") || null,
      estimated_budget: parseInt(getSelectValue("estimated_budget")) || null,
      deadline: getSelectValue("deadline") || null,
      priority: getSelectValue("priority") || null,
      project_description: getValue("project_details"),
      reference_link: getValue("reference_link") || null,
      source: "website_inquiry",
    };
  }

  // ===== SUBMIT - 2 Step Process =====
  async function submitForm() {
    if (state.isSubmitting) return;

    if (!validateStep(state.currentStep)) return;

    const formData = collectFormData();

    // Validate required fields
    const required = [
      "customer_name",
      "customer_phone_number",
      "vehicle_brand",
      "vehicle_model",
      "project_type",
      "project_description",
    ];

    const missing = required.filter((field) => !formData[field]);
    if (missing.length > 0) {
      showToast("Please fill in all required fields", "error");
      return;
    }

    // Validate phone
    const phoneRegex = /^(\+62|62|08)\d{8,13}$/;
    if (!phoneRegex.test(formData.customer_phone_number.replace(/\s/g, ""))) {
      showToast("Format nomor telepon tidak valid", "error");
      return;
    }

    // Validate email if provided
    if (formData.customer_email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.customer_email)) {
        showToast("Please enter a valid email address", "error");
        return;
      }
    }

    state.isSubmitting = true;
    dom.submitBtn.disabled = true;
    dom.submitBtn.innerHTML = '<span class="spinner"></span> Submitting...';

    abortPendingRequest();
    state.abortController = new AbortController();

    try {
      // ============================================================
      // STEP 1: Create Inquiry (JSON)
      // ============================================================
      const payload = {
        customer_name: formData.customer_name,
        customer_phone_number: formData.customer_phone_number,
        customer_email: formData.customer_email,
        province: formData.province,
        city: formData.city,
        vehicle_brand: formData.vehicle_brand,
        vehicle_model: formData.vehicle_model,
        vehicle_year: formData.vehicle_year,
        vehicle_license_plate: formData.vehicle_license_plate,
        previous_repaint: formData.previous_repaint,
        bike_modified: formData.bike_modified,
        vehicle_condition: formData.vehicle_condition,
        project_type: formData.project_type,
        services: formData.services,
        desired_finish: formData.desired_finish,
        desired_color: formData.desired_color,
        estimated_budget: formData.estimated_budget,
        deadline: formData.deadline,
        priority: formData.priority,
        project_description: formData.project_description,
        reference_link: formData.reference_link,
        source: formData.source,
      };

      const response = await fetch("/api/api/inquiries/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        signal: state.abortController.signal,
      });

      // Handle response as text first (avoid bytes issue)
      const responseText = await response.text();
      let result;
      try {
        result = responseText ? JSON.parse(responseText) : {};
      } catch (parseError) {
        result = { message: responseText || "Submission received" };
      }

      if (!response.ok) {
        const errorMsg =
          result.detail || result.message || `Server error: ${response.status}`;
        showToast(errorMsg, "error");
        return;
      }

      const inquiryId = result.data?.id;
      if (!inquiryId) {
        showToast("Failed to create inquiry: No ID returned", "error");
        return;
      }

      // ============================================================
      // STEP 2: Upload Photos (if any)
      // ============================================================
      if (state.selectedFiles.length > 0) {
        const photoFormData = new FormData();
        state.selectedFiles.forEach((file) => {
          photoFormData.append("photos", file);
        });

        const photoResponse = await fetch(
          `/api/api/inquiries/${inquiryId}/photos?stage=initial`,
          {
            method: "POST",
            body: photoFormData,
            signal: state.abortController.signal,
          },
        );

        if (!photoResponse.ok) {
          // Photos failed but inquiry created - log but continue
          console.warn(
            "Photo upload failed but inquiry was created successfully",
          );
          const photoText = await photoResponse.text();
          console.warn("Photo upload error:", photoText);
        }
      }

      // ============================================================
      // SUCCESS
      // ============================================================
      showSuccessModal();
      resetForm();
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }
      console.error("Submission error:", error);
      showToast(
        "Network error. Please check your connection and try again.",
        "error",
      );
    } finally {
      state.isSubmitting = false;
      dom.submitBtn.disabled = false;
      dom.submitBtn.textContent = "Start My Project";
      state.abortController = null;
    }
  }

  // ===== RESET FORM =====
  function resetForm() {
    dom.form?.reset();
    revokeObjectURLs();
    state.selectedFiles = [];
    if (dom.photoPreviewGrid) {
      dom.photoPreviewGrid.innerHTML = "";
      dom.photoPreviewGrid.style.display = "none";
    }
    updateUploadText();
    goToStep(1);
    if (dom.submitBtn) dom.submitBtn.disabled = true;
    clearErrors(dom.form);
    document.querySelectorAll(".service-card").forEach((card) => {
      card.classList.remove("selected");
    });
  }

  // ===== PHOTO HANDLING =====
  function handleFileUpload(files) {
    const validFiles = Array.from(files).filter((f) =>
      f.type.startsWith("image/"),
    );

    if (state.selectedFiles.length + validFiles.length > state.maxFiles) {
      showToast(`Maximum ${state.maxFiles} photos allowed.`, "error");
      return;
    }

    state.selectedFiles = [...state.selectedFiles, ...validFiles];
    renderPhotoPreviews();
    updateUploadText();
  }

  function renderPhotoPreviews() {
    const grid = dom.photoPreviewGrid;
    if (!grid) return;

    revokeObjectURLs();
    grid.innerHTML = "";

    if (state.selectedFiles.length === 0) {
      grid.style.display = "none";
      return;
    }

    grid.style.display = "grid";

    state.selectedFiles.forEach((file, index) => {
      const url = URL.createObjectURL(file);
      const item = document.createElement("div");
      item.className = "preview-item";

      item.innerHTML = `
                <img src="${url}" alt="Preview ${index + 1}" loading="lazy">
                <button class="remove-photo" data-index="${index}" aria-label="Remove photo">×</button>
            `;

      grid.appendChild(item);

      item.querySelector(".remove-photo")?.addEventListener("click", (e) => {
        e.stopPropagation();
        const idx = parseInt(e.target.dataset.index);
        if (!isNaN(idx)) {
          state.selectedFiles.splice(idx, 1);
          renderPhotoPreviews();
          updateUploadText();
        }
      });
    });
  }

  function updateUploadText() {
    const p = document.getElementById("uploadParagraph");
    if (p) {
      p.textContent =
        state.selectedFiles.length > 0
          ? `${state.selectedFiles.length} photo(s) selected. Click to add more.`
          : "Front • Rear • Left Side • Right Side • Dashboard • Damaged Area";
    }
  }

  // ===== BRAND/MODEL FILTER =====
  function filterModelsByBrand(brand) {
    if (!dom.modelSelect) return;

    const options = dom.modelSelect.querySelectorAll("option[data-brand]");
    let hasVisible = false;

    options.forEach((opt) => {
      if (brand && opt.dataset.brand === brand) {
        opt.style.display = "";
        hasVisible = true;
      } else {
        opt.style.display = "none";
      }
    });

    const currentOpt = dom.modelSelect.querySelector(
      `option[value="${dom.modelSelect.value}"]`,
    );
    if (currentOpt && currentOpt.style.display === "none") {
      dom.modelSelect.value = "";
    }

    // Reset placeholder visibility
    const placeholder = dom.modelSelect.querySelector('option[value=""]');
    if (placeholder) {
      placeholder.style.display = "";
    }
  }

  // ===== TOAST =====
  function showToast(message, type = "info") {
    const existing = document.querySelector(".custom-toast");
    if (existing) removeElement(existing);

    const toast = document.createElement("div");
    toast.className = `custom-toast toast-${type}`;
    toast.setAttribute("role", "alert");
    toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${type === "error" ? "⚠️" : "ℹ️"}</span>
                <span class="toast-message">${message}</span>
            </div>
            <button class="toast-close" aria-label="Close notification">&times;</button>
        `;

    Object.assign(toast.style, {
      position: "fixed",
      bottom: "30px",
      right: "30px",
      background: type === "error" ? "#2a1215" : "#1a1a1a",
      color: "#fff",
      padding: "16px 20px",
      borderRadius: "12px",
      border: `1px solid ${type === "error" ? "#ff4d4f" : "#ff6b00"}`,
      boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
      zIndex: "99999",
      maxWidth: "400px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "16px",
      animation: "slideUp 0.3s ease",
      fontFamily: "'Inter', sans-serif",
    });

    document.body.appendChild(toast);

    const close = () => {
      if (toast.parentNode) {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(20px)";
        setTimeout(() => removeElement(toast), 300);
      }
    };

    toast.querySelector(".toast-close")?.addEventListener("click", close);
    setTimeout(close, 5000);
  }

  // ===== SUCCESS MODAL =====
  function showSuccessModal() {
    const existing = document.querySelector(".custom-modal-overlay");
    if (existing) removeElement(existing);

    const overlay = document.createElement("div");
    overlay.className = "custom-modal-overlay";
    overlay.innerHTML = `
            <div class="custom-modal" role="dialog" aria-modal="true">
                <div class="custom-modal-icon">🚀</div>
                <h3>Project Submitted!</h3>
                <p>Thank you for choosing NOCTRA AUTOWORKS.

Our team will review your project details and contact you via WhatsApp within 24 hours.</p>
                <button class="custom-modal-btn">Got it!</button>
            </div>
        `;

    document.body.appendChild(overlay);

    const closeModal = () => removeElement(overlay);
    overlay
      .querySelector(".custom-modal-btn")
      ?.addEventListener("click", closeModal);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal();
    });
  }

  // ===== EVENT SETUP =====
  function setupEvents() {
    // Navigation
    dom.prevBtn?.addEventListener("click", () =>
      goToStep(state.currentStep - 1),
    );
    dom.nextBtn?.addEventListener("click", () =>
      goToStep(state.currentStep + 1),
    );

    // Submit
    dom.submitBtn?.addEventListener("click", submitForm);
    dom.form?.addEventListener("submit", (e) => {
      e.preventDefault();
      submitForm();
    });

    // Keyboard shortcut - Enter to advance
    dom.form?.addEventListener("keydown", (e) => {
      if (
        e.key === "Enter" &&
        (e.target.tagName === "INPUT" || e.target.tagName === "SELECT")
      ) {
        const isTextArea = e.target.tagName === "TEXTAREA";
        if (!isTextArea) {
          e.preventDefault();
          state.currentStep === state.totalSteps
            ? submitForm()
            : goToStep(state.currentStep + 1);
        }
      }
    });

    // Brand/Model filtering
    dom.brandSelect?.addEventListener("change", function () {
      filterModelsByBrand(this.value);
    });

    // Service cards toggle
    document
      .querySelectorAll('.service-card input[type="checkbox"]')
      .forEach((cb) => {
        cb.addEventListener("change", function () {
          this.closest(".service-card")?.classList.toggle(
            "selected",
            this.checked,
          );
        });
      });

    // Upload zone click
    dom.uploadZone?.addEventListener("click", () => dom.photoInput?.click());

    // Drag and drop
    dom.uploadZone?.addEventListener("dragover", (e) => {
      e.preventDefault();
      dom.uploadZone.classList.add("dragover");
    });

    dom.uploadZone?.addEventListener("dragleave", (e) => {
      e.preventDefault();
      dom.uploadZone.classList.remove("dragover");
    });

    dom.uploadZone?.addEventListener("drop", (e) => {
      e.preventDefault();
      dom.uploadZone.classList.remove("dragover");
      if (e.dataTransfer.files.length) {
        handleFileUpload(e.dataTransfer.files);
      }
    });

    // File input change
    dom.photoInput?.addEventListener("change", function () {
      if (this.files.length) {
        handleFileUpload(this.files);
        this.value = "";
      }
    });

    // Agreement checkbox
    dom.agreementCheck?.addEventListener("change", function () {
      if (dom.submitBtn) {
        dom.submitBtn.disabled = !this.checked;
      }
    });
  }

  // ===== INIT =====
  function init() {
    cacheDom();

    if (!dom.form) {
      console.warn("Inquiry form not found");
      return;
    }

    // Initial setup
    filterModelsByBrand(dom.brandSelect?.value || "");
    updateStep(1);
    if (dom.submitBtn) dom.submitBtn.disabled = true;

    injectStyles();
    setupEvents();

    console.log("NOCTRA AUTOWORKS Inquiry initialized");
  }

  // ===== STYLES =====
  function injectStyles() {
    const styleId = "inquiry-dynamic-styles";
    if (document.getElementById(styleId)) return;

    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
            .custom-toast {
                font-family: 'Inter', sans-serif !important;
            }
            .custom-toast.toast-error {
                border-color: #ff4d4f !important;
            }
            .custom-toast.toast-error .toast-icon {
                color: #ff4d4f;
            }
            .custom-toast.toast-info .toast-icon {
                color: #ff6b00;
            }
            .custom-modal-overlay {
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.85);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 99999;
                padding: 20px;
                backdrop-filter: blur(8px);
                animation: fadeIn 0.3s ease;
            }
            .custom-modal {
                background: #1a1a1a;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 20px;
                padding: 40px;
                max-width: 450px;
                width: 100%;
                text-align: center;
                animation: slideUp 0.4s ease;
                box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            }
            .custom-modal-icon { font-size: 64px; margin-bottom: 16px; }
            .custom-modal h3 { color: #fff; margin-bottom: 12px; font-size: 24px; font-weight: 600; }
            .custom-modal p { color: #aaa; margin-bottom: 24px; line-height: 1.8; white-space: pre-line; font-size: 0.95rem; }
            .custom-modal-btn {
                background: #ff6b00;
                color: #fff;
                border: none;
                padding: 14px 40px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 16px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-family: inherit;
            }
            .custom-modal-btn:hover {
                background: #ff7a1a;
                transform: translateY(-2px);
                box-shadow: 0 4px 16px rgba(255,107,0,0.3);
            }
            .spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255,255,255,0.3);
                border-top-color: #fff;
                border-radius: 50%;
                animation: spin 0.6s linear infinite;
                margin-right: 8px;
                vertical-align: middle;
            }
            .upload-zone.dragover {
                border-color: #ff6b00 !important;
                background: rgba(255,107,0,0.08) !important;
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes slideUp {
                from { opacity: 0; transform: translateY(40px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            .error-message {
                color: #ff4d4f;
                font-size: 0.75rem;
                margin-top: 4px;
                display: block;
                animation: fadeIn 0.2s ease;
            }
            input.error, select.error, textarea.error {
                border-color: #ff4d4f !important;
            }
            .photo-preview-grid {
                display: none;
                grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
                gap: 10px;
                margin-top: 15px;
            }
            .preview-item {
                position: relative;
                border-radius: 8px;
                overflow: hidden;
                aspect-ratio: 1;
                border: 1px solid rgba(255,255,255,0.08);
                transition: all 0.2s ease;
            }
            .preview-item:hover {
                border-color: #ff6b00;
                transform: scale(1.02);
            }
            .preview-item img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            .remove-photo {
                position: absolute;
                top: 4px;
                right: 4px;
                background: rgba(0,0,0,0.7);
                border: none;
                color: white;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                font-size: 16px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: 0.2s;
                line-height: 1;
                font-weight: 700;
            }
            .remove-photo:hover {
                background: #ff4d4f;
                transform: scale(1.1);
            }
            @media (max-width: 768px) {
                .custom-modal {
                    padding: 30px 20px;
                    margin: 20px;
                }
                .custom-modal-icon { font-size: 48px; }
                .custom-modal h3 { font-size: 20px; }
                .photo-preview-grid {
                    grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
                }
                .preview-item {
                    aspect-ratio: 1;
                }
                .remove-photo {
                    width: 20px;
                    height: 20px;
                    font-size: 12px;
                }
            }
            @media (max-width: 480px) {
                .photo-preview-grid {
                    grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
                    gap: 6px;
                }
                .remove-photo {
                    width: 18px;
                    height: 18px;
                    font-size: 10px;
                }
            }
        `;
    document.head.appendChild(style);
  }

  // ===== CLEANUP ON UNLOAD =====
  window.addEventListener("beforeunload", () => {
    abortPendingRequest();
    revokeObjectURLs();
    document
      .querySelectorAll(".custom-toast, .custom-modal-overlay")
      .forEach(removeElement);
  });

  // ===== START =====
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
