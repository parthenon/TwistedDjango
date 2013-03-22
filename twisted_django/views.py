from django.http import HttpResponse


def ajax_get_session_id(request):
    return HttpResponse(str(request.session.session_key))
