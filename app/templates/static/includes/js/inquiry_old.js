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
  const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  const YEAR_MIN = 1980; // Diperbaiki: konsisten dengan HTML min attribute
  const MAX_PHOTOS = 10;
  const MIN_DESCRIPTION_LENGTH = 20;
  const MIN_NAME_LENGTH = 2;
  const MAX_FILE_SIZE_MB = 5;

  // ─── Main Class ──────────────────────────────────────────────
  class InquiryWizard {
    // ─── Private fields ──────────────────────────────────────
    #dom = {};
    #state = {
      currentStep: 0,
      totalSteps: 3,
      isSubmitting: false,
      isUploading: false,
    };
    #photoFiles = [];
    #abortController = null;
    #isInitialized = false;

    // ─── Constructor ──────────────────────────────────────────
    constructor() {
      const form = document.getElementById("inquiryForm");
      if (!form) {
        console.warn("Inquiry form not found. Wizard not initialized.");
        return;
      }

      // Prevent multiple initialization
      if (window._inquiryWizardInstance) {
        console.warn("Inquiry Wizard already initialized.");
        return;
      }

      this.#dom.form = form;
      this.#cacheDomRefs();
      this.#bindEvents();
      this.#initWizard();
      this.#isInitialized = true;
      window._inquiryWizardInstance = this;

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
      refs.modal = document.getElementById("inquiryModal");

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
        modal,
      } = this.#dom;

      nextBtn?.addEventListener("click", () => this.#goNext());
      prevBtn?.addEventListener("click", () => this.#goPrev());

      // 🔥 Gunakan event submit biasa, jangan double
      form?.addEventListener("submit", (e) => this.#handleSubmit(e));

      // Phone number formatting
      phone_number?.addEventListener("input", (e) => {
        let val = e.target.value.replace(/[^0-9+]/g, "");
        // Pastikan +62 di depan
        if (val.startsWith("62") && !val.startsWith("+")) {
          val = "+" + val;
        }
        if (val.length > 0 && !val.startsWith("+")) {
          // Jika tidak mulai dengan +, tambahkan +62
          const numeric = val.replace(/\D/g, "");
          if (numeric.length > 0) {
            val = "+62" + numeric;
          }
        }
        e.target.value = val;
      });

      // License plate uppercase
      plate_number?.addEventListener("input", (e) => {
        e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
      });

      // Service cards toggle
      this.#dom.serviceCards.forEach((card) => {
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (!checkbox) return;

        const sync = () => {
          card.classList.toggle("selected", checkbox.checked);
        };

        card.addEventListener("click", (e) => {
          if (e.target.tagName !== "INPUT") {
            checkbox.checked = !checkbox.checked;
            sync();
          }
        });

        checkbox.addEventListener("change", sync);
        sync();
      });

      // Brand → Model filtering
      bike_brand?.addEventListener("change", () => this.#filterModels());
      this.#filterModels();

      // Photo upload
      project_photos?.addEventListener("change", (e) => {
        this.#handlePhotoUpload(e);
      });

      // Drag and drop
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

      // 🔥 Enter key → next step atau submit
      form?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
          e.preventDefault();
          if (this.#state.currentStep === this.#state.totalSteps - 1) {
            if (
              this.#validateStep(this.#state.currentStep) &&
              !this.#state.isSubmitting
            ) {
              // Gunakan submit langsung, bukan requestSubmit untuk menghindari infinite loop
              this.#handleSubmit(new Event("submit"));
            }
          } else {
            nextBtn?.click();
          }
        }
      });

      // 🔥 Close modal on backdrop click atau ESC key
      modal?.addEventListener("click", (e) => {
        if (
          e.target === modal ||
          e.target.classList.contains("modal-backdrop")
        ) {
          this.#closeModal();
        }
      });

      // ESC key to close modal
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal?.classList.contains("active")) {
          this.#closeModal();
        }
      });
    }

    // ─── Photo Handling ──────────────────────────────────────
    #handlePhotoUpload(event) {
      const input = event.target;
      const files = input.files;

      if (!files || files.length === 0) {
        // Jika tidak ada file, reset photoFiles
        this.#photoFiles = [];
        this.#updatePhotoPreview();
        return;
      }

      // Validate file count
      if (files.length > MAX_PHOTOS) {
        this.#showAlert(
          "warning",
          "Terlalu Banyak Foto",
          `Maksimal ${MAX_PHOTOS} foto diperbolehkan.`,
        );
        input.value = "";
        this.#photoFiles = [];
        this.#updatePhotoPreview();
        return;
      }

      // Validate file size
      for (const file of files) {
        if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
          this.#showAlert(
            "warning",
            "File Terlalu Besar",
            `File "${file.name}" melebihi ${MAX_FILE_SIZE_MB}MB.`,
          );
          input.value = "";
          this.#photoFiles = [];
          this.#updatePhotoPreview();
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

      // Bersihkan grid dengan aman
      while (grid.firstChild) {
        grid.removeChild(grid.firstChild);
      }

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
            const dt = new DataTransfer();
            this.#photoFiles.forEach((f) => dt.items.add(f));
            this.#dom.project_photos.files = dt.files;
            this.#updatePhotoPreview();
          });

          wrapper.appendChild(img);
          wrapper.appendChild(removeBtn);
          grid.appendChild(wrapper);
        };
        reader.onerror = () => {
          console.error("Failed to read file:", file.name);
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
      // Cek source dari query param
      const urlParams = new URLSearchParams(window.location.search);
      const source = urlParams.get("source") || "website";
      console.log(`📊 Source: ${source}`);
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
        this.#showError(
          phone_number,
          "Masukkan nomor WhatsApp yang valid (contoh: +628123456789).",
        );
        valid = false;
      }

      const mail = email?.value.trim() || "";
      if (!EMAIL_REGEX.test(mail)) {
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

      const conditions = this.#getSelectedConditions();
      if (conditions.length === 0) {
        this.#showAlert(
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
        this.#showAlert(
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

    // ─── Alert System (SweetAlert2) ──────────────────────────
    #showAlert(type, title, message) {
      if (typeof Swal !== "undefined") {
        const iconMap = {
          success: "success",
          error: "error",
          warning: "warning",
          info: "info",
        };
        Swal.fire({
          title: title,
          text: message,
          icon: iconMap[type] || "info",
          confirmButtonColor: "#ff6b00",
          background: "#0a0a0a",
          color: "#f1f5f9",
          confirmButtonText: "OK",
        });
      } else {
        // Fallback ke modal custom
        const existing = document.querySelector(".custom-modal-overlay");
        if (existing) existing.remove();
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
        const close = () => modal.remove();
        closeBtn.addEventListener("click", close);
        modal.addEventListener("click", (e) => {
          if (e.target === modal) close();
        });
      }
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

    // ─── Close Modal ──────────────────────────────────────────
    #closeModal() {
      const modal = this.#dom.modal;
      if (modal && modal.classList.contains("active")) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
        document.documentElement.style.overflow = "";
        document.body.classList.remove("modal-open");
        // Abort pending requests
        this.#abortRequests();
        // Dispatch event
        document.dispatchEvent(new CustomEvent("modalClosed"));
      }
    }

    // ─── API ──────────────────────────────────────────────────
    async #createInquiry(payload) {
      const controller = new AbortController();
      this.#abortController = controller;

      const response = await fetch(API_BASE, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
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

      const controller = new AbortController();
      this.#abortController = controller;

      const response = await fetch(`${API_BASE}${inquiryId}/photos`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.message || "Gagal upload foto");
      }

      return data;
    }

    // ─── Form Submission ──────────────────────────────────────
    async #handleSubmit(event) {
      // Prevent default only if event is not already prevented
      if (event && event.preventDefault) {
        event.preventDefault();
      }

      if (this.#state.isSubmitting || this.#state.isUploading) return;

      if (!this.#validateStep(2)) return;

      this.#state.isSubmitting = true;
      const submitBtn = this.#dom.submitBtn;
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Mengirim...";
        submitBtn.style.opacity = "0.7";
      }

      try {
        // Get source from query param
        const urlParams = new URLSearchParams(window.location.search);
        const source = urlParams.get("source") || "website";

        // Build payload
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
          source: source,
        };

        console.log("📤 Submitting inquiry:", payload);

        const response = await this.#createInquiry(payload);
        const inquiryId = response?.data?.id;

        if (!inquiryId) {
          throw new Error(
            "Tidak ada ID inquiry yang dikembalikan dari server.",
          );
        }

        // Upload photos if any
        if (this.#photoFiles.length > 0) {
          this.#state.isUploading = true;
          if (submitBtn) {
            submitBtn.textContent = "Mengupload foto...";
          }
          try {
            await this.#uploadPhotos(inquiryId, this.#photoFiles);
          } catch (uploadErr) {
            console.warn("⚠️ Photo upload failed:", uploadErr);
            // Tampilkan peringatan tapi inquiry sudah terbuat
            this.#showAlert(
              "warning",
              "Foto Gagal Diupload",
              `Inquiry berhasil dibuat (ID: ${inquiryId}), tetapi foto gagal diupload. Anda bisa mengirim ulang foto melalui WhatsApp.`,
            );
            // Lanjut ke sukses
          } finally {
            this.#state.isUploading = false;
          }
        }

        // ✅ SUCCESS
        this.#showAlert(
          "success",
          "🎉 Project Submitted!",
          `Permintaan Anda (ID: ${inquiryId}) telah berhasil dikirim!\n\nTim kami akan segera menghubungi Anda melalui WhatsApp dalam 1x24 jam.`,
        );

        // Reset form & close modal
        this.#resetForm();
        this.#closeModal();
      } catch (err) {
        console.error("Submission error:", err);

        if (err.name === "AbortError") {
          // User canceled, ignore
          return;
        }

        this.#showAlert(
          "error",
          "Gagal Mengirim",
          err.message || "Terjadi kesalahan. Silakan coba lagi.",
        );
      } finally {
        this.#state.isSubmitting = false;
        this.#state.isUploading = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Mulai Project Saya";
          submitBtn.style.opacity = "1";
        }
        this.#abortController = null;
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
        // Bersihkan grid dengan aman
        while (grid.firstChild) {
          grid.removeChild(grid.firstChild);
        }
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

      const photoInput = this.#dom.project_photos;
      if (photoInput) photoInput.value = "";

      // Reset model filter
      this.#filterModels();
    }

    // ─── Abort pending requests ──────────────────────────────
    #abortRequests() {
      if (this.#abortController) {
        this.#abortController.abort();
        this.#abortController = null;
      }
    }

    // ─── Public method untuk cleanup ─────────────────────────
    destroy() {
      this.#abortRequests();
      window._inquiryWizardInstance = null;
      this.#isInitialized = false;
    }

    // ─── Public getter untuk cek status ──────────────────────
    isInitialized() {
      return this.#isInitialized;
    }
  }

  // ─── Instantiate ─────────────────────────────────────────────
  let wizardInstance = null;

  document.addEventListener("DOMContentLoaded", () => {
    wizardInstance = new InquiryWizard();
  });

  // 🔥 Jika modal ditutup, abort pending requests
  document.addEventListener("modalClosed", () => {
    if (wizardInstance && wizardInstance.isInitialized()) {
      // Panggil method private melalui public method
      wizardInstance.destroy();
      // Re-initialize jika diperlukan
      wizardInstance = new InquiryWizard();
    }
  });

  // Cleanup on page unload
  window.addEventListener("beforeunload", () => {
    if (wizardInstance) {
      wizardInstance.destroy();
    }
  });
})();
