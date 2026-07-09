================================================================================
                    PROJECTS MODULE - DOCUMENTATION
================================================================================

📌 OVERVIEW
-----------
Module untuk mengelola Projects (proyek workshop) dari mulai pembuatan,
tracking progress, manajemen tasks, labor, material usage, hingga completion.

📁 STRUKTUR FOLDER
------------------
static/js/pages/projects/
├── index.js              # Entry point - inisialisasi module (100+ baris)
├── config.js             # Konfigurasi & State management (50+ baris)
├── dom.js                # DOM References - semua element ID (200+ baris)
├── api.js                # API Services - semua panggilan ke backend (250+ baris)
├── formatters.js         # Formatting functions (currency, date, status) (100+ baris)
├── toast.js              # Toast notification system (30+ baris)
├── utils.js              # Utility functions (helper) (50+ baris)
├── drawer.js             # Drawer functions (open, close, switch tabs) (100+ baris)
├── renderers/
│   ├── cards.js          # Project cards rendering & pagination (150+ baris)
│   ├── dashboard.js      # Dashboard stats rendering (50+ baris)
│   └── detail/
│       ├── overview.js   # Overview tab - customer, vehicle, status (80+ baris)
│       ├── materials.js  # Materials tab - consumed materials (60+ baris)
│       ├── labor.js      # Labor tab - labor entries (60+ baris)
│       ├── timeline.js   # Timeline tab - dates, milestones, activities (90+ baris)
│       └── tasks.js      # Tasks tab - task list & status (50+ baris)
└── handlers/
    ├── actions.js        # CRUD actions (delete, confirm) (40+ baris)
    ├── modals.js         # Modal handlers (create, edit, submit) (120+ baris)
    ├── progress.js       # Progress popup - slider, milestones (100+ baris)
    ├── tasks.js          # Task management - add, complete (80+ baris)
    ├── materials.js      # Material consumption - consume, delete (70+ baris)
    ├── labor.js          # Labor management - add, delete (70+ baris)
    ├── dropdowns.js      # Dropdown loaders - materials, labor types (120+ baris)
    └── events.js         # Event bindings & keyboard shortcuts (150+ baris)

🔧 DEPENDENCIES
---------------
- API Base URL: /api/api
- Endpoints yang digunakan:

  Projects:
  GET    /projects/                           - List projects (with filters)
  GET    /projects/statistics                 - Dashboard statistics
  GET    /projects/{id}                      - Detail project
  POST   /projects/                           - Create project
  PATCH  /projects/{id}                      - Update project
  DELETE /projects/{id}                      - Delete project
  PATCH  /projects/{id}/progress             - Update progress
  POST   /projects/{id}/complete             - Complete project

  Tasks:
  GET    /projects/{id}/tasks                - List tasks
  POST   /projects/{id}/tasks                - Add task
  POST   /projects/tasks/{id}/complete       - Complete task

  Labor:
  GET    /projects/{id}/labor                - List labor entries
  POST   /projects/{id}/labor                - Add labor entry
  DELETE /projects/labor/{id}                - Delete labor entry

  Materials:
  POST   /inventory/usage                    - Consume material
  DELETE /inventory/usage/{id}               - Delete material usage

  Dropdowns:
  GET    /inventory/items                    - Inventory items (for materials)
  GET    /price-list/items                   - Price list items (for labor types)
  GET    /inventory/items/{id}               - Check inventory item

🚀 FLOW APLIKASI
----------------
1. User buka halaman → initProjects() dijalankan
2. bindEvents() & bindKeyboardShortcuts() dipanggil
3. loadProjects() mengambil data dari API
4. renderProjects() menampilkan data di card grid
5. updateDashboard() menampilkan statistik
6. loadMaterialItems() & loadLaborTypes() untuk dropdown di drawer

7. User klik card → openProjectDrawer(id)
8. loadInquiryDetail() mengambil semua data terkait
9. Render semua tab:
   - Overview: customer, vehicle, status, progress
   - Materials: consumed materials with delete
   - Labor: labor entries with delete
   - Timeline: dates, milestones, activities
   - Tasks: task list with complete button

10. User bisa:
    - Update progress → openProgressPopup() → slider → save
    - Add task → openTaskModal() → submit
    - Complete task → handleCompleteTask()
    - Consume material → select material → quantity → consume
    - Add labor → select type → hours → rate → add
    - Delete material/labor → confirm → delete
    - Edit project → openEditProjectModal() → update
    - Delete project → confirmDeleteProject()

🔍 DEBUGGING TIPS
-----------------
1. Cek console log untuk tracking:
   - "🚀 Initializing Projects page..." - start
   - "📊 Dashboard updated:" - stats
   - "📦 Loaded inventory items:" - materials dropdown
   - "👷 Loaded labor items:" - labor dropdown

2. Error yang sering muncul:
   - cards.js / dashboard.js 404 → cek path import di index.js
   - drawerBackdrop not exported → tambahkan di dom.js
   - getStatusBadgeClass not found → tambahkan di formatters.js
   - openCreateProjectModal is not defined → cek import di index.js

3. Cara test cepat:
   - Buka console browser
   - Ketik: window.loadProjects() untuk reload data
   - Ketik: window.openProjectDrawer('{id}') untuk buka drawer

4. Cek struktur data:
   - project.status: draft, active, in_progress, on_hold, completed, cancelled
   - project.priority: low, medium, high, urgent
   - project.progress: 0-100

📝 CATATAN PENTING
------------------
1. State disimpan di file config.js, akses via state.xxx
2. Semua DOM akses via DOM.xxx() (getter function)
3. Semua API via ProjectAPI.xxx()
4. Formatting via Formatter.xxx()
5. Jangan lupa export functions ke window untuk inline onclick

6. Tab structure:
   - overview: customer, vehicle, status, priority, progress, notes
   - materials: consumed materials with delete button
   - labor: labor entries with delete button
   - timeline: dates, milestones, activities
   - tasks: tasks with complete button

7. Progress milestones:
   - 25% - Initial Phase
   - 50% - Midway
   - 75% - Almost Done
   - 100% - Complete

🔄 UPDATE GUIDE
----------------
1. Menambah field baru di project:
   - Tambah ke state di config.js
   - Tambah ke form di handlers/modals.js (create & edit)
   - Tambah ke renderers/detail/overview.js (display)
   - Tambah ke api.js jika perlu

2. Menambah tab baru di drawer:
   - Buat file renderers/detail/newtab.js
   - Tambah HTML tab di projects.html
   - Tambah tab panel di DOM.tabPanels (dom.js)
   - Import di drawer.js
   - Panggil render di openProjectDrawer()

3. Menambah filter baru:
   - Tambah ke state.filters
   - Tambah ke params di api.js fetchProjects()
   - Tambah event listener di handlers/events.js

4. Menambah action baru:
   - Buat handler di handlers/ yang sesuai
   - Tambah button di renderers yang sesuai
   - Bind event di handlers/events.js
   - Export ke window di index.js

5. Fix dropdowns (materials / labor):
   - Cek fetchInventoryItems() dan fetchPriceListItems() di api.js
   - Pastikan response data structure sesuai
   - Cek loadMaterialItems() dan loadLaborTypes() di handlers/dropdowns.js

🔧 COMMON ISSUES & SOLUTIONS
----------------------------
1. "cards.js 404 Not Found"
   → Pastikan path di import index.js: './renderers/cards.js'

2. "drawerBackdrop is not defined"
   → Tambahkan di dom.js: export const drawerBackdrop = document.createElement('div')...

3. "getStatusBadgeClass is not defined"
   → Tambahkan di formatters.js: export function getStatusBadgeClass(status) {...}

4. "openCreateProjectModal is not defined"
   → Pastikan di-import di index.js dan di-export ke window

5. "Progress slider not updating milestones"
   → Cek event listener di progressPopupSlider di handlers/events.js

6. "Material dropdown not showing inventory items"
   → Cek fetchInventoryItems() response structure di api.js

7. "Labor dropdown not showing labor types"
   → Cek fetchPriceListItems() response structure di api.js

8. "Delete material/labor not working"
   → Cek handleDeleteMaterial() dan handleDeleteLabor() di handlers/

📊 STATUS COLOR GUIDE
--------------------
| Status       | Color      | Badge Class |
|--------------|------------|-------------|
| Draft        | ⚫ Gray    | .draft      |
| Active       | 🔵 Blue    | .active     |
| In Progress  | 🟡 Yellow  | .in_progress|
| On Hold      | ⚫ Gray    | .on_hold    |
| Completed    | 🟢 Green   | .completed  |
| Cancelled    | 🔴 Red     | .cancelled  |

📊 PRIORITY COLOR GUIDE
-----------------------
| Priority     | Color      | Badge Class |
|--------------|------------|-------------|
| Low          | ⚫ Gray    | .low        |
| Medium       | 🔵 Blue    | .medium     |
| High         | 🟡 Yellow  | .high       |
| Urgent       | 🔴 Red     | .urgent     |

⌨️ KEYBOARD SHORTCUTS
---------------------
| Shortcut    | Action                          |
|-------------|---------------------------------|
| Esc         | Close modal / drawer / popup    |
| Ctrl+N      | Create new project              |
| Ctrl+F      | Focus search                    |

📂 FILE LOCATIONS
-----------------
| Module      | Path                                      |
|-------------|-------------------------------------------|
| Projects JS | /static/js/pages/projects/                |
| Projects CSS| /static/includes/css/pages/projects.css   |
| Projects HTML| /templates/pages/projects.html           |

🔍 API BASE URL
---------------
/api/api

================================================================================