const $ = (selector, parent = document) => parent.querySelector(selector);

const $$ = (selector, parent = document) => [
  ...parent.querySelectorAll(selector),
];

const form = $(".inquiry-form");

if (!form) {
  console.warn("Inquiry form not found.");
} else {
  /* ==========================================
     ELEMENTS
  ========================================== */

  const fullName = $("#fullname");
  const phoneNumber = $("#phone_number");

  const bikeBrand = $("#bike_brand");
  const bikeModel = $("#bike_model");
  const bikeYear = $("#bike_year");
  const plateNumber = $("#plate_number");

  const bodyCondition = $("#body_condition");

  const estimatedBudget = $("#estimated_budget");
  const targetResult = $("#target_result");

  const projectDetails = $("#project_details");
  const referenceLink = $("#reference_link");
  const projectPhotos = $("#project_photos");

  const pages = $$(".wizard-page");
  const steps = $$(".step");

  const nextBtn = $("#nextBtn");
  const prevBtn = $("#prevBtn");
  const submitBtn = $("#submitBtn");

  const progressLine = $(".progress-line");

  let currentStep = 0;

  /* ==========================================
     HELPERS
  ========================================== */

  function createError(message) {
    const error = document.createElement("small");

    error.className = "error-message";
    error.textContent = message;

    return error;
  }

  function clearErrors() {
    $$(".error-message").forEach((el) => el.remove());

    $$("input, textarea, select", form).forEach((field) => {
      field.style.borderColor = "";
    });
  }

  function showError(field, message) {
    if (!field) return;

    field.style.borderColor = "#ff4d4f";

    const existing = field.parentElement?.querySelector(".error-message");

    if (existing) {
      existing.remove();
    }

    field.parentElement?.appendChild(createError(message));
  }

  function isValidPhone(phone) {
    return /^(\+62|62|08)\d{8,13}$/.test(phone);
  }

  function isValidUrl(url) {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  function getSelectedServices() {
    return $$(".service-card input[type='checkbox']:checked").map(
      (checkbox) => checkbox.value,
    );
  }

  function updateProgressLine() {
    if (!progressLine) return;

    const total = steps.length - 1;

    const percentage = total <= 0 ? 0 : (currentStep / total) * 100;

    progressLine.style.background =
      "linear-gradient(90deg, var(--primary) " +
      percentage +
      "%, rgba(255,255,255,.08) " +
      percentage +
      "%)";
  }

  /* ==========================================
     WIZARD
  ========================================== */

  function updateWizard() {
    pages.forEach((page, index) => {
      page.classList.toggle("active", index === currentStep);
    });

    steps.forEach((step, index) => {
      step.classList.toggle("active", index <= currentStep);
    });

    prevBtn.style.display = currentStep === 0 ? "none" : "inline-flex";

    nextBtn.style.display =
      currentStep === pages.length - 1 ? "none" : "inline-flex";

    submitBtn.style.display =
      currentStep === pages.length - 1 ? "inline-flex" : "none";

    updateProgressLine();
  }

  /* ==========================================
     VALIDATION
  ========================================== */

  function validateStepOne() {
    let valid = true;

    const fullname = fullName?.value.trim() || "";

    const phone = phoneNumber?.value.trim() || "";

    if (fullname.length < 3) {
      showError(fullName, "Full name must be at least 3 characters.");
      valid = false;
    }

    if (!isValidPhone(phone)) {
      showError(phoneNumber, "Please enter a valid WhatsApp number.");
      valid = false;
    }

    return valid;
  }

  function validateStepTwo() {
    let valid = true;

    if (!bikeBrand?.value) {
      showError(bikeBrand, "Please select a motorcycle brand.");

      valid = false;
    }

    if (!bikeModel?.value.trim() || bikeModel.value.trim().length < 2) {
      showError(bikeModel, "Motorcycle model is required.");

      valid = false;
    }

    if (
      bikeYear?.value &&
      (Number(bikeYear.value) < 1950 ||
        Number(bikeYear.value) > new Date().getFullYear() + 1)
    ) {
      showError(bikeYear, "Please enter a valid production year.");

      valid = false;
    }

    return valid;
  }

  function validateStepThree() {
    let valid = true;

    const services = getSelectedServices();

    if (!services.length) {
      alert("Please select at least one service.");

      valid = false;
    }

    if (
      !projectDetails?.value.trim() ||
      projectDetails.value.trim().length < 20
    ) {
      showError(
        projectDetails,
        "Project description must be at least 20 characters.",
      );

      valid = false;
    }

    const ref = referenceLink?.value.trim() || "";

    if (ref && !isValidUrl(ref)) {
      showError(referenceLink, "Please enter a valid URL.");

      valid = false;
    }

    if (projectPhotos?.files && projectPhotos.files.length > 10) {
      showError(projectPhotos, "Maximum 10 photos allowed.");

      valid = false;
    }

    return valid;
  }

  function validateStep(step) {
    clearErrors();

    switch (step) {
      case 0:
        return validateStepOne();

      case 1:
        return validateStepTwo();

      case 2:
        return validateStepThree();

      default:
        return true;
    }
  }

  /* ==========================================
     STEP NAVIGATION
  ========================================== */

  nextBtn?.addEventListener("click", () => {
    if (!validateStep(currentStep)) {
      return;
    }

    currentStep++;

    updateWizard();
  });

  prevBtn?.addEventListener("click", () => {
    currentStep--;

    updateWizard();
  });

  /* ==========================================
     SERVICE CARDS
  ========================================== */

  $$(".service-card").forEach((card) => {
    const checkbox = $("input[type='checkbox']", card);

    if (!checkbox) return;

    function syncState() {
      card.classList.toggle("selected", checkbox.checked);
    }

    checkbox.addEventListener("change", syncState);

    syncState();
  });

  /* ==========================================
     PHOTO PREVIEW COUNT
  ========================================== */

  projectPhotos?.addEventListener("change", () => {
    const uploadZone = projectPhotos.closest(".upload-zone");

    if (!uploadZone) return;

    const paragraph = $("p", uploadZone);

    if (!paragraph) return;

    const count = projectPhotos.files.length;

    if (!count) {
      paragraph.textContent = "Drag & drop photos here or click to browse.";

      return;
    }

    paragraph.textContent = `${count} photo${count > 1 ? "s" : ""} selected`;
  });

  /* ==========================================
     AUTO FORMAT
  ========================================== */

  phoneNumber?.addEventListener("input", (e) => {
    e.target.value = e.target.value.replace(/[^0-9+]/g, "");
  });

  plateNumber?.addEventListener("input", (e) => {
    e.target.value = e.target.value.toUpperCase();
  });

  /* ==========================================
     SUBMIT
  ========================================== */

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!validateStepThree()) {
      return;
    }

    submitBtn.disabled = true;

    submitBtn.textContent = "Submitting...";

    try {
      const data = {
        customer_name: fullName?.value.trim(),

        customer_phone_number: phoneNumber?.value.trim(),

        customer_email: referenceLink?.value?.trim() || "user@example.com", // kalau tidak ada input, biarkan kosong atau tambahkan field

        vehicle_brand: bikeBrand?.value,

        vehicle_model: bikeModel?.value?.trim(),

        vehicle_license_plate: plateNumber?.value?.trim(),

        vehicle_condition: bodyCondition?.value || "",

        project_type: getSelectedServices()?.join(", "), // multi service jadi string

        project_description: projectDetails?.value?.trim(),

        project_target: targetResult?.value || "",

        reference_link: referenceLink?.value?.trim() || ""
      };
      // create inquiry
      const res = await createCustomerInquiry(data);
      const inquiryId = res?.data?.id;

      if (!inquiryId) {
        throw new Error("Invalid inquiry response (missing id)");
      }

      // upload photos ()
      const files = projectPhotos?.files;
      if (files && files.length > 0) {
        await uploadInquiryPhotos(inquiryId, files);
      }

      // console.log("NOCTRA Inquiry", data);

      alert("Project inquiry submitted successfully.");

      form.reset();

      $$(".service-card").forEach((card) => {
        card.classList.remove("selected");
      });

      currentStep = 0;
      clearErrors();
      updateWizard();

      const uploadZone = projectPhotos?.closest(".upload-zone");

      if (uploadZone) {
        const p = $("p", uploadZone);

        if (p) {
          p.textContent = "Drag & drop photos here or click to browse.";
        }
      }
    } catch (error) {
      console.error(error);

      alert("Something went wrong. Please try again.");
    } finally {
      submitBtn.disabled = false;

      submitBtn.textContent = "Start My Project";
    }
  });

  /* ==========================================
     INIT
  ========================================== */

  updateWizard();
}

const motorcycleData = {
  Honda: [
    "Astrea Grand",
    "Supra",
    "Supra X",
    "Revo",
    "Blade",
    "Beat",
    "Scoopy",
    "Genio",
    "Vario 125",
    "Vario 160",
    "PCX 160",
    "ADV 160",
    "CB150R",
    "Verza",
    "Mega Pro",
    "Tiger",
    "CBR150R",
    "CBR250RR",
    "CRF150L",
  ],
  Yamaha: [
    "Mio",
    "Mio Sporty",
    "Mio Soul",
    "Fino",
    "Xeon",
    "Lexi",
    "Aerox",
    "NMAX",
    "XMAX",
    "Jupiter Z",
    "Jupiter MX",
    "Vega",
    "Vixion",
    "Byson",
    "R15",
    "R25",
    "MT-15",
    "XSR 155",
  ],
  Suzuki: [
    "Crystal",
    "Shogun",
    "Smash",
    "Satria",
    "Satria F150",
    "Nex",
    "Address",
    "Burgman Street",
    "GSX-R150",
    "GSX-S150",
  ],
  Kawasaki: [
    "Kaze",
    "Athlete",
    "Ninja 150RR",
    "Ninja 250R",
    "Ninja ZX-25R",
    "KLX 150",
    "D-Tracker",
    "W175",
    "Versys X250",
  ],
};

const brandSelect = document.getElementById("bike_brand");
const modelSelect = document.getElementById("bike_model");

brandSelect.addEventListener("change", () => {
  const brand = brandSelect.value;

  modelSelect.innerHTML = '<option value="">Pilih Model</option>';

  if (!motorcycleData[brand]) return;

  motorcycleData[brand].forEach((model) => {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    modelSelect.appendChild(option);
  });
});

const API_BASE = "http://localhost/api/customer/inquiry/";

// 1. CREATE CUSTOMER INQUIRY (JSON BODY)
async function createCustomerInquiry(payload) {
  try {
    const res = await fetch(`${API_BASE}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data?.message || "Failed to create inquiry");
    }

    return data;
  } catch (err) {
    console.error("createCustomerInquiry error:", err);
    throw err;
  }
}


async function uploadInquiryPhotos(inquiryId, files) {
  try {
    const formData = new FormData();

    Array.from(files).forEach((file) => {
      formData.append("photos", file);
    });

    const res = await fetch(
      `${API_BASE}${inquiryId}/photos`,
      {
        method: "POST",
        body: formData,
      }
    );

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data?.message || "Failed to upload photos");
    }

    return data;
  } catch (err) {
    console.error("uploadInquiryPhotos error:", err);
    throw err;
  }
}
