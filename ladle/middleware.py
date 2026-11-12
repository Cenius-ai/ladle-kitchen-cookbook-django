"""Security response headers for every response.

The application ships all of its own CSS and JavaScript, so a strict
same-origin Content-Security-Policy works without a nonce: there are no inline
scripts, no inline event handlers and no inline style attributes anywhere in
the templates.
"""

from django.utils.deprecation import MiddlewareMixin

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        "connect-src 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "object-src 'none'",
    ]
)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Attach the baseline hardening headers to every HTML and asset response."""

    def process_response(self, request, response):
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        # The cook-along voice mode needs the microphone; nothing else does.
        response.setdefault(
            "Permissions-Policy", "microphone=(self), camera=(), geolocation=()"
        )
        return response
