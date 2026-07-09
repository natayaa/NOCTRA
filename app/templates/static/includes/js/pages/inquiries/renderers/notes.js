// ============================================================
// inquiries/renderers/notes.js - Notes Rendering
// ============================================================

import { DOM } from "../dom.js";

export function renderDrawerNotes(notes) {
  const container = DOM.drawerNotes();
  const counter = DOM.noteCounter();

  if (!container) return;

  if (!notes || notes.length === 0) {
    container.value = "";
    if (counter) counter.textContent = "0";
    return;
  }

  const latestNote = notes[notes.length - 1];
  container.value = latestNote?.note || "";
  if (counter) counter.textContent = container.value.length;
}
