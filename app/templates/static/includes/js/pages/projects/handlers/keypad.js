// projects/handlers/keypad.js (FIXED & IMPROVED)

let keypadInitialized = false;
let keypadValue = "0";
let isOpen = false;

export function initHoursKeypad() {
  const input = document.getElementById("laborHours");
  const keypad = document.getElementById("hoursKeypad");

  if (!input || !keypad) {
    console.warn("Hours keypad elements not found");
    return;
  }

  if (keypadInitialized) {
    console.log("Hours keypad already initialized");
    return;
  }

  keypadInitialized = true;
  keypadValue = input.value || "0";
  input.value = keypadValue;

  function updateInput(value) {
    keypadValue = value;
    input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function openKeypad() {
    if (isOpen) return;
    keypad.classList.add("active");
    input.classList.add("active");
    keypadValue = input.value || "0";
    isOpen = true;
  }

  function closeKeypad(triggerChange = false) {
    if (!isOpen) return;
    keypad.classList.remove("active");
    input.classList.remove("active");
    isOpen = false;
    if (triggerChange) {
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  // Input click
  input.addEventListener("click", (e) => {
    e.stopPropagation();
    if (isOpen) {
      closeKeypad();
    } else {
      openKeypad();
    }
  });

  // Keypad buttons
  keypad.addEventListener("click", (e) => {
    e.stopPropagation();
    const btn = e.target.closest(".keypad-btn");
    if (!btn) return;
    const value = btn.dataset.value;
    if (!value) return;

    if (value === "enter") {
      closeKeypad(true);
      return;
    }

    const result = processKeypadInput(value, keypadValue);
    if (result !== null) {
      updateInput(result);
    }
  });

  // Outside click
  document.addEventListener("click", (e) => {
    const wrapper = input.closest(".hours-input-wrapper");
    if (isOpen && wrapper && !wrapper.contains(e.target)) {
      closeKeypad();
    }
  });

  // Keyboard support
  input.addEventListener("keydown", (e) => {
    e.preventDefault();
    const key = e.key;

    if ((key >= "0" && key <= "9") || key === ".") {
      updateInput(processKeypadInput(key, keypadValue));
      return;
    }

    if (key === "Backspace") {
      updateInput(processKeypadInput("backspace", keypadValue));
      return;
    }

    if (key === "Delete") {
      updateInput("0");
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

  console.log("✅ Hours keypad initialized");
}

function processKeypadInput(value, currentValue = "0") {
  switch (value) {
    case "backspace":
      return currentValue.length > 1 ? currentValue.slice(0, -1) : "0";
    case "clear":
      return "0";
    case ".":
      return currentValue.includes(".") ? currentValue : currentValue + ".";
    default:
      if (!/^\d$/.test(value)) return currentValue;
      if (currentValue === "0") return value;
      const [whole, decimal = ""] = currentValue.split(".");
      if (!currentValue.includes(".") && whole.length >= 8) return currentValue;
      if (currentValue.includes(".") && decimal.length >= 2)
        return currentValue;
      return currentValue + value;
  }
}

window.debugKeypad = () => {
  console.log({
    keypadValue,
    isOpen,
    initialized: keypadInitialized,
    inputValue: document.getElementById("laborHours")?.value,
  });
};
