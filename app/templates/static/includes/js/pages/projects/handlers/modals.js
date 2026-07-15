// projects/handlers/modals.js (FIXED & IMPROVED)

import { DOM } from "../dom.js";
import { ProjectAPI } from "../api.js";
import { showToast } from "../toast.js";
import { loadProjects } from "../index.js";

export function closeProjectModal() {
  const modal = DOM.projectModal();
  if (modal) modal.classList.remove("active");
  document.body.style.overflow = "";
}

export function openCreateProjectModal() {
  const title = DOM.modalTitle();
  const subtitle = DOM.modalSubtitle();
  const editId = DOM.editProjectId();
  const form = DOM.projectForm();
  const submit = DOM.submitProjectBtn();
  const modal = DOM.projectModal();

  if (title) title.textContent = "Create New Project";
  if (subtitle)
    subtitle.textContent = "Register workshop project and production schedule";
  if (editId) editId.value = "";
  if (form) form.reset();
  if (submit) submit.textContent = "Create Project";
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
    // Focus on first input
    setTimeout(() => DOM.projectName()?.focus(), 100);
  }
}

export async function openEditProjectModal(projectId) {
  const projectData = await ProjectAPI.fetchDetail(projectId);
  const project = projectData?.project || projectData;
  if (!project) {
    showToast("Failed to load project data", "error");
    return;
  }

  const title = DOM.modalTitle();
  const subtitle = DOM.modalSubtitle();
  const editId = DOM.editProjectId();
  const submit = DOM.submitProjectBtn();
  const modal = DOM.projectModal();

  if (title) title.textContent = "Edit Project";
  if (subtitle) subtitle.textContent = `Editing: ${project.name}`;
  if (editId) editId.value = projectId;
  if (submit) submit.textContent = "Update Project";

  const fields = {
    projectName: project.name,
    customerName: project.customer_name,
    customerPhone: project.customer_phone,
    customerEmail: project.customer_email,
    projectStatus: project.status || "active",
    projectPriority: project.priority || "medium",
    vehicleBrand: project.vehicle_brand,
    vehicleModel: project.vehicle_model,
    vehicleYear: project.vehicle_year,
    licensePlate: project.vehicle_license_plate,
    estimatedCost: project.estimated_cost,
    estimatedRevenue: project.estimated_revenue,
    startDate: project.project_start_date
      ? project.project_start_date.split("T")[0]
      : "",
    targetDelivery: project.project_target_delivery
      ? project.project_target_delivery.split("T")[0]
      : "",
    projectNotes: project.notes,
  };

  Object.keys(fields).forEach((key) => {
    const el = DOM[key]();
    if (el) {
      el.value =
        fields[key] !== undefined && fields[key] !== null ? fields[key] : "";
    }
  });

  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
    setTimeout(() => DOM.projectName()?.focus(), 100);
  }
}

export async function handleProjectFormSubmit(e) {
  e.preventDefault();

  const editId = DOM.editProjectId?.value || "";
  const isEdit = !!editId;

  const data = {
    name: DOM.projectName?.value?.trim(),
    customer_name: DOM.customerName?.value?.trim(),
    customer_phone: DOM.customerPhone?.value?.trim(),
    customer_email: DOM.customerEmail?.value?.trim(),
    status: DOM.projectStatus?.value || "active",
    priority: DOM.projectPriority?.value || "medium",
    vehicle_brand: DOM.vehicleBrand?.value?.trim(),
    vehicle_model: DOM.vehicleModel?.value?.trim(),
    vehicle_year: DOM.vehicleYear?.value
      ? parseInt(DOM.vehicleYear.value)
      : null,
    vehicle_license_plate: DOM.licensePlate?.value?.trim(),
    estimated_cost: DOM.estimatedCost?.value
      ? parseFloat(DOM.estimatedCost.value)
      : null,
    estimated_revenue: DOM.estimatedRevenue?.value
      ? parseFloat(DOM.estimatedRevenue.value)
      : null,
    project_start_date: DOM.startDate?.value || null,
    project_target_delivery: DOM.targetDelivery?.value || null,
    notes: DOM.projectNotes?.value?.trim(),
  };

  // Validasi
  const errors = [];
  if (!data.name) errors.push("Project name is required");
  if (!data.customer_name) errors.push("Customer name is required");
  if (!data.vehicle_brand) errors.push("Vehicle brand is required");
  if (!data.vehicle_model) errors.push("Vehicle model is required");

  if (errors.length > 0) {
    showToast(`Please fix the following:\n• ${errors.join("\n• ")}`, "error");
    return;
  }

  // Konfirmasi untuk update
  if (isEdit) {
    const currentProject = state.projects.find((p) => p.id === editId);
    if (
      currentProject &&
      currentProject.status === "completed" &&
      data.status !== "completed"
    ) {
      if (
        !confirm(
          "This project was completed. Changing status will mark it as not completed. Continue?",
        )
      ) {
        return;
      }
    }
  }
  if (
    data.customer_email &&
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.customer_email)
  ) {
    showToast("❌ Invalid email format", "error");
    DOM.customerEmail()?.focus();
    return;
  }
  if (
    data.customer_phone &&
    !/^[0-9+\-\s()]{8,15}$/.test(data.customer_phone)
  ) {
    showToast("❌ Invalid phone number (min 8 digits)", "error");
    DOM.customerPhone()?.focus();
    return;
  }

  const submitBtn = DOM.submitProjectBtn();
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = isEdit ? "Updating..." : "Creating...";
  }

  try {
    const result = isEdit
      ? await ProjectAPI.update(editId, data)
      : await ProjectAPI.create(data);

    if (result) {
      showToast(
        isEdit ? "✅ Project updated!" : "✅ Project created!",
        "success",
      );
      closeProjectModal();
      await loadProjects();
    } else {
      showToast(
        isEdit ? "❌ Failed to update project" : "❌ Failed to create project",
        "error",
      );
    }
  } catch (error) {
    console.error("Project form error:", error);
    showToast("❌ " + (error.message || "Something went wrong"), "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = isEdit ? "Update Project" : "Create Project";
    }
  }
}
