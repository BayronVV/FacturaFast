from rest_framework import serializers
from .models import Usuario, Empresa, Cliente, Producto, Factura, FacturaItem
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

DEFAULT_VAT = Decimal('19.00')

# -------------------------------
# Empresa
# -------------------------------

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        exclude = ['user']

# -------------------------------
# Usuario con empresa
# -------------------------------

class UsuarioRegistroSerializer(serializers.ModelSerializer):
    empresa = EmpresaSerializer()

    class Meta:
        model = Usuario
        fields = ['email', 'full_name', 'password', 'empresa']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        empresa_data = validated_data.pop('empresa')
        user = Usuario.objects.create_user(**validated_data)
        Empresa.objects.create(user=user, **empresa_data)
        return user

# -------------------------------
# Cliente
# -------------------------------

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            'id', 'empresa', 'name', 'email', 'phone_number',
            'address', 'tax_identification_number', 'created_at'
        ]
        read_only_fields = ['id', 'empresa', 'created_at']

# -------------------------------
# Producto
# -------------------------------

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            'id', 'empresa', 'name', 'description',
            'unit_price', 'vat_percentage', 'created_at'
        ]
        read_only_fields = ['id', 'empresa', 'created_at']

# -------------------------------
# FacturaItem (lectura)
# -------------------------------

class FacturaItemReadSerializer(serializers.ModelSerializer):
    product = ProductoSerializer(read_only=True)

    class Meta:
        model = FacturaItem
        fields = ['id', 'product', 'description', 'unit_price', 'vat_percentage', 'quantity']

# -------------------------------
# FacturaItem (escritura)
# -------------------------------

class FacturaItemWriteSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())

    class Meta:
        model = FacturaItem
        fields = ['id', 'product', 'description', 'unit_price', 'vat_percentage', 'quantity']
        read_only_fields = ['id']

    def validate(self, attrs):
        request = self.context.get('request')
        empresa = getattr(request.user, 'empresa', None)
        product = attrs.get('product')

        if not product:
            raise serializers.ValidationError("product is required")
        if empresa is None or product.empresa_id != empresa.id:
            raise serializers.ValidationError("Producto no pertenece a la empresa del usuario")

        qty = attrs.get('quantity')
        if qty is None:
            raise serializers.ValidationError("quantity is required")
        try:
            if int(qty) <= 0:
                raise serializers.ValidationError("quantity must be greater than 0")
        except (TypeError, ValueError):
            raise serializers.ValidationError("quantity must be an integer")

        return attrs

    def _to_decimal(self, value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise serializers.ValidationError("Invalid decimal value")

    def create(self, validated_data):
        product = validated_data['product']
        up = validated_data.get('unit_price')
        vp = validated_data.get('vat_percentage')

        validated_data['unit_price'] = self._to_decimal(up) if up is not None else product.unit_price
        validated_data['vat_percentage'] = self._to_decimal(vp) if vp is not None else (product.vat_percentage or DEFAULT_VAT)
        validated_data['quantity'] = int(validated_data['quantity'])

        return FacturaItem.objects.create(**validated_data)

# -------------------------------
# Factura
# -------------------------------

class FacturaSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Cliente.objects.all(), write_only=True)
    customer_detail = ClienteSerializer(source='customer', read_only=True)
    number = serializers.CharField(read_only=True)

    items = FacturaItemWriteSerializer(many=True, required=False, write_only=True)
    items_detail = FacturaItemReadSerializer(source='facturaitem_set', many=True, read_only=True)

    class Meta:
        model = Factura
        fields = [
            'id', 'empresa', 'customer', 'customer_detail', 'invoice_date', 'notes', 'number',
            'subtotal', 'total_tax', 'total', 'items', 'items_detail', 'created_at'
        ]
        read_only_fields = [
            'id', 'empresa', 'subtotal', 'total_tax', 'total',
            'created_at', 'invoice_date', 'number'
        ]

    def validate(self, attrs):
        request = self.context.get('request')
        empresa = getattr(request.user, 'empresa', None)
        customer = attrs.get('customer')

        if empresa is None:
            raise serializers.ValidationError("Usuario sin empresa asociada")
        if customer.empresa_id != empresa.id:
            raise serializers.ValidationError("Cliente no pertenece a la empresa del usuario")

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data.pop('invoice_date', None)
        items_input = request.data.get('items', [])
        validated_data.pop('items', None)

        if not items_input or not isinstance(items_input, list):
            raise serializers.ValidationError("Debes incluir al menos un producto en la factura.")

        # ✅ Ya viene empresa desde la vista, no la pasamos de nuevo
        factura = Factura.objects.create(**validated_data)

        for idx, item_raw in enumerate(items_input):
            try:
                item_data = {
                    'product': item_raw.get('product'),
                    'description': item_raw.get('description', ''),
                    'unit_price': item_raw.get('unit_price'),
                    'vat_percentage': item_raw.get('vat_percentage'),
                    'quantity': item_raw.get('quantity'),
                }

                write_serializer = FacturaItemWriteSerializer(data=item_data, context={'request': request})
                write_serializer.is_valid(raise_exception=True)
                vi = write_serializer.validated_data

                FacturaItem.objects.create(
                    invoice=factura,
                    product=vi['product'],
                    description=vi.get('description', ''),
                    unit_price=vi.get('unit_price', vi['product'].unit_price),
                    vat_percentage=vi.get('vat_percentage', vi['product'].vat_percentage or DEFAULT_VAT),
                    quantity=int(vi['quantity'])
                )
            except Exception as e:
                raise serializers.ValidationError({f"item_{idx}": str(e)})

        factura.recalculate_totals()
        return factura

# -------------------------------
# Login con email
# -------------------------------

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Credenciales inválidas")

        attrs["username"] = user.email
        data = super().validate(attrs)
        data["email"] = user.email
        return data