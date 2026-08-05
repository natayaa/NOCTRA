// ============================================================
// restored-bikes/renderers/documents.js - Documents Rendering
// ============================================================

import { DOM } from "../dom.js";

const ICON_MAP = {
  pdf: "fa-file-pdf",
  jpg: "fa-file-image",
  jpeg: "fa-file-image",
  png: "fa-file-image",
  doc: "fa-file-word",
  docx: "fa-file-word",
  xls: "fa-file-excel",
  xlsx: "fa-file-excel",
  txt: "fa-file-alt",
  default: "fa-file",
};

function getFileIcon(filename) {
  if (!filename) return ICON_MAP.default;
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  return ICON_MAP[ext] || ICON_MAP.default;
}

function formatFileSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

export function renderDocuments(documents) {
  const list = DOM.documentList();
  if (!list) return;

  if (!documents || documents.length === 0) {
    list.innerHTML = `<div class="empty-state">No documents uploaded</div>`;
    return;
  }

  list.innerHTML = documents
    .map((doc) => {
      const icon = getFileIcon(doc.filename);
      const size = formatFileSize(doc.file_size);
      return `
        <div class="document-item" data-id="${doc.id}">
          <div class="doc-info">
            <i class="fas ${icon}"></i>
            <div>
              <div class="doc-name">${doc.filename || "Unknown"}</div>
              ${size ? `<div class="doc-size">${size}</div>` : ""}
            </div>
          </div>
          <div class="doc-actions">
            <button onclick="window.downloadDocument('${doc.id}')" title="Download">
              <i class="fas fa-download"></i>
            </button>
            <button class="delete-doc" onclick="window.deleteDocument('${doc.id}')" title="Delete">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      `;
    })
    .join("");
}
