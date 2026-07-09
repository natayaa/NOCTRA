================================================================================
                    PRICE LIST MODULE - DOCUMENTATION
================================================================================

📌 OVERVIEW
-----------
Module untuk mengelola daftar harga (Price List) untuk services, materials,
labor, bike models, paint, finish, dan accessories.

📁 STRUKTUR FOLDER
------------------
static/js/pages/price_list/
├── index.js              # Entry point - inisialisasi module
├── config.js             # Konfigurasi & State management
├── dom.js                # DOM References (semua element ID)
├── api.js                # API Services (semua panggilan ke backend)
├── formatters.js         # Formatting functions
├── toast.js              # Toast notification system
├── utils.js              # Utility functions
├── renderers/
│   └── table.js          # Table rendering, stats, category filter
└── handlers/
    ├── actions.js        # CRUD actions & export
    ├── modals.js         # Create/Edit modal handlers
    ├── history.js        # Price history modal
    ├── bulk.js           # Bulk update modal
    └── events.js         # Event bindings & keyboard shortcuts

🔧 DEPENDENCIES
---------------
- API Base URL: /api/api
- Endpoints yang digunakan:
  GET    /price-list/items/                    - List price items
  GET    /price-list/items/{id}               - Detail item
  POST   /price-list/items/                   - Create item
  PATCH  /price-list/items/{id}               - Update item
  DELETE /price-list/items/{id}               - Delete item
  POST   /price-list/items/{id}/toggle        - Toggle active status
  GET    /price-list/items/{id}/price-history - Price history
  POST   /price-list/items/{id}/change-price  - Change price
  GET    /price-list/stats                    - Dashboard stats
  GET    /price-list/categories/with-counts   - Categories with counts
  POST   /price-list/items/bulk-update-prices - Bulk update

🚀 FLOW APLIKASI
----------------
1. User buka halaman → loadPriceItems() dijalankan
2. fetchPriceItems() mengambil data dari API
3. renderItems() menampilkan data di table
4. User bisa:
   - Tambah item → openCreateModal() → submit → loadPriceItems()
   - Edit item → openEditModal(id) → submit → loadPriceItems()
   - Hapus item → confirmDelete(id) → loadPriceItems()
   - Lihat history → openHistoryModal(id)
   - Bulk update → openBulkModal() → submit → loadPriceItems()
   - Export → exportPriceItems()

🔍 DEBUGGING TIPS
-----------------
1. Cek console log untuk tracking:
   - "📡 Fetching price items" - cek parameter yang dikirim
   - "📦 API Response" - cek struktur response
   - "🎨 Rendering items" - cek data sebelum di-render

2. Error yang sering muncul:
   - history.forEach is not a function → API return bukan array, gunakan ensureArray()
   - Category filter tidak update → cek updateCategoryFilter()

3. Cara test cepat:
   - Buka console browser
   - Ketik: window.loadPriceItems() untuk reload data
   - Ketik: window.openCreateModal() untuk buka modal create

📝 CATATAN PENTING
------------------
1. State disimpan di file config.js, akses via state.xxx
2. Semua DOM akses via DOM.xxx() (getter function)
3. Semua API via PriceAPI.xxx()
4. Formatting via Formatter.xxx()
5. Jangan lupa export functions ke window untuk inline onclick

🔄 UPDATE GUIDE
----------------
1. Menambah field baru di price item:
   - Tambah ke state di config.js
   - Tambah ke form di handlers/modals.js
   - Tambah ke renderItems() di renderers/table.js

2. Menambah filter baru:
   - Tambah ke state.filters
   - Tambah ke params di api.js fetchItems()
   - Tambah event listener di handlers/events.js

3. Menambah action baru:
   - Buat handler di handlers/actions.js
   - Tambah button di renderers/table.js
   - Bind event di handlers/events.js

================================================================================