from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, viewsets, permissions
from .serializers import (
    CustomTokenObtainPairSerializer,
    UsuarioRegistroSerializer,
    ClienteSerializer,
    ProductoSerializer,
    FacturaSerializer,
)
from .models import Usuario, Cliente, Producto, Factura

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class RegistroUsuarioView(generics.CreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioRegistroSerializer
    permission_classes = [permissions.AllowAny]  # ✅ Esto permite el acceso sin token

class ClienteViewSet(viewsets.ModelViewSet):
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cliente.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Producto.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class FacturaViewSet(viewsets.ModelViewSet):
    serializer_class = FacturaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Factura.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save()