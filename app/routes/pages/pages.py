from fastapi import APIRouter, status, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response


pages = APIRouter(tags=["HTML Pages"])
templates = Jinja2Templates("templates/")

# INDEX HTML
@pages.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    budget_values = ["1000000", "2000000", "3000000", "4000000", "5000000"]
    budget_formatted = []
    for value in budget_values:
        num = int(value)
        if num >= 1000000:
            if num % 1000000 == 0:
                formatted = f"Rp. {num//1000000} Juta"
            else:
                formatted = f"Rp. {num/1000000:.1f} Juta"
        else:
            formatted = f"Rp. {num:,}".replace(",", ".")
        budget_formatted.append({"value": value, "label": formatted})
        
    konteks = {
        "request": request, "page_title": "NOKTRA AUTOWORKS",
        "page_content": "Premium motorcycle restoration, repaint and custom build workshop",
        "target_result": ["OEM Standard", "Custom", "Restorasi"], 
        "estimasi_budget": budget_formatted,
        "motorcycle_data": {
            "Honda": [
                "Astrea Grand", "Supra", "Supra X", "Revo", "Blade", "Beat", 
                "Scoopy", "Genio", "Vario 125", "Vario 160", "PCX 160", "ADV 160", 
                "CB150R", "Verza", "Mega Pro", "Tiger", "CBR 150R", "CBR 250R(RR)", "CRF 150L"
            ],
            "Yamaha": [
                "Mio (Sporty/Smile/Old)", "Mio Soul", "Fino", "Xeon", "Lexi",
                "Aerox", "NMAX", "XMAX", "Jupiter Z", "Jupiter MX", "Vega", 
                "Vixion (Old, New, NVL, Etc)", "Byson", "R15", "R25", "MT-15", "XSR 155"
            ],
            "Suzuki": [
                "Crystal", "Shogun", "Satria 2Tax", "Satria F150 4Tax", "Nex", "Address", 
                "Burgman Street", "GSX 150R", "GSX S150"
            ],
            "Kawasaki": [
                "Kaze", "Athlete", "Ninja 150R/RR", "Ninja 250R (Karbu/FI)",
                "Ninja ZX-25R", "KLX 150", "D-Tracker", "W175", "Versys X250"
            ]
        }
    }
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=konteks,
        status_code=status.HTTP_200_OK
    )

