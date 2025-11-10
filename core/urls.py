from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from .views import doc_admin_view, doc_customer_view, doc_staff_view

urlpatterns = [
    path('docs/admin', doc_admin_view, name='doc'),
    path('docs/customer', doc_customer_view, name='doc'),
    path('docs/staff', doc_staff_view, name='doc'),
    path('api/v5/', include('orders.urls'))
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('api/v1/', include('panel.urls')),
    path('api/v2/', include('staff.urls')),
    path('api/v3/', include('customer.urls')),
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)