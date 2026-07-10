// projects/handlers/materialKeypad.js (FIXED & IMPROVED)

let materialKeypadInitialized = false;
let materialKeypadValue = "1";
let materialIsOpen = false;
let materialValueBeforeOpen = "1";

export function initMaterialQtyKeypad() {
  const input = document.getElementById("materialQty");
  const keypad = document.getElementById("materialQtyKeypad");

  if (!input || !keypad) {
    console.warn("Material quantity keypad elements not found");
    return;
  }

  if (materialKeypadInitialized) {
    console.log("Material quantity keypad already initialized");
    return;
  }

  materialKeypadInitialized = true;
  materialKeypadValue = input.value || "1";
  input.value = materialKeypadValue;

  function updateInput(value) {
    materialKeypadValue = value;
    input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function openKeypad() {
    if (materialIsOpen) return;
    materialValueBeforeOpen = input.value || "1";
    keypad.classList.add("active");
    input.classList.add("active");
    materialKeypadValue = input.value || "1";
    materialIsOpen = true;
  }

  function closeKeypad(triggerChange = false) {
    if (!materialIsOpen) return;
    keypad.classList.remove("active");
    input.classList.remove("active");
    materialIsOpen = false;
    if (triggerChange) {
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  // Input click
  input.addEventListener("click", (e) => {
    e.stopPropagation();
    if (materialIsOpen) {
      closeKeypad();
    } else {
      openKeypad();
    }
  });

  // Keypad buttons
  keypad.addEventListener("click", (e) => {
    const btn = e.target.closest(".keypad-btn");
    if (!btn) return;
    e.stopPropagation();
    const value = btn.dataset.value;
    if (!value) return;

    if (value === "enter") {
      closeKeypad(true);
      return;
    }

    const result = processMaterialKeypadInput(value, materialKeypadValue);
    if (result !== null) {
      updateInput(result);
    }
  });

  // Outside click
  document.addEventListener("click", (e) => {
    const wrapper = input.closest(".material-qty-wrapper");
    const isClickOnKeypad = keypad.contains(e.target);
    const isClickOnInput = input === e.target || input.contains(e.target);

    if (isClickOnKeypad || isClickOnInput) return;

    if (materialIsOpen && wrapper && !wrapper.contains(e.target)) {
      setTimeout(() => {
        if (materialIsOpen) closeKeypad();
      }, 50);
    }
  });

  // Keyboard support
  input.addEventListener("keydown", (e) => {
    e.preventDefault();
    const key = e.key;

    if ((key >= "0" && key <= "9") || key === ".") {
      const result = processMaterialKeypadInput(key, materialKeypadValue);
      if (result !== null) updateInput(result);
      return;
    }

    if (key === "Backspace") {
      const result = processMaterialKeypadInput(
        "backspace",
        materialKeypadValue,
      );
      if (result !== null) updateInput(result);
      return;
    }

    if (key === "Delete") {
      updateInput("1");
      return;
    }

    if (key === "Enter") {
      closeKeypad(true);
      return;
    }

    if (key === "Escape") {
      closeKeypad(false);
    }
  });

  console.log("✅ Material quantity keypad initialized");
}

function processMaterialKeypadInput(value, currentValue = "1") {
  switch (value) {
    case "backspace":
      return currentValue.length > 1 ? currentValue.slice(0, -1) : "1";
    case "clear":
      return "1";
    case ".":
      return currentValue.includes(".") ? currentValue : currentValue + ".";
    default:
      if (!/^\d$/.test(value)) return currentValue;
      if (currentValue === "1" && value !== ".") return value;
      const [whole, decimal = ""] = currentValue.split(".");
      if (!currentValue.includes(".") && whole.length >= 8) return currentValue;
      if (currentValue.includes(".") && decimal.length >= 2)
        return currentValue;
      return currentValue + value;
  }
}

window.debugMaterialKeypad = () => {
  console.log({
    materialKeypadValue,
    materialIsOpen,
    materialInitialized: materialKeypadInitialized,
    materialValueBeforeOpen: materialValueBeforeOpen,
    inputValue: document.getElementById("materialQty")?.value,
  });
};
