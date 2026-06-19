/* =========================================================
   inquiries.js – Table view with full CRUD + Drawer
   (Fixed: added Project Status column, proper actions,
    disable Convert when needed, sync with projects)
   ========================================================= */
(function() {
  'use strict';

  const API_BASE = '/api/customer/inquiry';
  const API_PROJECTS = '/api/projects';

  let inquiriesData = [];
  let currentFilter = '';
  let currentSearch = '';
  let currentInquiryId = null;

  // DOM refs
  const tbody = document.getElementById('inquiriesBody');
  const searchInput = document.getElementById('searchInquiry');
  const statusFilter = document.getElementById('statusFilter');
  const totalSpan = document.getElementById('totalCount');
  const newSpan = document.getElementById('newCount');
  const quotedSpan = document.getElementById('quotedCount');
  const convertedSpan = document.getElementById('convertedCount');

  // Helpers
  function formatCurrency(amount) {
    if (!amount && amount !== 0) return '—';
    return 'Rp ' + Number(amount).toLocaleString('id-ID');
  }

  function escapeHtml(str = '') {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function statusLabel(status) {
    const map = {
      new: 'New',
      quoted: 'Quoted',
      approved: 'Approved',
      rejected: 'Rejected',
      converted: 'Converted',
      completed: 'Completed'
    };
    return map[status?.toLowerCase()] || status;
  }

  function projectStatusLabel(status) {
    const map = {
      new: 'New',
      quoted: 'Quoted',
      approved: 'Approved',
      preparation: 'Preparation',
      painting: 'Painting',
      assembly: 'Assembly',
      completed: 'Completed'
    };
    return map[status?.toLowerCase()] || status || '—';
  }

  function statusBadgeClass(status) {
    const s = status?.toLowerCase() || 'new';
    return s === 'completed' ? 'completed' : s;
  }

  function showToast(msg, isError = false) {
    let t = document.querySelector('.app-toast');
    if (!t) {
      t = document.createElement('div');
      t.className = 'app-toast';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.className = 'app-toast' + (isError ? ' error' : '');
    setTimeout(() => t.classList.add('show'), 10);
    clearTimeout(t._timeout);
    t._timeout = setTimeout(() => t.classList.remove('show'), 3000);
  }

  // API call
  async function fetchJSON(url, options = {}) {
    const res = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || res.statusText);
    }
    return res.json();
  }

  // Load inquiries
  async function loadInquiries() {
    tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">Loading inquiries...</td></tr>`;
    try {
      const data = await fetchJSON(`${API_BASE}/`);
      inquiriesData = data.data || [];
      renderTable();
      updateDashboard();
    } catch (err) {
      console.error(err);
      showToast('Failed to load inquiries', true);
      tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">Error loading inquiries</td></tr>`;
    }
  }

  function renderTable() {
    const search = currentSearch.toLowerCase().trim();
    const status = currentFilter;

    const filtered = inquiriesData.filter(inq => {
      const matchSearch = !search ||
        inq.customer_name.toLowerCase().includes(search) ||
        inq.customer_phone_number.includes(search) ||
        inq.vehicle_brand.toLowerCase().includes(search) ||
        inq.vehicle_model.toLowerCase().includes(search);
      const matchStatus = !status || inq.status.toLowerCase() === status;
      return matchSearch && matchStatus;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="loading-placeholder">No inquiries found</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(inq => {
      const statusLow = (inq.status || '').toLowerCase();
      const canConvert = !(statusLow === 'converted' || statusLow === 'rejected' || statusLow === 'completed');
      const projectStatus = inq.project ? projectStatusLabel(inq.project.status) : '—';
      return `
      <tr data-id="${inq.id}">
        <td data-label="Customer">
          <strong>${escapeHtml(inq.customer_name)}</strong><br>
          <small>${escapeHtml(inq.customer_phone_number)}</small>
        </td>
        <td data-label="Vehicle">${escapeHtml(inq.vehicle_brand)} ${escapeHtml(inq.vehicle_model)}</td>
        <td data-label="Project Type">${escapeHtml(inq.project_type || '—')}</td>
        <td data-label="Status"><span class="status-badge ${statusBadgeClass(inq.status)}">${statusLabel(inq.status)}</span></td>
        <td data-label="Project Status">
          ${inq.project ? `<span class="project-status-badge ${inq.project.status}">${projectStatus}</span>` : '—'}
        </td>
        <td data-label="Created">${new Date(inq.created_at).toLocaleDateString()}</td>
        <td data-label="Actions" style="text-align:center;">
          <div class="actions">
            <button class="action-btn view" data-action="view" title="View Details"><i class="ph ph-eye"></i></button>
            <button class="action-btn quote" data-action="quote" title="Send Quote"><i class="ph ph-file-text"></i></button>
            <button class="action-btn approve" data-action="approve" title="Approve"><i class="ph ph-check"></i></button>
            <button class="action-btn reject" data-action="reject" title="Reject"><i class="ph ph-x"></i></button>
            ${canConvert ? `<button class="action-btn convert" data-action="convert" title="Convert to Project"><i class="ph ph-arrow-right"></i></button>` : ''}
          </div>
        </td>
      </tr>
    `}).join('');

    // Attach events to action buttons
    tbody.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const tr = btn.closest('tr');
        const id = tr.dataset.id;
        const action = btn.dataset.action;
        if (action === 'view') openDrawer(id);
        else if (action === 'quote') openQuoteModal(id);
        else if (action === 'approve') approveInquiry(id);
        else if (action === 'reject') openRejectModal(id);
        else if (action === 'convert') convertInquiry(id);
      });
    });

    // Click on row = view
    tbody.querySelectorAll('tr').forEach(tr => {
      tr.addEventListener('click', () => {
        const id = tr.dataset.id;
        if (id) openDrawer(id);
      });
    });
  }

  function updateDashboard() {
    const total = inquiriesData.length;
    const newCount = inquiriesData.filter(i => i.status?.toLowerCase() === 'new').length;
    const quoted = inquiriesData.filter(i => i.status?.toLowerCase() === 'quoted').length;
    const converted = inquiriesData.filter(i => i.status?.toLowerCase() === 'converted').length;
    if (totalSpan) totalSpan.textContent = total;
    if (newSpan) newSpan.textContent = newCount;
    if (quotedSpan) quotedSpan.textContent = quoted;
    if (convertedSpan) convertedSpan.textContent = converted;
  }

  // ============================================================
  // DRAWER
  // ============================================================
  let drawer = document.getElementById('inquiryDrawer');
  let closeDrawerBtn = document.getElementById('closeDrawer');

  function initializeDrawer() {
    if (!drawer) return;
    closeDrawerBtn?.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });
  }

  async function openDrawer(id) {
    if (!drawer) return;
    currentInquiryId = id;
    drawer.classList.add('active');

    // Reset loading placeholders
    document.getElementById('drawerCustomerName').textContent = 'Loading...';
    document.getElementById('drawerStatusBadge').textContent = '...';
    ['drawerName','drawerPhone','drawerEmail','drawerBrand','drawerModel','drawerPlate','drawerCondition','drawerType','drawerBudget','drawerTarget','drawerDescription','drawerReference','drawerProjectStatus'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '—';
    });
    document.getElementById('drawerPhotosSection').style.display = 'none';
    document.getElementById('drawerTimeline').innerHTML = '<div class="timeline-item"><span>—</span><p>Loading...</p></div>';
    document.getElementById('drawerNotes').value = '';

    try {
      const data = await fetchJSON(`${API_BASE}/${id}`);
      const inq = data.data;
      populateDrawer(inq);
    } catch (err) {
      console.error(err);
      showToast('Could not load inquiry details', true);
      closeDrawer();
    }
  }

  function populateDrawer(inq) {
    // Customer
    document.getElementById('drawerCustomerName').textContent = inq.customer_name || '—';
    document.getElementById('drawerStatusBadge').textContent = statusLabel(inq.status);
    document.getElementById('drawerStatusBadge').className = `status-badge ${statusBadgeClass(inq.status)}`;
    document.getElementById('drawerName').textContent = inq.customer_name || '—';
    document.getElementById('drawerPhone').textContent = inq.customer_phone_number || '—';
    document.getElementById('drawerEmail').textContent = inq.customer_email || '—';

    // Vehicle & Project
    document.getElementById('drawerBrand').textContent = inq.vehicle_brand || '—';
    document.getElementById('drawerModel').textContent = inq.vehicle_model || '—';
    document.getElementById('drawerPlate').textContent = inq.vehicle_license_plate || '—';
    document.getElementById('drawerCondition').textContent = inq.vehicle_condition || '—';
    document.getElementById('drawerType').textContent = inq.project_type || '—';
    document.getElementById('drawerBudget').textContent = formatCurrency(inq.estimated_budget);
    document.getElementById('drawerTarget').textContent = inq.project_target || '—';

    // Project Status (tambahan)
    const projectStatusEl = document.getElementById('drawerProjectStatus');
    if (inq.project && inq.project.status) {
      projectStatusEl.textContent = projectStatusLabel(inq.project.status);
    } else {
      projectStatusEl.textContent = '—';
    }

    // Description
    document.getElementById('drawerDescription').textContent = inq.project_description || 'No description provided.';
    const refLink = document.getElementById('drawerReference');
    if (inq.reference_link) {
      refLink.href = inq.reference_link;
      refLink.style.display = 'inline';
    } else {
      refLink.style.display = 'none';
    }

    // Photos
    const photoSection = document.getElementById('drawerPhotosSection');
    const photoGrid = document.getElementById('drawerPhotos');
    if (inq.photos && inq.photos.length > 0) {
      photoSection.style.display = 'block';
      photoGrid.innerHTML = inq.photos.map(p => `
        <img src="${escapeHtml(p.file_path)}" alt="Photo" loading="lazy" />
      `).join('');
    } else {
      photoSection.style.display = 'none';
    }

    // Financial Summary (dari project jika ada)
    const financialSection = document.getElementById('drawerFinancialSection');
    const estCost = document.getElementById('drawerEstCost');
    const actualCost = document.getElementById('drawerActualCost');
    const estRevenue = document.getElementById('drawerEstRevenue');
    const actualRevenue = document.getElementById('drawerActualRevenue');
    const profitEl = document.getElementById('drawerProfit');
    const marginEl = document.getElementById('drawerMargin');

    if (inq.project && inq.project.id) {
      financialSection.style.display = 'block';
      const p = inq.project;
      const estCostVal = p.estimated_cost || 0;
      const actualCostVal = p.actual_cost || 0;
      const estRevenueVal = p.estimated_revenue || 0;
      const actualRevenueVal = p.actual_revenue || 0;
      const profit = actualRevenueVal - actualCostVal;
      const margin = actualRevenueVal > 0 ? ((profit / actualRevenueVal) * 100).toFixed(0) : 0;

      estCost.textContent = formatCurrency(estCostVal);
      actualCost.textContent = formatCurrency(actualCostVal);
      estRevenue.textContent = formatCurrency(estRevenueVal);
      actualRevenue.textContent = formatCurrency(actualRevenueVal);
      profitEl.textContent = formatCurrency(profit);
      marginEl.textContent = margin + '%';
    } else {
      financialSection.style.display = 'none';
    }

    // Timeline
    const timeline = document.getElementById('drawerTimeline');
    if (inq.activities && inq.activities.length > 0) {
      timeline.innerHTML = inq.activities.map(act => `
        <div class="timeline-item">
          <span>${new Date(act.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
          <p>${escapeHtml(act.activity)}</p>
        </div>
      `).join('');
    } else {
      timeline.innerHTML = `<div class="timeline-item"><span>—</span><p>No activity yet</p></div>`;
    }

    // Notes
    const notes = document.getElementById('drawerNotes');
    notes.value = inq.note || '';
    document.getElementById('noteCounter').textContent = notes.value.length;

    // Action buttons state
    const statusLow = (inq.status || '').toLowerCase();
    const isConverted = statusLow === 'converted';
    const isRejected = statusLow === 'rejected';
    const isCompleted = statusLow === 'completed';

    document.getElementById('drawerApproveBtn').disabled = !(statusLow === 'new' || statusLow === 'quoted');
    document.getElementById('drawerQuoteBtn').disabled = !(statusLow === 'new' || statusLow === 'quoted');
    document.getElementById('drawerRejectBtn').disabled = isRejected || isConverted || isCompleted;
    document.getElementById('drawerConvertBtn').disabled = isConverted || isRejected || isCompleted;

    const viewProjectBtn = document.getElementById('drawerViewProjectBtn');
    if (inq.project && inq.project.id) {
      viewProjectBtn.href = `/management/projects?open=${inq.project.id}`;
      viewProjectBtn.style.display = 'inline-flex';
    } else {
      viewProjectBtn.style.display = 'none';
    }
  }

  function closeDrawer() {
    if (drawer) drawer.classList.remove('active');
    currentInquiryId = null;
  }

  // ============================================================
  // ACTIONS
  // ============================================================

  async function approveInquiry(id) {
    if (!id && currentInquiryId) id = currentInquiryId;
    if (!id) return;
    try {
      await fetchJSON(`${API_BASE}/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'approved' })
      });
      showToast('Inquiry approved');
      loadInquiries();
      if (drawer.classList.contains('active')) {
        await openDrawer(id);
      }
    } catch (err) {
      console.error(err);
      showToast('Failed to approve', true);
    }
  }

  // --- Quote Modal ---
  let quoteModal, quoteForm, quoteCost, quoteRevenue, quoteInquiryId;

  function initializeQuoteModal() {
    quoteModal = document.getElementById('quoteModal');
    quoteForm = document.getElementById('quoteForm');
    quoteCost = document.getElementById('quoteCost');
    quoteRevenue = document.getElementById('quoteRevenue');
    const closeBtn = document.getElementById('closeQuoteModal');
    const cancelBtn = document.getElementById('cancelQuoteBtn');

    closeBtn?.addEventListener('click', closeQuoteModal);
    cancelBtn?.addEventListener('click', closeQuoteModal);
    quoteModal?.addEventListener('click', (e) => { if (e.target === quoteModal) closeQuoteModal(); });
    quoteForm?.addEventListener('submit', handleQuoteSubmit);
  }

  function openQuoteModal(id) {
    quoteInquiryId = id;
    quoteCost.value = '';
    quoteRevenue.value = '';
    quoteModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeQuoteModal() {
    quoteModal.classList.remove('active');
    document.body.style.overflow = '';
    quoteInquiryId = null;
  }

  async function handleQuoteSubmit(e) {
    e.preventDefault();
    const cost = parseFloat(quoteCost.value);
    const revenue = parseFloat(quoteRevenue.value);
    if (isNaN(cost) || isNaN(revenue) || cost < 0 || revenue < 0) {
      showToast('Please enter valid numbers', true);
      return;
    }
    try {
      await fetchJSON(`${API_BASE}/${quoteInquiryId}/quote`, {
        method: 'POST',
        body: JSON.stringify({ estimated_cost: cost, estimated_revenue: revenue })
      });
      showToast('Quotation sent');
      closeQuoteModal();
      loadInquiries();
      if (drawer.classList.contains('active')) {
        await openDrawer(quoteInquiryId);
      }
    } catch (err) {
      console.error(err);
      showToast('Failed to send quote', true);
    }
  }

  // --- Reject Modal ---
  let rejectModal, rejectForm, rejectReason, rejectInquiryId;

  function initializeRejectModal() {
    rejectModal = document.getElementById('rejectModal');
    rejectForm = document.getElementById('rejectForm');
    rejectReason = document.getElementById('rejectReason');
    const closeBtn = document.getElementById('closeRejectModal');
    const cancelBtn = document.getElementById('cancelRejectBtn');

    closeBtn?.addEventListener('click', closeRejectModal);
    cancelBtn?.addEventListener('click', closeRejectModal);
    rejectModal?.addEventListener('click', (e) => { if (e.target === rejectModal) closeRejectModal(); });
    rejectForm?.addEventListener('submit', handleRejectSubmit);
  }

  function openRejectModal(id) {
    rejectInquiryId = id;
    rejectReason.value = '';
    rejectModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeRejectModal() {
    rejectModal.classList.remove('active');
    document.body.style.overflow = '';
    rejectInquiryId = null;
  }

  async function handleRejectSubmit(e) {
    e.preventDefault();
    const reason = rejectReason.value.trim();
    try {
      await fetchJSON(`${API_BASE}/${rejectInquiryId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason })
      });
      showToast('Inquiry rejected');
      closeRejectModal();
      loadInquiries();
      if (drawer.classList.contains('active')) {
        await openDrawer(rejectInquiryId);
      }
    } catch (err) {
      console.error(err);
      showToast('Failed to reject', true);
    }
  }

  // --- Convert to Project ---
  async function convertInquiry(id) {
    if (!id && currentInquiryId) id = currentInquiryId;
    if (!id) return;

    // Cek status inquiry dari data lokal
    const inquiry = inquiriesData.find(i => i.id === id);
    if (inquiry) {
      const statusLow = (inquiry.status || '').toLowerCase();
      if (statusLow === 'converted' || statusLow === 'rejected' || statusLow === 'completed') {
        showToast('Inquiry cannot be converted', true);
        return;
      }
    }

    if (!confirm('Convert this inquiry to a project?')) return;
    try {
      const res = await fetchJSON(`${API_BASE}/${id}/convert`, { method: 'POST' });
      showToast('Inquiry converted to project!');
      loadInquiries();
      if (drawer.classList.contains('active')) {
        await openDrawer(id);
      }
    } catch (err) {
      console.error(err);
      showToast('Conversion failed', true);
    }
  }

  // --- WhatsApp ---
  function openWhatsApp(id) {
    if (!id && currentInquiryId) id = currentInquiryId;
    if (!id) return;
    const inquiry = inquiriesData.find(i => i.id === id);
    if (inquiry && inquiry.customer_phone_number) {
      let phone = inquiry.customer_phone_number.replace(/\D/g, '');
      if (!phone.startsWith('62') && phone.startsWith('0')) phone = '62' + phone.slice(1);
      if (!phone.startsWith('62')) phone = '62' + phone;
      window.open(`https://wa.me/${phone}`, '_blank');
    } else {
      showToast('No phone number available', true);
    }
  }

  // --- Notes auto-save in drawer ---
  let notesTimeout;

  function initializeNotes() {
    const notes = document.getElementById('drawerNotes');
    const counter = document.getElementById('noteCounter');
    if (!notes) return;

    notes.addEventListener('input', () => {
      counter.textContent = notes.value.length;
      clearTimeout(notesTimeout);
      notesTimeout = setTimeout(async () => {
        if (!currentInquiryId) return;
        try {
          await fetchJSON(`${API_BASE}/${currentInquiryId}/notes`, {
            method: 'PATCH',
            body: JSON.stringify({ note: notes.value })
          });
        } catch (err) {
          console.warn('Failed to save notes', err);
        }
      }, 800);
    });
  }

  // ============================================================
  // Search & Filter
  // ============================================================
  function initializeSearch() {
    searchInput?.addEventListener('input', () => {
      currentSearch = searchInput.value;
      renderTable();
    });
    statusFilter?.addEventListener('change', () => {
      currentFilter = statusFilter.value;
      renderTable();
    });
  }

  // ============================================================
  // Export (placeholder)
  // ============================================================
  document.getElementById('exportInquiriesBtn')?.addEventListener('click', () => {
    showToast('Export feature coming soon');
  });

  // ============================================================
  // Event bindings for drawer action buttons
  // ============================================================
  function bindDrawerActions() {
    document.getElementById('drawerApproveBtn')?.addEventListener('click', () => {
      if (currentInquiryId) approveInquiry(currentInquiryId);
    });
    document.getElementById('drawerQuoteBtn')?.addEventListener('click', () => {
      if (currentInquiryId) openQuoteModal(currentInquiryId);
    });
    document.getElementById('drawerRejectBtn')?.addEventListener('click', () => {
      if (currentInquiryId) openRejectModal(currentInquiryId);
    });
    document.getElementById('drawerWhatsappBtn')?.addEventListener('click', () => {
      if (currentInquiryId) openWhatsApp(currentInquiryId);
    });
    document.getElementById('drawerConvertBtn')?.addEventListener('click', () => {
      if (currentInquiryId) convertInquiry(currentInquiryId);
    });
  }

  // ============================================================
  // Init
  // ============================================================
  function init() {
    initializeDrawer();
    initializeQuoteModal();
    initializeRejectModal();
    initializeNotes();
    initializeSearch();
    bindDrawerActions();
    loadInquiries();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();