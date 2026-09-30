from .models import Event


class EventStatusMiddleware:
    """Keep event statuses in line with the clock so ended events close automatically."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        Event.refresh_statuses()
        return self.get_response(request)
