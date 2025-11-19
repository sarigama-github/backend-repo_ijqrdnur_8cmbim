import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from database import db, create_document, get_documents
from schemas import Quote

app = FastAPI(title="Inspiration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Inspiration API is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# -------------------------------
# Inspiration Quotes Endpoints
# -------------------------------

class NewQuote(BaseModel):
    text: str
    author: Optional[str] = None
    mood: Optional[str] = None

@app.post("/api/quotes")
def add_quote(payload: NewQuote):
    try:
        # Validate via Quote schema then insert
        quote = Quote(**payload.model_dump())
        inserted_id = create_document("quote", quote)
        return {"id": inserted_id, "message": "Quote saved"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/quotes")
def list_quotes(mood: Optional[str] = None, limit: int = 20):
    try:
        filter_dict = {"mood": mood} if mood else {}
        docs = get_documents("quote", filter_dict, limit)
        # Convert ObjectId and datetimes to strings
        def clean(doc):
            d = {k: (str(v) if k == "_id" else (v.isoformat() if hasattr(v, 'isoformat') else v)) for k, v in doc.items()}
            return d
        return [clean(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/quotes/random")
def random_quote():
    try:
        # Fetch a small sample and choose one
        docs = get_documents("quote", {}, 50)
        import random
        if not docs:
            # Seed with a few quotes on first call (non-blocking best-effort)
            samples = [
                {"text": "Stay hungry, stay foolish.", "author": "Steve Jobs", "mood": "motivation"},
                {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs", "mood": "work"},
                {"text": "Whether you think you can or you think you can’t, you’re right.", "author": "Henry Ford", "mood": "mindset"},
            ]
            for s in samples:
                try:
                    create_document("quote", s)
                except Exception:
                    pass
            docs = get_documents("quote", {}, 50)
        choice = random.choice(docs)
        choice["_id"] = str(choice.get("_id"))
        for k, v in list(choice.items()):
            if hasattr(v, 'isoformat'):
                choice[k] = v.isoformat()
        return choice
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
