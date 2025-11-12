from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from facturas.models import Empresa, Cliente, Producto
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = "Inicializa empresa, cliente y producto para cada usuario que no los tenga"

    def handle(self, *args, **kwargs):
        for user in User.objects.all():
            empresa, creada = Empresa.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": f"Empresa de {user.full_name}",
                    "tax_identification_number": "123456789",
                    "address": "Dirección genérica",
                    "phone_number": "0000000000",
                    "email": user.email,
                    "website_link": "",
                }
            )
            if creada:
                self.stdout.write(self.style.SUCCESS(f"✅ Empresa creada para {user.email}"))

            # Cliente por defecto
            if not Cliente.objects.filter(empresa=empresa).exists():
                Cliente.objects.create(
                    empresa=empresa,
                    name="Cliente Demo",
                    email="cliente@demo.com",
                    phone_number="0000000000",
                    address="Dirección del cliente",
                    tax_identification_number="987654321"
                )
                self.stdout.write(f"🧾 Cliente demo creado para {user.email}")

            # Producto por defecto
            if not Producto.objects.filter(empresa=empresa).exists():
                Producto.objects.create(
                    empresa=empresa,
                    name="Producto Demo",
                    description="Producto de prueba",
                    unit_price=Decimal("100.00"),
                    vat_percentage=Decimal("19.00")
                )
                self.stdout.write(f"📦 Producto demo creado para {user.email}")

        self.stdout.write(self.style.SUCCESS("🎉 Inicialización completada."))