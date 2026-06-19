// price_list.js – Full CRUD with Pagination
(function() {
  'use strict';

  // DOM refs
  const tbody = document.getElementById('priceTableBody');
  const searchInput = document.getElementById('searchPrice');
  const categoryFilter = document.getElementById('categoryFilter');
  const addBtn = document.getElementById('addPriceBtn');

  const modal = document.getElementById('priceModal');
  const modalTitle = document.getElementById('modalTitle');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const cancelModalBtn = document.getElementById('cancelModalBtn');
  const form = document.getElementById('priceForm');
  const editId = document.getElementById('editId');
  const category = document.getElementById('category');
  const name = document.getElementById('name');
  const description = document.getElementById('description');
  const price = document.getElementById('price');
  const unit = document.getElementById('unit');
  const vehicleBrand = document.getElementById('vehicleBrand');
  const vehicleModel = document.getElementById('vehicleModel');
  const effectiveDate = document.getElementById('effectiveDate');
  const isActive = document.getElementById('isActive');
  const submitBtn = document.getElementById('submitBtn');

  // Pagination refs
  const prevPageBtn = document.getElementById('prevPageBtn');
  const nextPageBtn = document.getElementById('nextPageBtn');
  const pageInfo = document.getElementById('pageInfo');

  let priceData = [];
  let isSubmitting = false;
  let currentPage = 1;
  let totalPages = 1;
  const limit = 10;

  // Helpers
  function formatCurrency(val) {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(val || 0);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>]/g, function(m) {
      if (m === '&') return '&amp;';
      if (m === '<') return '&lt;';
      if (m === '>') return '&gt;';
      return m;
    });
  }

  function showToast(msg, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) {
      const c = document.createElement('div');
      c.id = 'toastContainer';
      c.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;display:flex;flex-direction:column;gap:8px;max-width:400px;';
      document.body.appendChild(c);
      return showToast(msg, type);
    }
    const toast = document.createElement('div');
    toast.style.cssText = `
      padding:12px 18px; border-radius:12px;
      background:${type === 'error' ? '#7f1d1d' : '#111827'};
      color:#fff; border:1px solid rgba(255,255,255,0.08);
      box-shadow:0 15px 40px rgba(0,0,0,0.3);
      transform:translateX(100%); opacity:0;
      transition:all 0.3s ease;
    `;
    toast.textContent = msg;
    container.appendChild(toast);
    requestAnimationFrame(() => { toast.style.transform = 'translateX(0)'; toast.style.opacity = '1'; });
    setTimeout(() => {
      toast.style.transform = 'translateX(100%)';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // API
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

  // Load data with pagination
  async function loadPriceList(page = 1) {
    currentPage = page;
    const search = searchInput.value.trim();
    const category = categoryFilter.value;

    let url = `/api/price-list/?page=${page}&limit=${limit}&active_only=true`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    tbody.innerHTML = '<tr><td colspan="8" class="loading-placeholder">Loading...</td></tr>';
    try {
      const data = await fetchJSON(url);
      priceData = data.data || [];
      totalPages = Math.ceil((data.total || 0) / limit);
      renderTable(priceData);
      updatePagination();
    } catch (err) {
      console.error(err);
      showToast('Failed to load price list', 'error');
      tbody.innerHTML = '<tr><td colspan="8" class="loading-placeholder">Error loading</td></tr>';
    }
  }

  function renderTable(items) {
    if (!items || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="loading-placeholder">No price items found</td></tr>';
      return;
    }
    tbody.innerHTML = items.map(item => `
      <tr>
        <td><span class="badge category-${item.category}">${escapeHtml(item.category)}</span></td>
        <td><strong>${escapeHtml(item.name)}</strong></td>
        <td>${escapeHtml(item.description || '-')}</td>
        <td>${formatCurrency(item.price)}</td>
        <td>${escapeHtml(item.unit || '-')}</td>
        <td>${item.vehicle_brand ? escapeHtml(item.vehicle_brand) + ' ' + escapeHtml(item.vehicle_model || '') : '-'}</td>
        <td><span class="status-badge ${item.is_active ? 'active' : 'inactive'}">${item.is_active ? 'Active' : 'Inactive'}</span></td>
        <td>
          <button class="action-btn edit-btn" data-id="${item.id}"><i class="ph ph-pencil"></i></button>
          <button class="action-btn delete-btn" data-id="${item.id}"><i class="ph ph-trash"></i></button>
        </td>
      </tr>
    `).join('');

    document.querySelectorAll('.edit-btn').forEach(btn => {
      btn.addEventListener('click', () => openEditModal(btn.dataset.id));
    });
    document.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteItem(btn.dataset.id));
    });
  }

  function updatePagination() {
    pageInfo.textContent = `Page ${currentPage} of ${totalPages || 1}`;
    prevPageBtn.disabled = currentPage <= 1;
    nextPageBtn.disabled = currentPage >= totalPages;
  }

  // Filters
  function applyFilters() {
    loadPriceList(1);  // reset to first page on filter change
  }

  // Modal
  function openModal(editMode = false, item = null) {
    if (editMode && item) {
      modalTitle.textContent = 'Edit Price Item';
      editId.value = item.id;
      category.value = item.category || '';
      name.value = item.name || '';
      description.value = item.description || '';
      price.value = item.price || '';
      unit.value = item.unit || '';
      vehicleBrand.value = item.vehicle_brand || '';
      vehicleModel.value = item.vehicle_model || '';
      effectiveDate.value = item.effective_date || '';
      isActive.checked = item.is_active !== undefined ? item.is_active : true;
      submitBtn.textContent = 'Update';
    } else {
      modalTitle.textContent = 'Add Price Item';
      editId.value = '';
      form.reset();
      isActive.checked = true;
      effectiveDate.value = new Date().toISOString().split('T')[0];
      submitBtn.textContent = 'Save';
    }
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }

  async function openEditModal(id) {
    try {
      const data = await fetchJSON(`/api/price-list/${id}`);
      openModal(true, data.data);
    } catch (err) {
      showToast('Failed to load price item', 'error');
    }
  }

  async function deleteItem(id) {
    if (!confirm('Delete this price item permanently?')) return;
    try {
      await fetchJSON(`/api/price-list/${id}`, { method: 'DELETE' });
      showToast('Item deleted');
      loadPriceList(currentPage);
    } catch (err) {
      showToast('Delete failed', 'error');
    }
  }

  // Form submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (isSubmitting) return;
    isSubmitting = true;

    const id = editId.value;
    const payload = {
      category: category.value,
      name: name.value.trim(),
      description: description.value.trim(),
      price: parseFloat(price.value) || 0,
      unit: unit.value.trim(),
      vehicle_brand: vehicleBrand.value.trim(),
      vehicle_model: vehicleModel.value.trim(),
      effective_date: effectiveDate.value || new Date().toISOString().split('T')[0],
      is_active: isActive.checked
    };

    try {
      let url = '/api/price-list/';
      let method = 'POST';
      if (id) {
        url = `/api/price-list/${id}`;
        method = 'PUT';
      }
      await fetchJSON(url, { method, body: JSON.stringify(payload) });
      showToast(id ? 'Item updated' : 'Item created');
      closeModal();
      loadPriceList(currentPage);
    } catch (err) {
      console.error(err);
      showToast(err.message || 'Save failed', 'error');
    } finally {
      isSubmitting = false;
    }
  });

  // Event listeners
  searchInput.addEventListener('input', applyFilters);
  categoryFilter.addEventListener('change', applyFilters);
  addBtn.addEventListener('click', () => openModal(false));
  closeModalBtn.addEventListener('click', closeModal);
  cancelModalBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

  // Pagination buttons
  prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) loadPriceList(currentPage - 1);
  });
  nextPageBtn.addEventListener('click', () => {
    if (currentPage < totalPages) loadPriceList(currentPage + 1);
  });

  // Init
  document.addEventListener('DOMContentLoaded', () => loadPriceList(1));
})();