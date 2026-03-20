import threading

_thread_locals = threading.local()

def get_current_request():
    """Retrieve current request from thread local storage."""
    return getattr(_thread_locals, 'request', None)

class AuditLogContextMiddleware:
    """Middleware to catch request and store it in thread local for audit signals."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request
        return response
