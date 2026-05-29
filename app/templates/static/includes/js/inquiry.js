const form = document.querySelector(".inquiry-form");

form.addEventListener("submit", (e) => {

    e.preventDefault();

    // INPUTS

    const fullName = form.querySelector(
        'input[placeholder="Your full name"]'
    );

    const phone = form.querySelector(
        'input[placeholder="+62 xxx"]'
    );

    const motorbike = form.querySelector(
        'input[placeholder="Mio Sporty"]'
    );

    const budget = form.querySelector(
        'input[placeholder="Rp 5.000.000"]'
    );

    const details = form.querySelector("textarea");

    const reference = form.querySelector(
        'input[placeholder="https://..."]'
    );


    // RESET

    clearErrors();


    let isValid = true;


    // FULL NAME

    if (fullName.value.trim().length < 3) {

        showError(
            fullName,
            "Full name minimum 3 characters."
        );

        isValid = false;
    }


    // PHONE

    const phoneRegex = /^(\+62|62|08)[0-9]{8,13}$/;

    if (!phoneRegex.test(phone.value.trim())) {

        showError(
            phone,
            "Invalid Indonesian phone number."
        );

        isValid = false;
    }


    // MOTORBIKE

    if (motorbike.value.trim().length < 2) {

        showError(
            motorbike,
            "Motorbike field is required."
        );

        isValid = false;
    }


    // BUDGET

    if (budget.value.trim() === "") {

        showError(
            budget,
            "Estimated budget is required."
        );

        isValid = false;
    }


    // DETAILS

    if (details.value.trim().length < 20) {

        showError(
            details,
            "Project details minimum 20 characters."
        );

        isValid = false;
    }


    // URL VALIDATION

    if (reference.value.trim() !== "") {

        try {

            new URL(reference.value);

        } catch {

            showError(
                reference,
                "Invalid URL format."
            );

            isValid = false;
        }

    }


    // SUCCESS

    if (isValid) {

        alert("Inquiry submitted successfully.");

        form.reset();
    }

});


// SHOW ERROR

function showError(input, message) {

    input.style.borderColor = "#ff4d79";

    const error = document.createElement("small");

    error.classList.add("error-message");

    error.innerText = message;

    input.parentElement.appendChild(error);

}


// CLEAR ERRORS

function clearErrors() {

    const errors = document.querySelectorAll(
        ".error-message"
    );

    errors.forEach(error => error.remove());

    const fields = document.querySelectorAll(
        "input, textarea, select"
    );

    fields.forEach(field => {
        field.style.borderColor = "rgba(255,255,255,.06)";
    });

}