from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "backend is alive"}

@app.get("/health")
def health():
    return {"status": "healthy"}