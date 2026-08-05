// projects/handlers/keypad.js (GABUNGAN + FACTORY)
let keypadInstances = {};

export function initKeypad(
  inputId,
  keypadId,
  initialValue = "0",
  maxDecimals = 2,
) {
  const input = document.getElementById(inputId);
  const keypad = document.getElementById(keypadId);

  if (!input || !keypad) {
    console.warn(`Keypad elements not found: ${inputId} / ${keypadId}`);
    return;
  }

  // Cegah init ganda per instance
  const instanceKey = `${inputId}_${keypadId}`;
  if (keypadInstances[instanceKey]) return;
  keypadInstances[instanceKey] = true;

  let currentValue = input.value || initialValue;
  let isOpen = false;
  let valueBeforeOpen = currentValue;

  function updateInput(value) {
    currentValue = value;
    input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function openKeypad() {
    if (isOpen) return;
    valueBeforeOpen = input.value || initialValue;
    keypad.classList.add("active");
    input.classList.add("active");
    currentValue = input.value || initialValue;
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

  function processInput(value) {
    switch (value) {
      case "backspace":
        return currentValue.length > 1
          ? currentValue.slice(0, -1)
          : initialValue === "0"
            ? "0"
            : "1";
      case "clear":
        return initialValue === "0" ? "0" : "1";
      case ".":
        return currentValue.includes(".") ? currentValue : currentValue + ".";
      default:
        if (!/^\d$/.test(value)) return currentValue;
        if (currentValue === initialValue && value !== ".") return value;
        const [whole, decimal = ""] = currentValue.split(".");
        if (!currentValue.includes(".") && whole.length >= 8)
          return currentValue;
        if (currentValue.includes(".") && decimal.length >= maxDecimals)
          return currentValue;
        return currentValue + value;
    }
  }

  // Event: Klik input
  input.addEventListener("click", (e) => {
    e.stopPropagation();
    if (isOpen) closeKeypad();
    else openKeypad();
  });

  // Event: Klik tombol keypad
  keypad.addEventListener("click", (e) => {
    e.stopPropagation();
    const btn = e.target.closest(".keypad-btn");
    if (!btn) return;
    const value = btn.dataset.value;
    if (value === "enter") {
      closeKeypad(true);
      return;
    }
    const result = processInput(value);
    if (result !== null) updateInput(result);
  });

  // Tutup jika klik di luar
  document.addEventListener("click", (e) => {
    const wrapper = input.closest(".input-wrapper"); // Sesuaikan class wrapper
    if (isOpen && wrapper && !wrapper.contains(e.target)) {
      closeKeypad();
    }
  });

  // Keyboard support
  input.addEventListener("keydown", (e) => {
    e.preventDefault();
    const key = e.key;
    if ((key >= "0" && key <= "9") || key === ".") {
      const result = processInput(key);
      if (result !== null) updateInput(result);
      return;
    }
    if (key === "Backspace") {
      const result = processInput("backspace");
      if (result !== null) updateInput(result);
      return;
    }
    if (key === "Delete") {
      updateInput(initialValue === "0" ? "0" : "1");
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

  console.log(`✅ Keypad initialized: ${inputId}`);
}
