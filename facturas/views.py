from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, viewsets, permissions, status
from rest_framework.response import Response
import traceback

from .serializers import (
    CustomTokenObtainPairSerializer,
    UsuarioRegistroSerializer,
    ClienteSerializer,
    ProductoSerializer,
    FacturaSerializer,
)

from .models import Usuario, Cliente, Producto, Factura

# 🔐 Login personalizado con email
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# 👤 Registro de usuario con empresa
class RegistroUsuarioView(generics.CreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioRegistroSerializer
    permission_classes = [permissions.AllowAny]

# 👥 CRUD de clientes
class ClienteViewSet(viewsets.ModelViewSet):
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cliente.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

# 📦 CRUD de productos
class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Producto.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

# 🧾 CRUD de facturas con trazas de error
class FacturaViewSet(viewsets.ModelViewSet):
    serializer_class = FacturaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Factura.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        empresa = self.request.user.empresa
        serializer.save(empresa=empresa)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            print("❌ ERROR AL CREAR FACTURA ❌")
            traceback.print_exc()
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)