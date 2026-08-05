================================================================================
                    INQUIRIES MODULE - DOCUMENTATION
================================================================================

📌 OVERVIEW
-----------
Module untuk mengelola Customer Inquiries (permintaan pelanggan) dari awal
masuk hingga dikonversi menjadi Project.

📁 STRUKTUR FOLDER
------------------
static/js/pages/inquiries/
├── index.js              # Entry point - inisialisasi module
├── config.js             # Konfigurasi & State management
├── dom.js                # DOM References (semua element ID)
├── api.js                # API Services (semua panggilan ke backend)
├── formatters.js         # Formatting functions (currency, date, status)
├── utils.js              # Utility functions (helper)
├── toast.js              # Toast notification system
├── drawer.js             # Drawer functions (open, close, load detail)
├── renderers/
│   ├── table.js          # Table rendering & pagination
│   ├── customer.js       # Customer info rendering di drawer
│   ├── vehicle.js        # Vehicle & project info rendering
│   ├── financial.js      # Financial summary rendering
│   ├── labor.js          # Labor items rendering
│   ├── materials.js      # Material usage rendering
│   ├── payments.js       # Payment summary & history rendering
│   ├── timeline.js       # Activity timeline rendering
│   ├── notes.js          # Internal notes rendering
│   ├── carousel.js       # Before/After photos & Lightbox
│   └── drawer-actions.js # Drawer action buttons (Approve, Quote, etc)
└── handlers/
    ├── actions.js        # Action handlers (Approve, Reject, WhatsApp, Notes)
    ├── modals.js         # Modal handlers (Convert, Quote, Reject)
    └── events.js         # Event bindings & keyboard shortcuts

🔧 DEPENDENCIES
---------------
- API Base URL: /api/api
- Endpoints yang digunakan:
  GET    /inquiries/                          - List inquiries
  GET    /inquiries/statistics                - Dashboard stats
  GET    /inquiries/{id}                     - Detail inquiry
  PATCH  /inquiries/{id}/status              - Update status
  POST   /inquiries/{id}/quote               - Send quotation
  POST   /inquiries/{id}/reject              - Reject inquiry
  POST   /projects/from-inquiry/{id}         - Convert to project
  GET    /inquiries/{id}/activities          - Activity timeline
  GET    /inquiries/{id}/notes               - Internal notes
  POST   /inquiries/{id}/notes               - Add note
  GET    /inquiries/{id}/photos              - Photos
  GET    /payments/inquiry/{id}              - Payments list
  GET    /projects/{id}/labor                - Labor items
  GET    /inventory/usage/project/{id}       - Material usage

🚀 FLOW APLIKASI
----------------
1. User buka halaman → loadInquiries() dijalankan
2. fetchInquiries() mengambil data dari API
3. renderInquiries() menampilkan data di table
4. User klik "View" → openInquiryDrawer(id)
5. loadInquiryDetail() mengambil semua data terkait
6. Render semua section di drawer
7. User bisa melakukan actions (Approve, Quote, Reject, Convert)

🔍 DEBUGGING TIPS
-----------------
1. Cek console log untuk tracking:
   - "📡 Fetching inventory items" - cek response API
   - "📦 Loaded inventory items" - cek data yang diterima
   - "🎨 Rendering payments" - cek data sebelum di-render
   - "📊 Calculated financial data" - cek hasil perhitungan

2. Error yang sering muncul:
   - Element not found → cek ID di DOM dengan DOM.xxx()
   - API 422 error → cek parameter yang dikirim
   - Data tidak muncul → cek struktur response API

3. Cara test cepat:
   - Buka console browser
   - Ketik: window.loadInquiries() untuk reload data
   - Ketik: window.openInquiryDrawer('{id}') untuk buka drawer

📝 CATATAN PENTING
------------------
1. State disimpan di file config.js, akses via state.xxx
2. Semua DOM akses via DOM.xxx() (getter function)
3. Semua API via InquiryAPI.xxx()
4. Formatting via Formatter.xxx()
5. Jangan lupa export functions ke window untuk inline onclick

🔄 UPDATE GUIDE
----------------
1. Menambah field baru di inquiry:
   - Tambah ke state di config.js
   - Tambah ke renderer yang sesuai
   - Tambah ke form jika perlu

2. Menambah action baru:
   - Buat handler di handlers/actions.js
   - Tambah button di renderers/drawer-actions.js
   - Bind event di handlers/events.js

3. Menambah API endpoint:
   - Tambah method di api.js (InquiryAPI)
   - Gunakan di handler yang sesuai

================================================================================