"""GZip compression middleware with ETag support for mobile optimization."""

import hashlib

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class CompressionMiddleware(BaseHTTPMiddleware):
    """Add ETag headers for caching support.

    GZip compression is handled separately via Starlette's GZipMiddleware.
    This middleware adds ETag headers to enable client-side caching.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Skip non-JSON responses and streaming
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Read body for ETag computation (only for buffered responses)
        if hasattr(response, "body"):
            body = response.body
            if body:
                etag = hashlib.md5(body).hexdigest()
                response.headers["ETag"] = f'"{etag}"'

                # Check If-None-Match
                if_none_match = request.headers.get("If-None-Match")
                if if_none_match and if_none_match.strip('"') == etag:
                    return Response(status_code=304, headers={"ETag": f'"{etag}"'})

        return response
