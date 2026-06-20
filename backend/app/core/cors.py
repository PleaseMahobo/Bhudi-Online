from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app):

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "https://bhudi.online",
            "https://www.bhudi.online",
            "https://*.vercel.app"
        ],
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )