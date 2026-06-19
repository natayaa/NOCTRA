/* =========================================================
   projects.js – Simplified Card view with Tabbed Drawer
   (Workers: update progress, consume material, add labor)
   ========================================================= */
(function () {
  "use strict";

  const API_BASE = "/api/projects";
  let projectsData = [];
  let currentFilter = "";
  let currentSearch = "";
  let currentProjectId = null;

  // ---- DOM refs ----
  const cardGrid = document.getElementById("projectCardGrid");
  const searchInput = document.getElementById("projectSearch");
  const statusFilter = document.getElementById("statusFilter");
  const activeCount = document.getElementById("activeCount");
  const prodCount = document.getElementById("prodCount");
  const completedCount = document.getElementById("completedCount");
  const revenueTotal = document.getElementById("revenueTotal");

  // ---- Helpers ----
  function formatCurrency(amount) {
    return `Rp ${Number(amount || 0).toLocaleString("id-ID")}`;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function statusLabel(status) {
    const map = {
      new: "New",
      quoted: "Quoted",
      approved: "Approved",
      preparation: "Preparation",
      painting: "Painting",
      assembly: "Assembly",
      completed: "Completed",
    };
    return map[status] || status;
  }

  function showToast(msg, isError = false) {
    let t = document.querySelector(".app-toast");
    if (!t) {
      t = document.createElement("div");
      t.className = "app-toast";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.className = "app-toast" + (isError ? " error" : "");
    setTimeout(() => t.classList.add("show"), 10);
    clearTimeout(t._timeout);
    t._timeout = setTimeout(() => t.classList.remove("show"), 3000);
  }

  // ---- API ----
  async function fetchJSON(url, options = {}) {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || res.statusText);
    }
    return res.json();
  }

  // ---- Load & Render ----
  async function loadProjects() {
    cardGrid.innerHTML = `<div class="loading-placeholder">Loading projects...</div>`;
    try {
      const data = await fetchJSON(`${API_BASE}/`);
      projectsData = data.data || [];
      renderCards();
      updateDashboard();
    } catch (err) {
      console.error(err);
      showToast("Failed to load projects", true);
      cardGrid.innerHTML = `<div class="loading-placeholder">Error loading projects</div>`;
    }
  }

  // ---- Render Cards (tanpa milestone, dengan tombol Complete) ----
  function renderCards() {
    const search = currentSearch.toLowerCase().trim();
    const status = currentFilter;
    const filtered = projectsData.filter((project) => {
      const matchSearch =
        !search ||
        project.name.toLowerCase().includes(search) ||
        project.customer_name.toLowerCase().includes(search) ||
        project.vehicle_brand.toLowerCase().includes(search) ||
        project.vehicle_model.toLowerCase().includes(search);
      const matchStatus = !status || project.status === status;
      return matchSearch && matchStatus;
    });

    if (filtered.length === 0) {
      cardGrid.innerHTML = `<div class="loading-placeholder">No projects found</div>`;
      return;
    }

    cardGrid.innerHTML = filtered
      .map((project) => {
        const progress = project.progress || 0;
        const isComplete = project.status === "completed";
        return `
          <div class="project-card-item" data-id="${project.id}">
            <div class="card-header">
              <h4>${escapeHtml(project.name)}</h4>
              <span class="status-badge ${project.status}">${statusLabel(project.status)}</span>
            </div>
            <div class="card-body">
              <div class="customer">👤 ${escapeHtml(project.customer_name)}</div>
              <div class="vehicle">🏍️ ${escapeHtml(project.vehicle_brand)} ${escapeHtml(project.vehicle_model)}</div>
            </div>
            <div class="card-progress">
              <div class="progress-bar">
                <div class="fill" style="width:${progress}%;"></div>
              </div>
              <div class="progress-label">
                <span>Progress</span>
                <span>${progress}%</span>
              </div>
            </div>
            <div class="card-actions">
              <button class="btn-progress" data-action="update-progress" data-id="${project.id}">
                <i class="ph ph-sliders-horizontal"></i> Progress
              </button>
              <button class="btn-details" data-action="view-details" data-id="${project.id}">
                <i class="ph ph-eye"></i> Detail
              </button>
              ${progress === 100 && !isComplete ? `
                <button class="btn-complete" data-action="complete" data-id="${project.id}">
                  <i class="ph ph-check-circle"></i> Complete
                </button>
              ` : ''}
              ${isComplete ? `
                <span class="badge-completed">✅ Selesai</span>
              ` : ''}
            </div>
          </div>
        `;
      })
      .join("");

    // Attach events
    cardGrid.querySelectorAll('[data-action="update-progress"]').forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openProgressPopup(btn.dataset.id);
      });
    });
    cardGrid.querySelectorAll('[data-action="view-details"]').forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openDrawer(btn.dataset.id);
      });
    });
    cardGrid.querySelectorAll('[data-action="complete"]').forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        completeProject(btn.dataset.id);
      });
    });
    // Klik card -> buka progress popup (opsional)
    cardGrid.querySelectorAll(".project-card-item").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".card-actions")) return;
        const id = card.dataset.id;
        if (id) openProgressPopup(id);
      });
    });
  }

  // ---- Milestones helper (untuk progress popup) ----
  function getMilestones(status, progress) {
    const allMilestones = [
      { key: "inquiry", label: "Inquiry Approved" },
      { key: "parts", label: "Parts Ordered" },
      { key: "disassembly", label: "Disassembly" },
      { key: "paint_prep", label: "Paint Preparation" },
      { key: "painting", label: "Painting" },
      { key: "assembly", label: "Assembly" },
      { key: "qc", label: "Quality Check" },
      { key: "delivery", label: "Ready for Delivery" },
    ];

    const statusMap = {
      new: ["inquiry"],
      quoted: ["inquiry"],
      approved: ["inquiry"],
      preparation: ["inquiry", "parts"],
      painting: ["inquiry", "parts", "disassembly", "paint_prep"],
      assembly: ["inquiry", "parts", "disassembly", "paint_prep", "painting"],
      completed: allMilestones.map((m) => m.key),
    };

    const completed = statusMap[status] || ["inquiry"];
    return allMilestones.map((m, idx) => {
      const isDone = completed.includes(m.key);
      const isActive = !isDone && completed.length === idx;
      return {
        label: m.label,
        status: isDone ? "done" : isActive ? "active" : "pending",
      };
    });
  }

  // ---- Dashboard ----
  function updateDashboard() {
    const active = projectsData.filter((p) => p.status !== "completed").length;
    const inProd = projectsData.filter((p) =>
      ["preparation", "painting", "assembly"].includes(p.status)
    ).length;
    const completed = projectsData.filter(
      (p) => p.status === "completed"
    ).length;
    const revenue = projectsData.reduce(
      (sum, p) => sum + (p.estimated_revenue || 0),
      0
    );
    if (activeCount) activeCount.textContent = active;
    if (prodCount) prodCount.textContent = inProd;
    if (completedCount) completedCount.textContent = completed;
    if (revenueTotal) revenueTotal.textContent = formatCurrency(revenue);
  }

  // ---- Inisialisasi Tab di Drawer ----
  function initTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    const panels = {
      overview: document.getElementById('tab-overview'),
      material: document.getElementById('tab-material'),
      labor: document.getElementById('tab-labor'),
      timeline: document.getElementById('tab-timeline')
    };
    tabs.forEach(btn => {
      btn.addEventListener('click', () => {
        tabs.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tabName = btn.dataset.tab;
        Object.keys(panels).forEach(key => {
          panels[key].classList.toggle('active', key === tabName);
        });
      });
    });
  }

  // ---- Progress Popup ----
  let progressPopup, progressPopupSlider, progressPopupValue, progressPopupNote;
  let progressPopupMilestones, markCompleteCheckbox;
  let currentProgressProjectId = null;
  let currentProgressData = null;

  function initializeProgressPopup() {
    progressPopup = document.getElementById("progressPopup");
    progressPopupSlider = document.getElementById("progressPopupSlider");
    progressPopupValue = document.getElementById("progressPopupValue");
    progressPopupNote = document.getElementById("progressPopupNote");
    progressPopupMilestones = document.getElementById("progressPopupMilestones");
    markCompleteCheckbox = document.getElementById("markCompleteCheckbox");

    // Cek apakah semua elemen ditemukan
    if (!progressPopup || !progressPopupSlider || !progressPopupValue || !progressPopupNote || !progressPopupMilestones || !markCompleteCheckbox) {
      console.error("Progress popup elements not found!");
      return;
    }

    const closeBtn = document.getElementById("closeProgressPopup");
    const cancelBtn = document.getElementById("cancelProgressBtn");
    const saveBtn = document.getElementById("saveProgressBtn");

    closeBtn?.addEventListener("click", closeProgressPopup);
    cancelBtn?.addEventListener("click", closeProgressPopup);
    progressPopup.addEventListener("click", (e) => {
      if (e.target === progressPopup) closeProgressPopup();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeProgressPopup();
    });

    progressPopupSlider?.addEventListener("input", function () {
      const val = parseInt(this.value, 10);
      progressPopupValue.textContent = val;
      updateMilestoneHighlights(val);
      if (val === 100 && currentProgressData?.status !== "completed") {
        markCompleteCheckbox.style.display = "flex";
        markCompleteCheckbox.checked = true;
      } else {
        markCompleteCheckbox.style.display = "none";
        markCompleteCheckbox.checked = false;
      }
    });

    saveBtn?.addEventListener("click", saveProgressPopup);
  }

  // ---- Delete Labor ----
  async function deleteLaborItem(laborId, projectId) {
    if (!confirm("Hapus data labor ini?")) return;
    try {
      await fetchJSON(`/api/projects/${projectId}/labor/${laborId}`, {
        method: "DELETE",
      });
      showToast("Labor deleted");
      openDrawer(projectId); // refresh drawer
    } catch (err) {
      showToast(err.message || "Gagal hapus labor", true);
    }
  }

  // ---- Delete Material Usage ----
  async function deleteMaterialItem(usageId, projectId) {
    if (!confirm("Hapus pemakaian material ini?")) return;
    try {
      await fetchJSON(`/api/inventory/usage/${usageId}`, {
        method: "DELETE",
      });
      showToast("Material usage deleted");
      openDrawer(projectId);
    } catch (err) {
      showToast(err.message || "Gagal hapus material", true);
    }
  }

  function openProgressPopup(id) {
    // Pastikan elemen sudah diinisialisasi
    if (!progressPopupSlider) {
      console.error("Progress popup not initialized");
      return;
    }

    const proj = projectsData.find((p) => p.id === id);
    if (!proj) return;
    currentProgressProjectId = id;
    currentProgressData = proj;

    const titleEl = document.getElementById("progressPopupTitle");
    const subtitleEl = document.getElementById("progressPopupSubtitle");
    if (titleEl) titleEl.textContent = `Update Progress: ${proj.name}`;
    if (subtitleEl)
      subtitleEl.textContent = `${proj.customer_name} • ${proj.vehicle_brand} ${proj.vehicle_model}`;

    const progress = proj.progress || 0;
    progressPopupSlider.value = progress;
    progressPopupValue.textContent = progress;
    progressPopupNote.value = proj.notes || "";

    const milestones = getMilestones(proj.status, progress);
    progressPopupMilestones.innerHTML = milestones
      .map(
        (m) => `
      <div class="milestone-item ${m.status}">
        ${m.status === "done" ? "✅" : m.status === "active" ? "⏳" : "⬜"}
        ${escapeHtml(m.label)}
      </div>
    `
      )
      .join("");
    updateMilestoneHighlights(progress);

    const isCompleted = proj.status === "completed";
    if (isCompleted) {
      markCompleteCheckbox.style.display = "flex";
      markCompleteCheckbox.checked = true;
      markCompleteCheckbox.disabled = true;
    } else if (progress === 100) {
      markCompleteCheckbox.style.display = "flex";
      markCompleteCheckbox.checked = true;
      markCompleteCheckbox.disabled = false;
    } else {
      markCompleteCheckbox.style.display = "none";
      markCompleteCheckbox.checked = false;
      markCompleteCheckbox.disabled = false;
    }

    progressPopup.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeProgressPopup() {
    progressPopup?.classList.remove("active");
    document.body.style.overflow = "";
    currentProgressProjectId = null;
    currentProgressData = null;
  }

  function updateMilestoneHighlights(progress) {
    const items = progressPopupMilestones.querySelectorAll(".milestone-item");
    const total = items.length;
    const doneCount = Math.floor((progress / 100) * total);
    items.forEach((item, index) => {
      const label = item.textContent.replace(/[✅⏳⬜]\s*/, "");
      if (index < doneCount) {
        item.className = "milestone-item done";
        item.innerHTML = "✅ " + label;
      } else if (index === doneCount) {
        item.className = "milestone-item active";
        item.innerHTML = "⏳ " + label;
      } else {
        item.className = "milestone-item pending";
        item.innerHTML = "⬜ " + label;
      }
    });
  }

  async function saveProgressPopup() {
    if (!currentProgressProjectId) return;
    const progress = parseInt(progressPopupSlider.value, 10);
    const note = progressPopupNote.value.trim();
    const markComplete = markCompleteCheckbox.checked;

    const payload = { progress };
    if (note !== (currentProgressData?.notes || "")) {
      payload.notes = note;
    }
    if (markComplete && progress === 100) {
      payload.status = "completed";
    }

    try {
      await fetchJSON(`${API_BASE}/${currentProgressProjectId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      showToast("Progress updated successfully");
      closeProgressPopup();
      loadProjects();
    } catch (err) {
      console.error(err);
      showToast("Failed to update progress", true);
    }
  }

  // ---- Drawer ----
  let drawer = document.getElementById("projectDrawer");
  let closeDrawerBtn = document.getElementById("closeDrawer");

  function initializeDrawer() {
    if (!drawer) return;
    closeDrawerBtn?.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeDrawer();
    });
  }

  // ---------- MAIN openDrawer ----------
  async function openDrawer(id) {
    if (!drawer) return;
    currentProjectId = id;
    drawer.classList.add("active");

    // Reset loading placeholders
    const placeholderFields = [
      "drawerTitle",
      "drawerCustomer",
      "drawerPhone",
      "drawerStatus",
      "drawerProgressFill",
      "drawerProgressText",
      "drawerBrand",
      "drawerModel",
      "drawerPlate",
      "drawerEstCost",
      "drawerActualCost",
      "drawerEstRevenue",
      "drawerActualRevenue",
      "drawerProfit",
      "drawerMargin",
      "drawerStartDate",
      "drawerDelivery",
      "drawerDuration",
      "drawerTimelineStatus",
      "drawerNotes",
    ];
    placeholderFields.forEach((fieldId) => {
      const el = document.getElementById(fieldId);
      if (el) {
        if (fieldId === "drawerStatus")
          el.innerHTML = '<span class="status-badge">-</span>';
        else if (fieldId === "drawerProgressFill") el.style.width = "0%";
        else if (fieldId === "drawerProgressText") el.textContent = "0%";
        else if (fieldId === "drawerTitle") el.textContent = "Loading...";
        else el.textContent = "-";
      }
    });

    try {
      const data = await fetchJSON(`${API_BASE}/${id}`);
      const p = data.data;
      populateDrawer(p);
    } catch (err) {
      console.error(err);
      showToast("Could not load project details", true);
      closeDrawer();
    }
  }

  // ---- populateDrawer (dengan tab) ----
  function populateDrawer(p) {
    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };
    const setHTML = (id, html) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = html;
    };

    // Overview
    setText('drawerCustomer', p.customer_name || '-');
    setText('drawerPhone', p.phone_number || '-');
    setText('drawerBrand', p.vehicle_brand || '-');
    setText('drawerModel', p.vehicle_model || '-');
    setText('drawerPlate', p.license_plate || '-');
    setHTML('drawerStatus', `<span class="status-badge ${p.status || ''}">${statusLabel(p.status)}</span>`);

    const progress = p.progress || 0;
    const fillEl = document.getElementById('drawerProgressFill');
    if (fillEl) fillEl.style.width = progress + '%';
    setText('drawerProgressText', progress + '%');

    // Financial
    const estCost = p.estimated_cost || 0;
    const actualCost = p.actual_cost || 0;
    const estRevenue = p.estimated_revenue || 0;
    const actualRevenue = p.actual_revenue || 0;
    const profit = actualRevenue - actualCost;
    const margin = actualRevenue > 0 ? ((profit / actualRevenue) * 100).toFixed(0) : 0;

    setText('drawerEstCost', formatCurrency(estCost));
    setText('drawerActualCost', formatCurrency(actualCost));
    setText('drawerEstRevenue', formatCurrency(estRevenue));
    setText('drawerActualRevenue', formatCurrency(actualRevenue));
    setText('drawerProfit', formatCurrency(profit));
    setText('drawerMargin', margin + '%');

    // Timeline
    const startDate = p.start_date ? new Date(p.start_date) : null;
    const targetDate = p.target_delivery ? new Date(p.target_delivery) : null;
    const now = new Date();

    setText('drawerStartDate', startDate ? startDate.toLocaleDateString() : '-');
    setText('drawerDelivery', targetDate ? targetDate.toLocaleDateString() : '-');

    let durationText = '-';
    let timelineStatusText = '-';
    if (startDate && targetDate) {
      const days = Math.ceil((targetDate - startDate) / (1000 * 60 * 60 * 24));
      durationText = `${days} days`;
      const daysRemaining = Math.ceil((targetDate - now) / (1000 * 60 * 60 * 24));
      if (now > targetDate) {
        timelineStatusText = `⚠️ Overdue by ${Math.abs(daysRemaining)} days`;
      } else if (daysRemaining <= 0) {
        timelineStatusText = '🎯 Due today!';
      } else if (daysRemaining <= 3) {
        timelineStatusText = `⏰ ${daysRemaining} days remaining (urgent)`;
      } else {
        timelineStatusText = `✅ ${daysRemaining} days remaining`;
      }
    } else if (startDate && !targetDate) {
      const daysPassed = Math.ceil((now - startDate) / (1000 * 60 * 60 * 24));
      durationText = 'No target set';
      timelineStatusText = `Started ${daysPassed} days ago`;
    } else {
      durationText = 'Dates not set';
    }
    setText('drawerDuration', durationText);
    setText('drawerTimelineStatus', timelineStatusText);
    // Update milestones berdasarkan progress
    updateTimelineMilestones(progress);


    // Notes (untuk timeline note, bisa diisi dari p.notes atau field terpisah)
    const timelineNote = document.getElementById('timelineNote');
    if (timelineNote) {
      // Bisa diisi dari p.notes atau dari field khusus 'timeline_notes' jika ada
      timelineNote.textContent = p.notes || '-';
    }

    // Load Material & Labor
    loadMaterialsForProject(p.id);
    loadMaterialUsageList(p.id);
    loadLaborList(p.id);

    const viewProjectBtn = document.getElementById('drawerViewProjectBtn');
    if (inq.project && inq.project.id) {
      // Arahkan ke halaman Projects dengan parameter open
      viewProjectBtn.href = `/management/projects?open=${inq.project.id}`;
      viewProjectBtn.style.display = 'inline-flex';
    } else {
      viewProjectBtn.style.display = 'none';
    }
  }

  // ---- Material usage ----
  async function loadMaterialsForProject(projectId) {
    try {
      const data = await fetchJSON("/api/inventory/");
      const select = document.getElementById("materialSelect");
      if (!select) return;
      select.innerHTML = '<option value="">Select Material</option>';
      if (data.data) {
        data.data.forEach((item) => {
          const opt = document.createElement("option");
          opt.value = item.id;
          opt.textContent = `${item.name} (${item.current_stock} ${item.unit})`;
          select.appendChild(opt);
        });
      }
    } catch (err) {
      console.warn("Failed to load materials for dropdown", err);
    }
  }

  async function loadMaterialUsageList(projectId) {
    const container = document.getElementById('drawerMaterialsList');
    if (!container) return;
    try {
      const response = await fetch(`/api/inventory/usage/project/${projectId}`);
      if (!response.ok) throw new Error('Not found');
      const data = await response.json();
      if (data.success && data.data && data.data.length > 0) {
        container.innerHTML = data.data
          .map(
            (item) => `
              <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border-color);padding:0.5rem 0;">
                <span>${escapeHtml(item.item_name || 'Unknown')}</span>
                <span>${item.quantity} ${escapeHtml(item.unit || '')}</span>
                <span>${formatCurrency(item.total_cost || item.quantity * item.cost_price)}</span>
                <button class="btn-delete-item" data-type="material" data-id="${item.id}" data-project="${projectId}" title="Hapus pemakaian material ini">×</button>
              </div>
            `
          )
          .join('');
      } else {
        container.innerHTML = '<p style="color:var(--text-muted);">No materials consumed yet.</p>';
      }
    } catch (err) {
      container.innerHTML = '<p style="color:var(--text-muted);">No materials consumed yet.</p>';
    }
  }

  // ---- Labor ----
  async function loadLaborList(projectId) {
    const container = document.getElementById('laborList');
    if (!container) return;
    try {
      const response = await fetch(`/api/projects/${projectId}/labor`);
      if (!response.ok) throw new Error('Not found');
      const data = await response.json();
      if (data.data && data.data.length > 0) {
        container.innerHTML = data.data
          .map(
            (item) => `
              <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border-color);padding:0.5rem 0;">
                <span>${escapeHtml(item.labor_type)}</span>
                <span>${item.hours} jam @ ${formatCurrency(item.rate_per_hour)}</span>
                <span>${formatCurrency(item.total_cost)}</span>
                <button class="btn-delete-item" data-type="labor" data-id="${item.id}" data-project="${projectId}" title="Hapus data labor ini">×</button>
              </div>
            `
          )
          .join('');
      } else {
        container.innerHTML = '<p style="color:var(--text-muted);">No labor recorded.</p>';
      }
    } catch (err) {
      container.innerHTML = '<p style="color:var(--text-muted);">No labor recorded.</p>';
    }
  }

  // ---- Consume material button ----
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("#consumeMaterialBtn");
    if (!btn) return;
    e.stopPropagation();
    const projectId = currentProjectId;
    if (!projectId) {
      showToast("No project selected", true);
      return;
    }
    const select = document.getElementById("materialSelect");
    const qtyInput = document.getElementById("materialQty");
    if (!select || !qtyInput) {
      showToast("Material form not ready", true);
      return;
    }
    const itemId = select.value;
    const qty = parseInt(qtyInput.value, 10);
    if (!itemId) {
      showToast("Select a material", true);
      return;
    }
    if (!qty || qty < 1) {
      showToast("Enter valid quantity", true);
      return;
    }
    try {
      await fetchJSON("/api/inventory/usage", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          item_id: itemId,
          quantity: qty,
        }),
      });
      showToast("Material consumed");
      openDrawer(projectId); // refresh drawer
    } catch (err) {
      showToast(err.message || "Failed to consume material", true);
    }
  });

  // Event delegation untuk tombol delete di drawer
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".btn-delete-item");
    if (!btn) return;
    const type = btn.dataset.type;
    const id = btn.dataset.id;
    const projectId = btn.dataset.project || currentProjectId;
    if (!projectId) {
      showToast("Project ID not found", true);
      return;
    }
    if (type === "labor") {
      await deleteLaborItem(id, projectId);
    } else if (type === "material") {
      await deleteMaterialItem(id, projectId);
    }
  });

  // ---- Complete Project ----
  async function completeProject(id) {
    if (!confirm("✅ Tandai project ini sebagai selesai?\n\nProject akan diarsipkan dan tidak bisa diubah lagi.")) return;
    try {
      await fetchJSON(`${API_BASE}/${id}/complete`, {
        method: "POST",
      });
      showToast("🎉 Project completed successfully!");
      loadProjects(); // refresh daftar
    } catch (err) {
      console.error(err);
      showToast(err.message || "Failed to complete project", true);
    }
  }

  // ---- Add Labor button ----
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("#addLaborBtn");
    if (!btn) return;

    const projectId = currentProjectId;
    if (!projectId) {
      showToast("Tidak ada project yang dipilih", true);
      return;
    }

    const select = document.getElementById("laborTypeSelect");
    const hoursInput = document.getElementById("laborHours");
    const laborType = select?.value;
    const hours = parseFloat(hoursInput?.value);

    if (!laborType) {
      showToast("Pilih jenis labor", true);
      return;
    }
    if (!hours || hours < 0.5) {
      showToast("Masukkan jam kerja yang valid (min 0.5)", true);
      return;
    }

    try {
      await fetchJSON(`/api/projects/${projectId}/labor`, {
        method: "POST",
        body: JSON.stringify({ labor_type: laborType, hours: hours }),
      });
      showToast("Labor added");
      openDrawer(projectId);
    } catch (err) {
      showToast(err.message || "Gagal menambah labor", true);
    }
  });

  function closeDrawer() {
    if (drawer) drawer.classList.remove("active");
    currentProjectId = null;
  }

  // ---- Modal (Create / Edit) ----
  let modal, modalTitle, modalSubtitle, form, submitBtn;
  let editingProjectId = null;

  function initializeModal() {
    modal = document.getElementById("projectModal");
    if (!modal) return;
    modalTitle = document.getElementById("modalTitle");
    modalSubtitle = document.getElementById("modalSubtitle");
    form = document.getElementById("projectForm");
    submitBtn = document.getElementById("submitProjectBtn");
    const openBtn = document.getElementById("newProjectBtn");
    const closeBtn = document.getElementById("closeModal");
    const cancelBtn = document.getElementById("cancelModalBtn");

    openBtn?.addEventListener("click", () => {
      editingProjectId = null;
      if (modalTitle) modalTitle.textContent = "Create New Project";
      if (modalSubtitle)
        modalSubtitle.textContent = "Register workshop project and production schedule";
      if (submitBtn) submitBtn.textContent = "Create Project";
      form?.reset();
      const editIdField = document.getElementById("editProjectId");
      if (editIdField) editIdField.value = "";
      modal.classList.add("active");
      document.body.style.overflow = "hidden";
    });

    closeBtn?.addEventListener("click", closeModal);
    cancelBtn?.addEventListener("click", closeModal);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });

    form?.addEventListener("submit", handleFormSubmit);
  }

  function closeModal() {
    modal?.classList.remove("active");
    document.body.style.overflow = "";
    editingProjectId = null;
  }

  async function openEditModal(id) {
    try {
      const data = await fetchJSON(`${API_BASE}/${id}`);
      const p = data.data;
      editingProjectId = id;
      if (modalTitle) modalTitle.textContent = "Edit Project";
      if (modalSubtitle) modalSubtitle.textContent = "Update project details";
      if (submitBtn) submitBtn.textContent = "Update Project";

      const fields = {
        editProjectId: id,
        projectName: p.name || "",
        customerName: p.customer_name || "",
        phoneNumber: p.phone_number || "",
        projectStatus: p.status || "new",
        progressSliderForm: p.progress || 0,
        progressDisplay: p.progress || 0,
        vehicleBrand: p.vehicle_brand || "",
        vehicleModel: p.vehicle_model || "",
        licensePlate: p.license_plate || "",
        estimatedCost: p.estimated_cost || 0,
        estimatedRevenue: p.estimated_revenue || 0,
        actualCost: p.actual_cost || 0,
        actualRevenue: p.actual_revenue || 0,
        startDate: p.start_date || "",
        targetDelivery: p.target_delivery || "",
        projectNotes: p.notes || "",
      };

      Object.keys(fields).forEach((key) => {
        const el = document.getElementById(key);
        if (el) el.value = fields[key];
      });

      modal.classList.add("active");
      document.body.style.overflow = "hidden";
    } catch (err) {
      console.error(err);
      showToast("Could not load project for editing", true);
    }
  }

  async function handleFormSubmit(e) {
    e.preventDefault();
    const getVal = (id) => document.getElementById(id)?.value || "";
    const payload = {
      name: getVal("projectName").trim(),
      customer_name: getVal("customerName").trim(),
      phone_number: getVal("phoneNumber").trim(),
      status: getVal("projectStatus"),
      progress: parseInt(getVal("progressSliderForm"), 10) || 0,
      vehicle_brand: getVal("vehicleBrand").trim(),
      vehicle_model: getVal("vehicleModel").trim(),
      license_plate: getVal("licensePlate").trim(),
      estimated_cost: parseFloat(getVal("estimatedCost")) || 0,
      estimated_revenue: parseFloat(getVal("estimatedRevenue")) || 0,
      actual_cost: parseFloat(getVal("actualCost")) || 0,
      actual_revenue: parseFloat(getVal("actualRevenue")) || 0,
      start_date: getVal("startDate") || null,
      target_delivery: getVal("targetDelivery") || null,
      notes: getVal("projectNotes").trim(),
    };

    try {
      let url = `${API_BASE}/`;
      let method = "POST";
      if (editingProjectId) {
        url = `${API_BASE}/${editingProjectId}`;
        method = "PATCH";
      }
      await fetchJSON(url, { method, body: JSON.stringify(payload) });
      showToast(editingProjectId ? "Project updated" : "Project created");
      form?.reset();
      closeModal();
      loadProjects();
    } catch (err) {
      console.error(err);
      showToast(editingProjectId ? "Update failed" : "Create failed", true);
    }
  }

  // ---- Load labor options from price list ----
  async function loadLaborOptions() {
    try {
      const res = await fetch('/api/price-list/?category=labor&active_only=true');
      const data = await res.json();
      const select = document.getElementById('laborTypeSelect');
      if (!select) return;
      select.innerHTML = '<option value="">Pilih Labor</option>';
      if (data.data) {
        data.data.forEach(item => {
          const opt = document.createElement('option');
          opt.value = item.name;
          opt.textContent = `${item.name} (${formatCurrency(item.price)} / ${item.unit || 'jam'})`;
          select.appendChild(opt);
        });
      }
    } catch (err) {
      console.warn("Gagal load labor options", err);
    }
  }

  // ---- Progress slider in modal ----
  function initializeProgressSlider() {
    const slider = document.getElementById("progressSliderForm");
    const display = document.getElementById("progressDisplay");
    if (!slider) return;
    slider.addEventListener("input", () => {
      const val = slider.value;
      if (display) display.textContent = val;
      slider.style.background = `linear-gradient(90deg, var(--accent) ${val}%, rgba(255,255,255,0.08) ${val}%)`;
    });
    slider.dispatchEvent(new Event("input"));
  }

  // ---- Update Milestones di Timeline ----
  function updateTimelineMilestones(progress) {
    const container = document.getElementById('timelineMilestones');
    if (!container) return;
    const stages = [
      { key: 'disassembly', label: 'Disassembly', threshold: 20 },
      { key: 'paint_prep', label: 'Paint Prep', threshold: 40 },
      { key: 'painting', label: 'Painting', threshold: 60 },
      { key: 'assembly', label: 'Assembly', threshold: 80 },
      { key: 'qc', label: 'Quality Check', threshold: 95 },
      { key: 'delivery', label: 'Ready for Delivery', threshold: 100 }
    ];
    let html = '';
    stages.forEach((stage, index) => {
      let status = 'pending';
      if (progress >= stage.threshold) status = 'done';
      else if (index === 0 || progress >= (stages[index-1]?.threshold || 0)) status = 'active';
      const icon = status === 'done' ? '✅' : status === 'active' ? '⏳' : '⬜';
      html += `<div class="milestone-item ${status}">${icon} ${stage.label}</div>`;
    });
    container.innerHTML = html;
  }

  // ---- Search & Filter ----
  function initializeSearch() {
    searchInput?.addEventListener("input", () => {
      currentSearch = searchInput.value;
      renderCards();
    });
    statusFilter?.addEventListener("change", () => {
      currentFilter = statusFilter.value;
      renderCards();
    });
  }

  // ---- Export placeholder ----
  document.getElementById("exportBtn")?.addEventListener("click", () => {
    showToast("Export feature coming soon");
  });

  function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
  }

  // ---- Init ----
  async function init() {
    initializeDrawer();
    initializeModal();
    initializeSearch();
    initializeProgressSlider();
    initializeProgressPopup();
    loadLaborOptions();
    await loadProjects(); // ← tunggu sampai data termuat
    initTabs();

    // Cek parameter 'open' di URL (dari inquiry drawer)
    const openProjectId = getQueryParam('open');
    if (openProjectId) {
      // Langsung buka drawer, data sudah ada
      openDrawer(openProjectId);
      const url = new URL(window.location);
      url.searchParams.delete('open');
      window.history.replaceState({}, '', url);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();