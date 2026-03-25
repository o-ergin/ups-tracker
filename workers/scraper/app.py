from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ups_scraper import scrape_ups_tracking

app = FastAPI(title="UPS Scrapling Worker")


class TrackRequest(BaseModel):
    tracking_number: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/track")
def track(req: TrackRequest):
    tracking_number = req.tracking_number.strip()

    if not tracking_number:
        raise HTTPException(status_code=400, detail="tracking_number is required")

    try:
        result = scrape_ups_tracking(tracking_number)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))