// static/js/pages/settings/handlers/users.js

import { DOM } from "../dom.js";
import { state } from "../config.js";
import { UserAPI } from "../api.js";
import { showToast } from "../../../pages/shared/toast.js";
import { renderUsers } from "../renderers/users.js";

// ============================================================
// LOAD USERS
// ============================================================

export async function loadUsers() {
  const users = await UserAPI.getUsers();
  state.users = users;
  renderUsers(users);
}

// ============================================================
// OPEN USER MODAL
// ============================================================

export function openUserModal(user = null) {
  const modal = DOM.userModal();
  const form = DOM.userForm();
  const usernameInput = DOM.userUsername();
  const emailInput = DOM.userEmail();
  const nameInput = DOM.userFullName();
  const passwordInput = DOM.userPassword();
  const roleSelect = DOM.userRole();

  if (!modal) return;

  if (user) {
    // Edit mode
    if (usernameInput) usernameInput.value = user.username || "";
    if (emailInput) emailInput.value = user.email || "";
    if (nameInput) nameInput.value = user.full_name || "";
    if (passwordInput) {
      passwordInput.placeholder = "Leave blank to keep current";
      passwordInput.required = false;
    }
    if (roleSelect) roleSelect.value = user.role || "user";
  } else {
    // Create mode
    if (usernameInput) usernameInput.value = "";
    if (emailInput) emailInput.value = "";
    if (nameInput) nameInput.value = "";
    if (passwordInput) {
      passwordInput.placeholder = "Min 8 characters";
      passwordInput.required = true;
    }
    if (roleSelect) roleSelect.value = "user";
  }

  modal.classList.add("active");
  setTimeout(() => usernameInput?.focus(), 100);
}

// ============================================================
// CLOSE USER MODAL
// ============================================================

export function closeUserModal() {
  const modal = DOM.userModal();
  if (modal) {
    modal.classList.remove("active");
  }
  const form = DOM.userForm();
  if (form) form.reset();
}

// ============================================================
// SAVE USER
// ============================================================

export async function saveUser(e) {
  e.preventDefault();

  const usernameInput = DOM.userUsername();
  const emailInput = DOM.userEmail();
  const nameInput = DOM.userFullName();
  const passwordInput = DOM.userPassword();
  const roleSelect = DOM.userRole();

  const username = usernameInput?.value?.trim();
  const email = emailInput?.value?.trim();
  const fullName = nameInput?.value?.trim();
  const password = passwordInput?.value;
  const role = roleSelect?.value || "user";

  if (!username) {
    showToast("Please enter a username", "warning");
    usernameInput?.focus();
    return;
  }

  if (!email) {
    showToast("Please enter an email", "warning");
    emailInput?.focus();
    return;
  }

  if (!fullName) {
    showToast("Please enter full name", "warning");
    nameInput?.focus();
    return;
  }

  // Check if creating new user (password required)
  const isNew = !document
    .querySelector("#userModal .modal-header h2")
    ?.textContent?.includes("Edit");
  if (isNew && (!password || password.length < 8)) {
    showToast("Password must be at least 8 characters", "warning");
    passwordInput?.focus();
    return;
  }

  const data = {
    username,
    email,
    full_name: fullName,
    role,
  };

  if (password) {
    data.password = password;
  }

  // We don't have user ID tracking in this implementation
  // Assume create for now
  const result = await UserAPI.createUser(data);

  if (result) {
    closeUserModal();
    await loadUsers();
  }
}

// ============================================================
// DELETE USER
// ============================================================

export async function deleteUser(id) {
  const success = await UserAPI.deleteUser(id);
  if (success) {
    await loadUsers();
  }
}
