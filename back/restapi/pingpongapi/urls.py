from django.urls import include, path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from . import views

schema_view = get_schema_view(
    openapi.Info(
        title="Pingpong API",
        default_version='v1',
        description="Pingpong API",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', views.ApiOverview, name='home'),
    path('pingpong/create/', views.create_job, name='create-job'),
    path('pingpong/status/<str:pk>/', views.status_job, name='status-job'),
    path('pingpong/update/<str:pk>/', views.update_job, name='update-job'),
    path('pingpong/render/<str:pk>/', views.render_job, name='render-job'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger',
            cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc',
            cache_timeout=0), name='schema-redoc'),
    path('nebula/<int:res>/<int:index>', views.get_nebula, name='get-nebula'),
]