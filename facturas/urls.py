from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegistroUsuarioView,
    ClienteViewSet,
    ProductoViewSet,
    FacturaViewSet,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet, basename='clientes')
router.register(r'productos', ProductoViewSet, basename='productos')
router.register(r'facturas', FacturaViewSet, basename='facturas')

urlpatterns = [
    # Auth / registro
    path('registro/', RegistroUsuarioView.as_view(), name='registro'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API recursos (GET/POST/PUT/DELETE para clientes, productos y facturas)
    path('', include(router.urls)),
]
