from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

DEFAULT_VAT = Decimal('19.00')

class UsuarioManager(BaseUserManager):
    def create_user(self, email, full_name, password=None):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password):
        user = self.create_user(email, full_name, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return self.email

class Empresa(models.Model):
    user = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    tax_identification_number = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
    email = models.EmailField()
    website_link = models.URLField(blank=True)

class Empresa(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='empresa')
    company_name = models.CharField(max_length=255)
    tax_identification_number = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    website_link = models.URLField(blank=True)

    def __str__(self):
        return self.company_name


class Cliente(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='clientes')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    tax_identification_number = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.empresa.company_name}"


class Producto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='productos')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    vat_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=DEFAULT_VAT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.empresa.company_name}"


class Factura(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='facturas')
    customer = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='facturas')
    invoice_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    number = models.CharField(max_length=64, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-invoice_date', '-id']

    def __str__(self):
        return f"Factura {self.number or self.id} — {self.empresa.company_name}"

    def recalculate_totals(self):
        items = self.items.all()
        subtotal = Decimal('0.00')
        total_tax = Decimal('0.00')
        for it in items:
            line_ex = (it.unit_price * it.quantity)
            line_tax = (line_ex * (it.vat_percentage / Decimal('100.00')))
            subtotal += line_ex
            total_tax += line_tax
        self.subtotal = subtotal
        self.total_tax = total_tax
        self.total = subtotal + total_tax
        self.save(update_fields=['subtotal', 'total_tax', 'total'])


class FacturaItem(models.Model):
    invoice = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='factura_items')
    description = models.CharField(max_length=1024, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vat_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def line_total_exclusive(self):
        return (self.unit_price * self.quantity)

    @property
    def line_tax(self):
        return (self.line_total_exclusive * (self.vat_percentage / Decimal('100.00')))

    @property
    def line_total_inclusive(self):
        return self.line_total_exclusive + self.line_tax

    def save(self, *args, **kwargs):
        # Completa unit_price y vat desde el producto si no vienen
        if self.unit_price is None:
            self.unit_price = self.product.unit_price
        if self.vat_percentage is None:
            self.vat_percentage = self.product.vat_percentage or DEFAULT_VAT
        super().save(*args, **kwargs)
        # Recalcula totales de la factura padre
        try:
            self.invoice.recalculate_totals()
        except Exception:
            pass