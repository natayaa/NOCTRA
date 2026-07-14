// static/js/pages/settings/renderers/users.js

import { escapeHtml } from "../../../pages/shared/utils.js";

export function renderUsers(users) {
  const container = document.getElementById("userList");
  if (!container) return;

  if (!users || users.length === 0) {
    container.innerHTML = `
            <div class="empty-state-sm">
                <p>No users yet. Add your first team member.</p>
            </div>
        `;
    return;
  }

  const roleColors = {
    admin: "admin",
    manager: "manager",
    supervisor: "supervisor",
    technician: "technician",
    user: "user",
  };

  container.innerHTML = users
    .map(
      (user) => `
        <div class="user-item" data-user-id="${user.id}">
            <div class="user-info">
                <strong>${escapeHtml(user.full_name || user.username)}</strong>
                <small>${escapeHtml(user.email)}</small>
            </div>
            <span class="user-role-badge ${roleColors[user.role] || "user"}">
                ${escapeHtml(user.role || "User")}
            </span>
            <div class="user-actions">
                <button class="btn-edit" data-id="${user.id}" title="Edit user">
                    <i class="ph ph-pencil"></i>
                </button>
                <button class="btn-delete" data-id="${user.id}" title="Delete user">
                    <i class="ph ph-trash"></i>
                </button>
            </div>
        </div>
    `,
    )
    .join("");

  container.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const user = users.find((u) => u.id === id);
      if (user) window.openUserModal(user);
    });
  });

  container.querySelectorAll(".btn-delete").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const user = users.find((u) => u.id === id);
      if (
        user &&
        confirm(`Delete user "${user.full_name || user.username}"?`)
      ) {
        window.deleteUser(id);
      }
    });
  });
}
