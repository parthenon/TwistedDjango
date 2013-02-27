from django.conf.urls.defaults import patterns, url

from views import ajax_get_session_id

urlpatterns = patterns(
    '',
    url(r'^session_id$', ajax_get_session_id, name="ajax_get_session_id"),
)
