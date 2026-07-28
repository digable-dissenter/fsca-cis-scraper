import math
import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from fsca_scraper.database import get_engine, get_session, Fsp, FspRepresentative, FspKeyIndividual, FspApprovedProduct
from fsca_scraper.experience import validate_experience, ADVICE, INTERMEDIARY

app = FastAPI(title="FSCA Registry Analytics & Geolocator")

# Setup templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Path to database files
GEO_DB_PATH = Path("postalcodes_geo.db")
FSCA_DB_PATH = Path("data/fsca_cis.db")


def get_postal_coordinates(postal_code: str) -> Optional[dict]:
    """Retrieve latitude/longitude coordinates for a SA postal code from the geo database."""
    if not GEO_DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(GEO_DB_PATH))
        cursor = conn.cursor()
        # Pad code to 4 digits
        padded = postal_code.zfill(4)
        row = cursor.execute(
            "SELECT latitude, longitude, suburb, area, province FROM postalcodes WHERE str_code = ? OR box_code = ? LIMIT 1",
            (padded, padded)
        ).fetchone()
        conn.close()
        if row:
            return {
                "latitude": row[0],
                "longitude": row[1],
                "suburb": row[2],
                "area": row[3],
                "province": row[4]
            }
    except Exception:
        pass
    return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula to compute distance in km between two coordinate points."""
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def evaluate_fsp_compliance(fsp: Fsp, ki_exp: int = 12, rep_exp: int = 12) -> dict:
    """Evaluate Compliance (Pass/Fail status) for FSP key individuals and representatives."""
    is_compliant = True
    fails = []
    
    # Check Approved Products against 12 months minimum experience
    for prod in fsp.approved_products:
        has_advice = prod.advice_automated or prod.advice_non_automated
        has_intermediary = prod.intermediary_scripted or prod.intermediary_other
        if not has_advice and not has_intermediary:
            has_advice = has_intermediary = True
            
        if has_advice:
            ok, req = validate_experience(prod.category, prod.product_name, ADVICE, rep_exp)
            if not ok:
                is_compliant = False
                fails.append(f"Product {prod.product_name} (Advice) requires {req}m (actual: {rep_exp}m)")
        if has_intermediary:
            ok, req = validate_experience(prod.category, prod.product_name, INTERMEDIARY, rep_exp)
            if not ok:
                is_compliant = False
                fails.append(f"Product {prod.product_name} (Intermediary) requires {req}m (actual: {rep_exp}m)")
                
    # Check Key Individuals
    for ki in fsp.key_individuals:
        if ki.cobs:
            for cob in ki.cobs:
                req = 12
                if ki_exp < req:
                    is_compliant = False
                    fails.append(f"KI {ki.full_names} {ki.surname} COB {cob.cob_description} requires {req}m (actual: {ki_exp}m)")
                    
    # Check Representatives
    for rep in fsp.representatives:
        for rp in rep.products:
            if rp.advice:
                ok, req = validate_experience(rp.category or "", rp.product_name, ADVICE, rep_exp)
                if not ok:
                    is_compliant = False
                    fails.append(f"Rep {rep.full_names} product {rp.product_name} (Advice) requires {req}m (actual: {rep_exp}m)")
            if rp.intermediary_scripted or rp.intermediary_other:
                ok, req = validate_experience(rp.category or "", rp.product_name, INTERMEDIARY, rep_exp)
                if not ok:
                    is_compliant = False
                    fails.append(f"Rep {rep.full_names} product {rp.product_name} (Intermediary) requires {req}m (actual: {rep_exp}m)")

    return {
        "status": "PASS" if is_compliant else "FAIL",
        "failures": fails
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the interactive single-page dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/stats")
async def stats():
    """Retrieve compliance counts and system stats."""
    engine = get_engine()
    session = get_session(engine)
    try:
        fsps = session.query(Fsp).all()
        total_fsps = len(fsps)
        total_reps = session.query(FspRepresentative).count()
        total_kis = session.query(FspKeyIndividual).count()
        
        pass_count = 0
        fail_count = 0
        for f in fsps:
            comp = evaluate_fsp_compliance(f)
            if comp["status"] == "PASS":
                pass_count += 1
            else:
                fail_count += 1
                
        return {
            "total_fsps": total_fsps,
            "total_reps": total_reps,
            "total_kis": total_kis,
            "compliant_fsps": pass_count,
            "non_compliant_fsps": fail_count,
        }
    finally:
        session.close()


@app.get("/api/fsps")
async def get_fsps(
    query: Optional[str] = None,
    postal_code: Optional[str] = None,
    status: Optional[str] = None,
    ki_exp: int = 12,
    rep_exp: int = 12
):
    """Query list of FSPs with filters and experience settings."""
    engine = get_engine()
    session = get_session(engine)
    try:
        q = session.query(Fsp)
        if query:
            q = q.filter(Fsp.name.ilike(f"%{query}%") | Fsp.fsp_no.ilike(f"%{query}%"))
        if postal_code:
            q = q.filter(Fsp.postal_code == postal_code.zfill(4))
            
        results = []
        for f in q.all():
            compliance = evaluate_fsp_compliance(f, ki_exp=ki_exp, rep_exp=rep_exp)
            if status and compliance["status"] != status:
                continue
                
            coords = get_postal_coordinates(f.postal_code) if f.postal_code else None
            
            results.append({
                "fsp_no": f.fsp_no,
                "name": f.name,
                "trading_name": f.trading_name,
                "fsp_type": f.fsp_type,
                "status": f.status,
                "address_line_1": f.address_line_1,
                "address_line_2": f.address_line_2,
                "postal_code": f.postal_code,
                "compliance": compliance,
                "coordinates": coords
            })
        return results
    finally:
        session.close()


@app.get("/api/geolocate")
async def geolocate(
    latitude: float,
    longitude: float,
    radius: float = Query(default=10.0, description="Search radius in kilometers"),
    ki_exp: int = 12,
    rep_exp: int = 12
):
    """Geolocate FSPs within a radius (km) of specified latitude/longitude coordinates."""
    engine = get_engine()
    session = get_session(engine)
    try:
        fsps = session.query(Fsp).all()
        nearby = []
        
        for f in fsps:
            if not f.postal_code:
                continue
            coords = get_postal_coordinates(f.postal_code)
            if not coords:
                continue
                
            dist = calculate_distance(latitude, longitude, coords["latitude"], coords["longitude"])
            if dist <= radius:
                compliance = evaluate_fsp_compliance(f, ki_exp=ki_exp, rep_exp=rep_exp)
                nearby.append({
                    "fsp_no": f.fsp_no,
                    "name": f.name,
                    "trading_name": f.trading_name,
                    "fsp_type": f.fsp_type,
                    "address_line_1": f.address_line_1,
                    "address_line_2": f.address_line_2,
                    "postal_code": f.postal_code,
                    "distance_km": round(dist, 2),
                    "compliance": compliance,
                    "coordinates": coords
                })
        # Sort by closest distance
        nearby.sort(key=lambda x: x["distance_km"])
        return nearby
    finally:
        session.close()
