from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView

urlpatterns = (
    [
        path("", RedirectView.as_view(url=reverse_lazy("admin:login"), permanent=False)),
        path("api/currencies/", include("currencies_api.urls")),
        path("actions/currencies/", include("currencies.urls")),
        path("admin/", admin.site.urls),
    ]
    + debug_toolbar_urls()
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)
