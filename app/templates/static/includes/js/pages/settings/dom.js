// static/js/pages/settings/dom.js

export const $ = (id) => {
  const el = document.getElementById(id);
  if (!el) console.warn(`⚠️ Element "${id}" not found`);
  return el;
};

export const $$ = (selector) => document.querySelectorAll(selector);

export const DOM = {
  // ==================== Toolbar ====================
  saveStatus: () => $("saveStatus"),
  saveBtn: () => $("saveSettings"),
  resetBtn: () => $("resetSettings"),

  // ==================== Navigation ====================
  navItems: () => $$(".settings-nav .nav-item"),
  sections: () => $$(".settings-section"),

  // ==================== Workshop ====================
  workshopName: () => $("workshop_name"),
  workshopAddress: () => $("workshop_address"),
  workshopPhone: () => $("workshop_phone"),
  workshopEmail: () => $("workshop_email"),
  workshopWebsite: () => $("workshop_website"),

  // ==================== Pricing ====================
  paintBasePrice: () => $("paint_base_price"),
  restorationBasePrice: () => $("restoration_base_price"),
  detailingBasePrice: () => $("detailing_base_price"),
  customColorPrice: () => $("custom_color_price"),
  laborPainter: () => $("labor_painter"),
  laborBody: () => $("labor_body"),
  laborAssembly: () => $("labor_assembly"),
  laborSupervisor: () => $("labor_supervisor"),
  taxPercent: () => $("tax_percent"),
  defaultMargin: () => $("default_margin"),
  defaultDuration: () => $("default_duration"),
  currency: () => $("currency"),

  // ==================== Security ====================
  requireMFA: () => $("require_mfa"),
  rememberMe: () => $("remember_me"),
  forcePasswordChange: () => $("force_password_change"),
  sessionTimeout: () => $("session_timeout"),
  maxLoginAttempts: () => $("max_login_attempts"),

  // ==================== System Preferences ====================
  emailNotifications: () => $("email_notifications"),
  whatsappNotifications: () => $("whatsapp_notifications"),
  autoInvoice: () => $("auto_invoice"),

  // ==================== WhatsApp Templates ====================
  templateList: () => $("templateList"),
  templateModal: () => $("templateModal"),
  templateForm: () => $("templateForm"),
  templateId: () => $("templateId"),
  templateName: () => $("templateName"),
  templateDescription: () => $("templateDescription"),
  templateContent: () => $("templateContent"),
  templateIsDefault: () => $("templateIsDefault"),
  templateModalTitle: () => $("templateModalTitle"),
  closeTemplateModal: () => $("closeTemplateModal"),
  cancelTemplateBtn: () => $("cancelTemplateBtn"),
  addTemplateBtn: () => $("addTemplateBtn"),

  // ==================== Project Types ====================
  projectTypeList: () => $("projectTypeList"),

  // ==================== Payment Methods ====================
  paymentMethodList: () => $("paymentMethodList"),

  // ==================== Users ====================
  userList: () => $("userList"),
  userModal: () => $("userModal"),
  userForm: () => $("userForm"),
  userUsername: () => $("userUsername"),
  userEmail: () => $("userEmail"),
  userFullName: () => $("userFullName"),
  userPassword: () => $("userPassword"),
  userRole: () => $("userRole"),
  closeUserModal: () => $("closeUserModal"),
  cancelUserBtn: () => $("cancelUserBtn"),
  addUserBtn: () => $("addUserBtn"),

  // ==================== Toast ====================
  toastContainer: () => $("toastContainer"),
};
