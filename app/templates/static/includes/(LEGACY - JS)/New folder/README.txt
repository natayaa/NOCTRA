================================================================================
                    NOCTRA WORKSHOP MANAGEMENT - MODULES SUMMARY
================================================================================

📊 STATISTIK MODULES
--------------------
Module          | Files | Lines (approx) | Dependencies
----------------|-------|----------------|--------------
inquiries/      | 18    | 1,800+         | API: 14 endpoints
price_list/     | 13    | 1,200+         | API: 11 endpoints
inventories/    | 18    | 1,800+         | API: 12 endpoints
projects/	    | 23	| 2,000+	     | API: 15 endpoints
----------------|-------|----------------|--------------
TOTAL           | 49    | 4,800+         | API: 37 endpoints

📁 STRUKTUR UMUM SEMUA MODULE
------------------------------
setiap module mengikuti pattern yang sama:

module/
├── index.js          # Entry point (export init, load, expose global)
├── config.js         # CONFIG, state
├── dom.js            # DOM references (getter functions)
├── api.js            # API services (XXXAPI object)
├── formatters.js     # Formatter object
├── toast.js          # showToast()
├── utils.js          # Helper functions
├── renderers/        # Rendering functions
│   └── *.js
└── handlers/         # Business logic & event handlers
    └── *.js

🔑 KEY PATTERNS
---------------
1. DOM Access:      DOM.xxx() - getter function, return null if not found
2. State Access:    state.xxx - direct access
3. API Calls:       XXXAPI.xxx() - semua async, return data
4. Formatting:      Formatter.xxx() - currency, date, status
5. Toast:           showToast(msg, type, duration)
6. Export to Global: window.xxx = xxx - untuk inline onclick

🚀 INITIALIZATION
-----------------
Setiap module memiliki init function yang dipanggil dari HTML:

```html
<script type="module">
    import { initInquiries } from "/static/js/pages/inquiries/index.js";
    initInquiries();
</script>