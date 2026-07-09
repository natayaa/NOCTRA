================================================================================
                    INVENTORIES MODULE - DOCUMENTATION
================================================================================

📌 OVERVIEW
-----------
Module untuk mengelola Inventory (persediaan) workshop termasuk materials,
parts, tools, dan chemicals dengan tracking stock, movements, dan alerts.

📁 STRUKTUR FOLDER
------------------
static/js/pages/inventories/
├── index.js              # Entry point - inisialisasi module
├── config.js             # Konfigurasi & State management
├── dom.js                # DOM References (semua element ID)
├── api.js                # API Services (semua panggilan ke backend)
├── formatters.js         # Formatting functions
├── toast.js              # Toast notification system
├── utils.js              # Utility functions
├── renderers/
│   ├── table.js          # Table rendering & pagination
│   ├── alerts.js         # Stock alerts rendering
│   ├── categories.js     # Categories rendering
│   ├── movements.js      # Recent movements rendering
│   └── detail.js         # Detail panel rendering
└── handlers/
    ├── actions.js        # CRUD actions & export
    ├── modals.js         # Create/Edit modal handlers
    ├── stock.js          # Stock adjustment
    ├── history.js        # Movement history
    ├── reorder.js        # Reorder / Purchase order
    └── events.js         # Event bindings & keyboard shortcuts

🔧 DEPENDENCIES
---------------
- API Base URL: /api/api
- Endpoints yang digunakan:
  GET    /inventory/items/                    - List items
  GET    /inventory/items/{id}               - Detail item
  POST   /inventory/items/                   - Create item
  PATCH  /inventory/items/{id}               - Update item
  DELETE /inventory/items/{id}               - Delete item
  POST   /inventory/stock/adjust             - Adjust stock
  GET    /inventory/alerts                   - Stock alerts
  GET    /inventory/movements/recent         - Recent movements
  GET    /inventory/movements/item/{id}      - Item movements history
  GET    /inventory/statistics               - Dashboard stats
  GET    /inventory/categories               - Categories
  GET    /inventory/suppliers                - Suppliers
  POST   /inventory/purchase-orders/         - Create purchase order

🚀 FLOW APLIKASI
----------------
1. User buka halaman → loadInventoryItems() dijalankan
2. fetchItems() mengambil data dari API
3. renderItems() menampilkan data di table
4. Sidebar menampilkan:
   - Categories (click untuk filter)
   - Recent movements
5. User klik row → selectItem(id) → renderDetailPanel()
6. User bisa:
   - Tambah item → openCreateModal() → submit → loadInventoryItems()
   - Edit item → openEditModal(id) → submit → loadInventoryItems()
   - Hapus item → confirmDelete(id) → loadInventoryItems()
   - Adjust stock → openStockAdjustModal(id) → submit
   - Lihat history → openHistoryModal(id)
   - Reorder → openReorderModal(id) → submit

🔍 DEBUGGING TIPS
-----------------
1. Cek console log untuk tracking:
   - "📡 Fetching inventory" - cek parameter
   - "📦 API Response" - cek struktur response
   - "🎨 Rendering inventory items" - cek data

2. Error yang sering muncul:
   - Recent movements show ID bukan nama → cek enrichment di fetchRecentMovements()
   - Detail panel kosong → cek fetchItemDetail()
   - Stock adjust gagal → cek parameter yang dikirim

3. Cara test cepat:
   - Buka console browser
   - Ketik: window.loadInventoryItems() untuk reload data
   - Ketik: window.selectItem('{id}') untuk pilih item

📝 CATATAN PENTING
------------------
1. State disimpan di file config.js, akses via state.xxx
2. Semua DOM akses via DOM.xxx() (getter function)
3. Semua API via InventoryAPI.xxx()
4. Formatting via Formatter.xxx()
5. Jangan lupa export functions ke window untuk inline onclick
6. Recent movements di-enrich dengan item name dari state.items

🔄 UPDATE GUIDE
----------------
1. Menambah field baru di inventory item:
   - Tambah ke state di config.js
   - Tambah ke form di handlers/modals.js
   - Tambah ke renderItems() di renderers/table.js
   - Tambah ke renderDetailPanel() di renderers/detail.js

2. Menambah filter baru:
   - Tambah ke state.filters
   - Tambah ke params di api.js fetchItems()
   - Tambah event listener di handlers/events.js

3. Menambah action baru:
   - Buat handler di handlers/ yang sesuai
   - Tambah button di renderers/ yang sesuai
   - Bind event di handlers/events.js

4. Fix recent movements item name:
   - Cek fetchRecentMovements() di api.js
   - Pastikan state.items sudah di-load sebelum movements
   - Enrich dengan item name dari state

================================================================================