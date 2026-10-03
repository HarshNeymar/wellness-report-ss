# Entry point for Vercel: it runs the FastAPI app from app/main.py as a serverless function.
#
# vercel.json rewrites every request to /api/index and Vercel hands the app that rewritten
# path, so every route would 404. The rewrite passes the real path in ?__path=..., and this
# middleware puts it back before FastAPI routes the request.
from urllib.parse import parse_qsl, urlencode

from app.main import app


class RestoreOriginalPath:
    def __init__(self, asgi_app):
        self.app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            params = parse_qsl(scope["query_string"].decode("latin-1"), keep_blank_values=True)
            original = [v for k, v in params if k == "__path"]
            if original:
                path = "/" + original[0].lstrip("/")
                rest = urlencode([(k, v) for k, v in params if k != "__path"])
                scope = {**scope, "path": path, "raw_path": path.encode(), "query_string": rest.encode()}
        await self.app(scope, receive, send)


app.add_middleware(RestoreOriginalPath)
