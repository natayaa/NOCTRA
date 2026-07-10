// inquiries/renderers/notes.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";

export function renderDrawerNotes(notes) {
  const container = DOM.drawerNotes();
  const counter = DOM.noteCounter();

  if (!container) return;

  if (!notes || notes.length === 0) {
    container.value = "";
    container.placeholder = "No notes yet. Add a note...";
    if (counter) counter.textContent = "0";
    return;
  }

  // ✅ Show latest note or concatenate all
  const latestNote = notes[notes.length - 1];
  const noteText = latestNote?.note || "";
  container.value = noteText;
  container.placeholder = "Add internal notes...";

  if (counter) {
    counter.textContent = noteText.length;
    counter.style.color =
      noteText.length > 400 ? "var(--danger, #ef4444)" : "var(--text-muted)";
  }

  // ✅ Show note count if multiple
  const countEl = document.getElementById("drawerNoteCount");
  if (countEl) {
    countEl.textContent = `(${notes.length} note${notes.length > 1 ? "s" : ""})`;
  }
}

export function updateNoteCounter() {
  const container = DOM.drawerNotes();
  const counter = DOM.noteCounter();
  if (!container || !counter) return;

  const length = container.value.length;
  counter.textContent = length;
  counter.style.color =
    length > 400 ? "var(--danger, #ef4444)" : "var(--text-muted)";
}
