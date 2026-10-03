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
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # TEMPORARY diagnostic: shows what Vercel handed the app. Remove once routing works.
        seen = (f"path={scope['path']!r} root_path={scope.get('root_path', '')!r} "
                f"query={scope['query_string'][:200].decode('latin-1')!r}")

        params = parse_qsl(scope["query_string"].decode("latin-1"), keep_blank_values=True)
        original = [v for k, v in params if k == "__path"]
        if original:
            path = "/" + original[0].lstrip("/")
            rest = urlencode([(k, v) for k, v in params if k != "__path"])
            scope = {**scope, "path": path, "raw_path": path.encode(), "query_string": rest.encode()}

        async def send_with_debug(message):
            if message["type"] == "http.response.start":
                headers = [*message.get("headers", []), (b"x-debug-seen", seen.encode("latin-1", "replace"))]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_debug)


app.add_middleware(RestoreOriginalPath)
