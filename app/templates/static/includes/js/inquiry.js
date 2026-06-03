const $ = (selector) => document.querySelector(selector);

const form = $(".inquiry-form");

if (!form) {
  console.warn("Inquiry form not found.");
} else {
  /* ======================
     ELEMENTS
  ====================== */

  const platePrefix = $(".plate-prefix");
  const plateNumber = $(".plate-number");
  const plateSuffix = $(".plate-suffix");

  const fullName = $("#fullname");
  const phone = $("#phone_number");
  const bikeBrand = $("#bike_brand");
  const bikeModel = $("#bike_model");
  const bodyCondition = $("#body_condition");
  const details = $("#project_details");
  const reference = $("#reference_link");
  const photos = $("#project_photos");

  const pages = document.querySelectorAll(".wizard-page");
  const steps = document.querySelectorAll(".step");

  const nextBtn = $("#nextBtn");
  const prevBtn = $("#prevBtn");
  const submitBtn = $("#submitBtn");

  /* ======================
     AUTO UPPERCASE
  ====================== */

  [platePrefix, plateSuffix].forEach((el) => {
    if (!el) return;

    el.addEventListener("input", (e) => {
      e.target.value = e.target.value.toUpperCase();
    });
  });

  /* ======================
     VALIDATION
  ====================== */

  function showError(input, message) {
    if (!input) return;

    input.style.borderColor = "#ff4d4f";

    const existing =
      input.parentElement?.querySelector(".error-message");

    if (existing) existing.remove();

    const err = document.createElement("small");

    err.className = "error-message";
    err.textContent = message;

    input.parentElement?.appendChild(err);
  }

  function clearErrors() {
    document
      .querySelectorAll(".error-message")
      .forEach((el) => el.remove());

    document
      .querySelectorAll("input, textarea, select")
      .forEach((el) => {
        el.style.borderColor = "";
      });
  }

  /* ======================
     WIZARD
  ====================== */

  let currentStep = 0;

  function updateWizard() {
    pages.forEach((page) => {
      page.classList.remove("active");
    });

    steps.forEach((step) => {
      step.classList.remove("active");
    });

    pages[currentStep]?.classList.add("active");

    steps.forEach((step, index) => {
      if (index <= currentStep) {
        step.classList.add("active");
      }
    });

    if (prevBtn) {
      prevBtn.style.display =
        currentStep === 0 ? "none" : "block";
    }

    if (nextBtn) {
      nextBtn.style.display =
        currentStep === pages.length - 1
          ? "none"
          : "block";
    }

    if (submitBtn) {
      submitBtn.style.display =
        currentStep === pages.length - 1
          ? "block"
          : "none";
    }
  }

  function validateStep(step) {
    clearErrors();
    let valid = true;

    if (step === 0) {
      if (!fullName?.value.trim() || fullName.value.trim().length < 3) {
        showError(fullName, "Nama minimal 3 karakter.");
        valid = false;
      }

      const phoneRegex = /^(\+62|62|08)[0-9]{8,13}$/;
      if (!phoneRegex.test(phone?.value.trim() || "")) {
        showError(phone, "Nomor WhatsApp tidak valid.");
        valid = false;
      }

      if (!bikeModel?.value.trim() || bikeModel.value.trim().length < 2) {
        showError(bikeModel, "Model motor wajib diisi.");
        valid = false;
      }

      if (!/^[A-Z]{1,2}$/.test(platePrefix?.value.trim() || "")) {
        showError(platePrefix, "Contoh: D");
        valid = false;
      }

      if (!/^\d{1,4}$/.test(plateNumber?.value.trim() || "")) {
        showError(plateNumber, "Contoh: 6637");
        valid = false;
      }

      if (!/^[A-Z]{1,3}$/.test(plateSuffix?.value.trim() || "")) {
        showError(plateSuffix, "Contoh: KK");
        valid = false;
      }
    }

    if (step === 1) {
      const selectedServices = [
        ...document.querySelectorAll(
          ".service-card input[type='checkbox']:checked"
        ),
      ];
      if (selectedServices.length === 0) {
        alert("Pilih minimal satu layanan.");
        valid = false;
      }
    }

    return valid;
  }

  nextBtn?.addEventListener("click", () => {
    if (!validateStep(currentStep)) return;
    if (currentStep < pages.length - 1) {
      currentStep++;
      updateWizard();
    }
  });

  prevBtn?.addEventListener("click", () => {
    if (currentStep > 0) {
      currentStep--;
      updateWizard();
    }
  });

  updateWizard();

  /* ======================
     SUBMIT
  ====================== */

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    clearErrors();

    let valid = true;

    // Step 0 & 1 already validated before advancing — only validate step 2 here
    const selectedServices = [
      ...document.querySelectorAll(
        ".service-card input[type='checkbox']:checked"
      ),
    ].map((checkbox) =>
      checkbox.parentElement
        ?.querySelector("span")
        ?.textContent.trim()
    );

    if (!details?.value.trim() || details.value.trim().length < 20) {
      showError(details, "Deskripsi minimal 20 karakter.");
      valid = false;
    }

    if (reference?.value.trim()) {
      try {
        new URL(reference.value.trim());
      } catch {
        showError(reference, "URL tidak valid.");
        valid = false;
      }
    }

    if (photos?.files?.length > 5) {
      showError(photos, "Maksimal 5 foto.");
      valid = false;
    }

    if (!valid) return;

    const data = {
      fullname: fullName.value.trim(),
      phone: phone.value.trim(),
      plate: `${platePrefix.value.trim()}-${plateNumber.value.trim()}-${plateSuffix.value.trim()}`,
      brand: bikeBrand?.value || "",
      model: bikeModel.value.trim(),
      services: selectedServices,
      condition: bodyCondition?.value || "",
      details: details.value.trim(),
      reference: reference?.value.trim() || "",
      photo_count: photos?.files?.length || 0,
    };

    console.log("Inquiry Data:", data);

    alert("Inquiry berhasil dikirim.");

    form.reset();

    currentStep = 0;

    clearErrors();
    updateWizard();
  });
}