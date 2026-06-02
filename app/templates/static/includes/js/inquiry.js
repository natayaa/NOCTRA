const form = document.querySelector(".inquiry-form");

const pages = form.querySelectorAll(".wizard-page");

/* ======================
   SCROLL LOCK MANAGER
====================== */
const ScrollLock = {
    lock() {
        document.body.style.overflow = "hidden";
    },
    unlock() {
        document.body.style.overflow = "";
    }
};

/* ======================
   ELEMENT SAFE BINDING
====================== */
const $ = (sel) => document.querySelector(sel);

const platePrefix = $(".plate-prefix");
const plateNumber = $(".plate-number");
const plateSuffix = $(".plate-suffix");

const fullName = $("#fullname");
const phone = $("#phone_number");
const bikeBrand = $("#bike_brand");
const bikeModel = $("#bike_model");
const serviceType = $("#service_type");
const bodyCondition = $("#body_condition");
const details = $("#project_details");
const reference = $("#reference_link");
const photos = $("#project_photos");

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
   VALIDATION ENGINE
====================== */
function showError(input, message) {
    if (!input) return;

    input.style.borderColor = "#ff4d4f";

    const old = input.parentElement.querySelector(".error-message");
    if (old) old.remove();

    const err = document.createElement("small");
    err.className = "error-message";
    err.textContent = message;

    input.parentElement.appendChild(err);
}

function clearErrors() {
    document.querySelectorAll(".error-message").forEach(e => e.remove());

    document.querySelectorAll("input, textarea, select").forEach(el => {
        el.style.borderColor = "";
    });
}

/* ======================
   FORM SUBMIT
====================== */
if (form) {
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        clearErrors();

        let ok = true;

        if (!fullName || fullName.value.trim().length < 3) {
            showError(fullName, "Nama minimal 3 karakter.");
            ok = false;
        }

        const phoneRegex = /^(\+62|62|08)[0-9]{8,13}$/;
        if (!phone || !phoneRegex.test(phone.value.trim())) {
            showError(phone, "Nomor HP tidak valid.");
            ok = false;
        }

        if (!bikeModel || bikeModel.value.trim().length < 2) {
            showError(bikeModel, "Model motor wajib diisi.");
            ok = false;
        }

        if (!platePrefix || !/^[A-Z]{1,2}$/.test(platePrefix.value.trim())) {
            showError(platePrefix, "Contoh: D");
            ok = false;
        }

        if (!plateNumber || !/^\d{1,4}$/.test(plateNumber.value.trim())) {
            showError(plateNumber, "Contoh: 6637");
            ok = false;
        }

        if (!plateSuffix || !/^[A-Z]{1,3}$/.test(plateSuffix.value.trim())) {
            showError(plateSuffix, "Contoh: KK");
            ok = false;
        }

        if (!details || details.value.trim().length < 20) {
            showError(details, "Deskripsi minimal 20 karakter.");
            ok = false;
        }

        if (reference && reference.value.trim() !== "") {
            try {
                new URL(reference.value.trim());
            } catch {
                showError(reference, "URL tidak valid.");
                ok = false;
            }
        }

        if (photos && photos.files.length > 5) {
            showError(photos, "Maksimal 5 foto.");
            ok = false;
        }

        if (!ok) return;

        const data = {
            fullname: fullName.value.trim(),
            phone: phone.value.trim(),
            plate: `${platePrefix.value}-${plateNumber.value}-${plateSuffix.value}`,
            brand: bikeBrand?.value,
            model: bikeModel.value.trim(),
            service: serviceType?.value,
            condition: bodyCondition?.value,
            details: details.value.trim(),
            reference: reference?.value.trim()
        };

        console.log("Inquiry Data:", data);

        alert("Inquiry berhasil dikirim.");

        form.reset();
        clearErrors();
        currentStep = 0;
        updateWizard();
    });
}

/* ======================
   WIZARD STATE MACHINE
====================== */
let currentStep = 0;

const pages = document.querySelectorAll(".wizard-page");
const steps = document.querySelectorAll(".step");

const nextBtn = $("#nextBtn");
const prevBtn = $("#prevBtn");
const submitBtn = $("#submitBtn");

function updateWizard() {
    pages.forEach(p => p.classList.remove("active"));
    steps.forEach(s => s.classList.remove("active"));

    if (pages[currentStep]) {
        pages[currentStep].classList.add("active");
    }

    steps.forEach((s, i) => {
        if (i <= currentStep) s.classList.add("active");
    });

    if (prevBtn) prevBtn.style.display = currentStep === 0 ? "none" : "block";
    if (nextBtn) nextBtn.style.display = currentStep === pages.length - 1 ? "none" : "block";
    if (submitBtn) submitBtn.style.display = currentStep === pages.length - 1 ? "block" : "none";
}

nextBtn?.addEventListener("click", () => {
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