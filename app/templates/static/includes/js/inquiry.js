/**
 * NOCTRA Inquiry Wizard
 * Multi-step form with API integration for customer inquiries.
 * Based on CustomerInquiryCreate schema
 */
(function () {
  "use strict";

  // ─── Constants ──────────────────────────────────────────────
  const API_BASE = "/api/api/inquiries/";
  const PHONE_REGEX = /^(\+62|62|08)\d{8,13}$/;
  const YEAR_MIN = 1950;
  const MAX_PHOTOS = 10;
  const MIN_DESCRIPTION_LENGTH = 20;
  const MIN_NAME_LENGTH = 2;

  // ─── Main Class ──────────────────────────────────────────────
  class InquiryWizard {
    // ─── Private fields ──────────────────────────────────────
    #dom = {};
    #state = {
      currentStep: 0,
      isSubmitting: false,
      totalSteps: 3,
    };
    #photoFiles = [];

    // ─── Constructor ──────────────────────────────────────────
    constructor() {
      const form = document.getElementById("inquiryForm");
      if (!form) {
        console.warn("Inquiry form not found. Wizard not initialized.");
        return;
      }
      this.#dom.form = form;
      this.#cacheDomRefs();
      this.#bindEvents();
      this.#initWizard();
      console.log("✅ Inquiry Wizard initialized");
    }

    // ─── DOM Caching ──────────────────────────────────────────
    #cacheDomRefs() {
      const ids = [
        "fullname",
        "phone_number",
        "email",
        "province",
        "city",
        "bike_brand",
        "bike_model",
        "bike_year",
        "plate_number",
        "previous_repaint",
        "bike_modified",
        "project_type",
        "desired_finish",
        "desired_color",
        "estimated_budget",
        "deadline",
        "priority",
        "project_details",
        "reference_link",
        "project_photos",
        "nextBtn",
        "prevBtn",
        "submitBtn",
        "progressLine",
        "agreementCheck",
        "photoPreviewGrid",
        "uploadParagraph",
        "uploadZone",
      ];
      const refs = {};
      ids.forEach((id) => {
        refs[id] = document.getElementById(id);
      });
      refs.pages = document.querySelectorAll(".wizard-page");
      refs.steps = document.querySelectorAll(".step");
      refs.serviceCards = document.querySelectorAll(".service-card");
      refs.conditionCheckboxes = document.querySelectorAll(
        'input[name="condition"]',
      );
      refs.servicesCheckboxes = document.querySelectorAll(
        'input[name="services"]',
      );

      this.#dom = { ...this.#dom, ...refs };
    }

    // ─── Event Binding ────────────────────────────────────────
    #bindEvents() {
      const {
        form,
        nextBtn,
        prevBtn,
        submitBtn,
        phone_number,
        plate_number,
        project_photos,
        bike_brand,
        bike_model,
      } = this.#dom;

      nextBtn?.addEventListener("click", () => this.#goNext());
      prevBtn?.addEventListener("click", () => this.#goPrev());
      form?.addEventListener("submit", (e) => this.#handleSubmit(e));

      // Phone number formatting - hanya angka dan +
      phone_number?.addEventListener("input", (e) => {
        e.target.value = e.target.value.replace(/[^0-9+]/g, "");
        e.target.value = e.target.value.replace(/(\+62|62)/, "+62");
      });

      // License plate uppercase
      plate_number?.addEventListener("input", (e) => {
        e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
      });

      // Service cards toggle - click entire card
      this.#dom.serviceCards.forEach((card) => {
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (!checkbox) return;

        const sync = () => {
          card.classList.toggle("selected", checkbox.checked);
        };

        card.addEventListener("click", (e) => {
          // Prevent double toggle if checkbox clicked directly
          if (e.target.tagName !== "INPUT") {
            checkbox.checked = !checkbox.checked;
            sync();
          }
        });

        checkbox.addEventListener("change", sync);
        sync();
      });

      // Brand - Model dependency
      bike_brand?.addEventListener("change", () => this.#filterModels());
      this.#filterModels();

      // Photo upload
      project_photos?.addEventListener("change", (e) => {
        this.#handlePhotoUpload(e);
      });

      // Drag and drop support
      const uploadZone = this.#dom.uploadZone;
      if (uploadZone) {
        uploadZone.addEventListener("dragover", (e) => {
          e.preventDefault();
          uploadZone.classList.add("dragover");
        });
        uploadZone.addEventListener("dragleave", () => {
          uploadZone.classList.remove("dragover");
        });
        uploadZone.addEventListener("drop", (e) => {
          e.preventDefault();
          uploadZone.classList.remove("dragover");
          if (e.dataTransfer.files.length > 0) {
            this.#dom.project_photos.files = e.dataTransfer.files;
            this.#handlePhotoUpload({ target: this.#dom.project_photos });
          }
        });
      }

      // 🔥 FIXED: Enter key support - prevent double submission
      form?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
          e.preventDefault();
          const currentStep = this.#state.currentStep;
          if (currentStep === this.#state.totalSteps - 1) {
            // 🔥 FIX: Gunakan form.dispatchEvent untuk trigger submit
            // Ini akan memicu event submit yang sudah di-handle oleh form listener
            // Dan mencegah double trigger karena kita tidak memanggil click() pada submitBtn
            if (this.#validateStep(currentStep)) {
              // Gunakan form.requestSubmit() untuk trigger submit secara native
              // Ini akan memicu event submit yang sama seperti klik tombol submit
              form.requestSubmit();
            }
          } else {
            nextBtn?.click();
          }
        }
      });
    }

    // ─── Photo Handling ──────────────────────────────────────
    #handlePhotoUpload(event) {
      const input = event.target;
      const files = input.files;

      if (!files || files.length === 0) return;

      // Validate file count
      if (files.length > MAX_PHOTOS) {
        this.#showModal(
          "warning",
          "Too Many Photos",
          `Maksimal ${MAX_PHOTOS} foto diperbolehkan.`,
        );
        input.value = "";
        return;
      }

      // Validate file size (max 5MB each)
      for (const file of files) {
        if (file.size > 5 * 1024 * 1024) {
          this.#showModal(
            "warning",
            "File Too Large",
            `File "${file.name}" melebihi 5MB.`,
          );
          input.value = "";
          return;
        }
      }

      this.#photoFiles = Array.from(files);
      this.#updatePhotoPreview();
    }

    #updatePhotoPreview() {
      const grid = this.#dom.photoPreviewGrid;
      const paragraph = this.#dom.uploadParagraph;
      if (!grid) return;

      grid.innerHTML = "";
      const files = this.#photoFiles;

      if (!files || files.length === 0) {
        grid.style.display = "none";
        if (paragraph) {
          paragraph.textContent =
            "Drag & drop foto di sini atau klik untuk mencari. (Max 10)";
        }
        return;
      }

      grid.style.display = "grid";

      files.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const img = document.createElement("img");
          img.src = e.target.result;
          img.alt = `Photo ${index + 1}`;
          img.loading = "lazy";

          const wrapper = document.createElement("div");
          wrapper.className = "preview-item";

          const removeBtn = document.createElement("button");
          removeBtn.type = "button";
          removeBtn.className = "remove-photo";
          removeBtn.innerHTML = "×";
          removeBtn.title = "Hapus foto";
          removeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            this.#photoFiles.splice(index, 1);
            // Update input files
            const dt = new DataTransfer();
            this.#photoFiles.forEach((f) => dt.items.add(f));
            this.#dom.project_photos.files = dt.files;
            this.#updatePhotoPreview();
          });

          wrapper.appendChild(img);
          wrapper.appendChild(removeBtn);
          grid.appendChild(wrapper);
        };
        reader.readAsDataURL(file);
      });

      if (paragraph) {
        paragraph.textContent = `${files.length} foto terpilih (Max ${MAX_PHOTOS})`;
      }
    }

    // ─── Model Filtering ──────────────────────────────────────
    #filterModels() {
      const { bike_brand, bike_model } = this.#dom;
      if (!bike_brand || !bike_model) return;

      const selectedBrand = bike_brand.value;
      const options = bike_model.querySelectorAll("option");

      options.forEach((option) => {
        if (option.value === "") {
          option.style.display = "";
          return;
        }
        const brand = option.dataset.brand;
        option.style.display = brand === selectedBrand ? "" : "none";
      });

      // Reset selection if current model doesn't match brand
      if (bike_model.value) {
        const selectedOption = bike_model.querySelector(
          `option[value="${bike_model.value}"]`,
        );
        if (selectedOption && selectedOption.style.display === "none") {
          bike_model.value = "";
        }
      }
    }

    // ─── Wizard Navigation ────────────────────────────────────
    #goNext() {
      if (!this.#validateStep(this.#state.currentStep)) return;
      if (this.#state.currentStep < this.#dom.pages.length - 1) {
        this.#state.currentStep++;
        this.#updateWizard();
        // Scroll to top of form
        this.#dom.form?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }

    #goPrev() {
      if (this.#state.currentStep > 0) {
        this.#state.currentStep--;
        this.#updateWizard();
        this.#dom.form?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }

    #initWizard() {
      this.#updateWizard();
    }

    #updateWizard() {
      const { pages, steps, prevBtn, nextBtn, submitBtn, progressLine } =
        this.#dom;
      const current = this.#state.currentStep;
      const total = pages.length - 1;

      pages.forEach((page, index) => {
        page.classList.toggle("active", index === current);
      });

      steps.forEach((step, index) => {
        step.classList.toggle("active", index <= current);
        const small = step.querySelector("small");
        if (small) {
          small.style.color = index <= current ? "#ffffff" : "#7a7a7a";
        }
      });

      if (prevBtn) {
        prevBtn.style.display = current === 0 ? "none" : "inline-flex";
      }
      if (nextBtn) {
        nextBtn.style.display = current === total ? "none" : "inline-flex";
      }
      if (submitBtn) {
        submitBtn.style.display = current === total ? "inline-flex" : "none";
      }

      if (progressLine) {
        const percentage = total <= 0 ? 0 : (current / total) * 100;
        progressLine.style.background = `linear-gradient(90deg, #ff6b00 ${percentage}%, rgba(255,255,255,.08) ${percentage}%)`;
      }

      // Update step numbers
      steps.forEach((step, index) => {
        const span = step.querySelector("span");
        if (span) {
          span.textContent = index + 1;
        }
      });
    }

    // ─── Validation ───────────────────────────────────────────
    #validateStep(step) {
      this.#clearErrors();
      switch (step) {
        case 0:
          return this.#validateStepOne();
        case 1:
          return this.#validateStepTwo();
        case 2:
          return this.#validateStepThree();
        default:
          return true;
      }
    }

    #validateStepOne() {
      const { fullname, phone_number, email, province, city } = this.#dom;
      let valid = true;

      const name = fullname?.value.trim() || "";
      if (name.length < MIN_NAME_LENGTH) {
        this.#showError(
          fullname,
          `Nama lengkap minimal ${MIN_NAME_LENGTH} karakter.`,
        );
        valid = false;
      }

      const phone = phone_number?.value.trim() || "";
      if (!PHONE_REGEX.test(phone)) {
        this.#showError(phone_number, "Masukkan nomor WhatsApp yang valid.");
        valid = false;
      }

      const mail = email?.value.trim() || "";
      if (!mail || !mail.includes("@") || !mail.includes(".")) {
        this.#showError(email, "Masukkan alamat email yang valid.");
        valid = false;
      }

      const provinceVal = province?.value.trim() || "";
      if (provinceVal.length < 2) {
        this.#showError(province, "Provinsi harus diisi.");
        valid = false;
      }

      const cityVal = city?.value.trim() || "";
      if (cityVal.length < 2) {
        this.#showError(city, "Kota / Kabupaten harus diisi.");
        valid = false;
      }

      // Highlight invalid fields
      if (!valid) {
        this.#dom.form?.scrollIntoView({ behavior: "smooth", block: "center" });
      }

      return valid;
    }

    #validateStepTwo() {
      const {
        bike_brand,
        bike_model,
        bike_year,
        previous_repaint,
        bike_modified,
      } = this.#dom;
      let valid = true;

      if (!bike_brand?.value) {
        this.#showError(bike_brand, "Pilih merek motor.");
        valid = false;
      }

      if (!bike_model?.value || bike_model.value.trim().length < 1) {
        this.#showError(bike_model, "Model motor harus diisi.");
        valid = false;
      }

      if (bike_year?.value) {
        const year = parseInt(bike_year.value, 10);
        const currentYear = new Date().getFullYear();
        if (isNaN(year) || year < YEAR_MIN || year > currentYear + 1) {
          this.#showError(
            bike_year,
            `Masukkan tahun produksi yang valid (${YEAR_MIN} - ${currentYear + 1}).`,
          );
          valid = false;
        }
      }

      if (!previous_repaint?.value) {
        this.#showError(previous_repaint, "Pilih riwayat repaint.");
        valid = false;
      }

      if (!bike_modified?.value) {
        this.#showError(bike_modified, "Pilih status modifikasi.");
        valid = false;
      }

      // Check if at least one condition is selected
      const conditions = this.#getSelectedConditions();
      if (conditions.length === 0) {
        this.#showModal(
          "warning",
          "Kondisi Kendaraan Diperlukan",
          "Pilih setidaknya satu kondisi kendaraan.",
        );
        valid = false;
      }

      if (!valid) {
        this.#dom.form?.scrollIntoView({ behavior: "smooth", block: "center" });
      }

      return valid;
    }

    #validateStepThree() {
      const {
        project_type,
        priority,
        project_details,
        reference_link,
        desired_color,
        agreementCheck,
      } = this.#dom;
      let valid = true;

      if (!project_type?.value) {
        this.#showError(project_type, "Pilih tipe project.");
        valid = false;
      }

      if (!priority?.value) {
        this.#showError(priority, "Pilih prioritas utama Anda.");
        valid = false;
      }

      const color = desired_color?.value.trim() || "";
      if (!color || color.length < 2) {
        this.#showError(desired_color, "Masukkan warna yang diinginkan.");
        valid = false;
      }

      if (!agreementCheck?.checked) {
        this.#showError(
          agreementCheck,
          "Anda harus menyetujui syarat untuk melanjutkan.",
        );
        valid = false;
      }

      const services = this.#getSelectedServices();
      if (services.length === 0) {
        this.#showModal(
          "warning",
          "Layanan Diperlukan",
          "Pilih setidaknya satu layanan.",
        );
        valid = false;
      }

      const desc = project_details?.value.trim() || "";
      if (desc.length < MIN_DESCRIPTION_LENGTH) {
        this.#showError(
          project_details,
          `Deskripsi project minimal ${MIN_DESCRIPTION_LENGTH} karakter.`,
        );
        valid = false;
      }

      const ref = reference_link?.value.trim() || "";
      if (ref && !this.#isValidUrl(ref)) {
        this.#showError(reference_link, "Masukkan URL yang valid.");
        valid = false;
      }

      if (this.#photoFiles.length > MAX_PHOTOS) {
        this.#showError(
          this.#dom.project_photos,
          `Maksimal ${MAX_PHOTOS} foto diperbolehkan.`,
        );
        valid = false;
      }

      if (!valid) {
        this.#dom.form?.scrollIntoView({ behavior: "smooth", block: "center" });
      }

      return valid;
    }

    // ─── Modal System ──────────────────────────────────────────
    #showModal(type, title, message) {
      const existingModal = document.querySelector(".custom-modal-overlay");
      if (existingModal) existingModal.remove();

      const modal = document.createElement("div");
      modal.className = "custom-modal-overlay";

      const iconMap = {
        success: "✅",
        error: "❌",
        warning: "⚠️",
        info: "ℹ️",
      };

      modal.innerHTML = `
        <div class="custom-modal">
          <div class="custom-modal-icon">${iconMap[type] || "ℹ️"}</div>
          <h3>${title}</h3>
          <p>${message}</p>
          <button class="custom-modal-btn" id="modalCloseBtn">OK</button>
        </div>
      `;

      document.body.appendChild(modal);

      const closeBtn = modal.querySelector("#modalCloseBtn");
      const closeModal = () => modal.remove();

      closeBtn.addEventListener("click", closeModal);
      modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
      });

      // Close with Escape key
      const escHandler = (e) => {
        if (e.key === "Escape") {
          closeModal();
          document.removeEventListener("keydown", escHandler);
        }
      };
      document.addEventListener("keydown", escHandler);
    }

    // ─── Helpers ──────────────────────────────────────────────
    #clearErrors() {
      document.querySelectorAll(".error-message").forEach((el) => el.remove());
      document.querySelectorAll("input, textarea, select").forEach((field) => {
        field.style.borderColor = "";
      });
    }

    #showError(field, message) {
      if (!field) return;
      field.style.borderColor = "#ff4d4f";

      let parent = field.parentElement;
      if (field.type === "checkbox") {
        parent =
          field.closest(".checkbox-label") || field.closest(".input-group");
      }

      if (!parent) return;
      const existing = parent.querySelector(".error-message");
      if (existing) existing.remove();

      const error = document.createElement("small");
      error.className = "error-message";
      error.textContent = message;
      parent.appendChild(error);
    }

    #isValidUrl(url) {
      try {
        new URL(url);
        return true;
      } catch {
        return false;
      }
    }

    #getSelectedConditions() {
      return Array.from(
        document.querySelectorAll('input[name="condition"]:checked'),
      ).map((cb) => cb.value);
    }

    #getSelectedServices() {
      return Array.from(
        document.querySelectorAll('input[name="services"]:checked'),
      ).map((cb) => cb.value);
    }

    #parseBudgetValue() {
      const select = this.#dom.estimated_budget;
      if (!select || !select.value) return null;
      const num = parseInt(select.value, 10);
      return isNaN(num) ? null : num;
    }

    // ─── API ──────────────────────────────────────────────────
    async #createInquiry(payload) {
      const response = await fetch(API_BASE, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.message ||
            data?.error ||
            data?.detail ||
            `HTTP ${response.status}`,
        );
      }

      return data;
    }

    async #uploadPhotos(inquiryId, files) {
      const formData = new FormData();
      files.forEach((file) => formData.append("photos", file));

      const response = await fetch(`${API_BASE}${inquiryId}/photos`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.message || "Failed to upload photos");
      }

      return data;
    }

    // ─── Form Submission ──────────────────────────────────────
    async #handleSubmit(event) {
      // 🔥 FIX: Prevent multiple submissions
      event.preventDefault();

      // 🔥 FIX: Cek apakah sudah dalam proses submit
      if (this.#state.isSubmitting) return;

      if (!this.#validateStep(2)) return;

      this.#state.isSubmitting = true;
      const submitBtn = this.#dom.submitBtn;
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Mengirim...";
        submitBtn.style.opacity = "0.7";
      }

      try {
        // 🔥 Build payload sesuai dengan CustomerInquiryCreate schema
        const payload = {
          customer_name: this.#dom.fullname?.value.trim() || "",
          customer_phone_number: this.#dom.phone_number?.value.trim() || "",
          customer_email: this.#dom.email?.value.trim() || "",
          province: this.#dom.province?.value.trim() || "",
          city: this.#dom.city?.value.trim() || "",
          vehicle_brand: this.#dom.bike_brand?.value || "",
          vehicle_model: this.#dom.bike_model?.value.trim() || "",
          vehicle_year: this.#dom.bike_year?.value
            ? parseInt(this.#dom.bike_year.value, 10)
            : null,
          vehicle_license_plate: this.#dom.plate_number?.value.trim() || "",
          previous_repaint: this.#dom.previous_repaint?.value || "",
          bike_modified: this.#dom.bike_modified?.value || "",
          vehicle_condition: this.#getSelectedConditions().join(", "),
          project_type: this.#dom.project_type?.value || "",
          services: this.#getSelectedServices().join(", "),
          desired_finish: this.#dom.desired_finish?.value || "",
          desired_color: this.#dom.desired_color?.value.trim() || "",
          estimated_budget: this.#parseBudgetValue(),
          deadline: this.#dom.deadline?.value || "",
          priority: this.#dom.priority?.value || "",
          project_description: this.#dom.project_details?.value.trim() || "",
          reference_link: this.#dom.reference_link?.value.trim() || "",
          source: "website",
        };

        console.log("📤 Submitting inquiry:", payload);

        const response = await this.#createInquiry(payload);
        const inquiryId = response?.data?.id;

        if (!inquiryId) {
          throw new Error("No inquiry ID returned from server");
        }

        // Upload photos if any
        if (this.#photoFiles.length > 0) {
          await this.#uploadPhotos(inquiryId, this.#photoFiles);
        }

        // ✅ SUCCESS
        this.#showModal(
          "success",
          "🎉 Project Submitted!",
          `Permintaan Anda (ID: ${inquiryId}) telah berhasil dikirim!\n\nTim kami akan segera menghubungi Anda melalui WhatsApp dalam 1x24 jam.`,
        );

        this.#resetForm();
      } catch (err) {
        console.error("Submission error:", err);

        // ❌ ERROR
        this.#showModal(
          "error",
          "Gagal Mengirim",
          err.message || "Terjadi kesalahan. Silakan coba lagi.",
        );
      } finally {
        this.#state.isSubmitting = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Mulai Project Saya";
          submitBtn.style.opacity = "1";
        }
      }
    }

    #resetForm() {
      const form = this.#dom.form;
      if (form) form.reset();

      document
        .querySelectorAll(".service-card")
        .forEach((c) => c.classList.remove("selected"));

      this.#photoFiles = [];
      const grid = this.#dom.photoPreviewGrid;
      if (grid) {
        grid.innerHTML = "";
        grid.style.display = "none";
      }

      const p = this.#dom.uploadParagraph;
      if (p) {
        p.textContent =
          "Drag & drop foto di sini atau klik untuk mencari. (Max 10)";
      }

      this.#state.currentStep = 0;
      this.#clearErrors();
      this.#updateWizard();
      this.#filterModels();

      // Reset file input
      const photoInput = this.#dom.project_photos;
      if (photoInput) photoInput.value = "";

      // Reset model filter
      this.#filterModels();
    }
  }

  // ─── Instantiate ─────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    new InquiryWizard();
  });
})();
