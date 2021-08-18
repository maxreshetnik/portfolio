from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.admin import GenericStackedInline

from . import models, forms


class SpecificationInline(GenericStackedInline):

    form = forms.SpecificationForm
    model = models.Specification
    extra = 0


class CartItemInline(admin.StackedInline):

    model = models.CartItem
    extra = 0


class ShippingAddressInline(admin.StackedInline):

    model = models.ShippingAddress
    extra = 0


class RateInline(admin.StackedInline):

    model = models.Rate
    extra = 0


class CategoryInline(admin.StackedInline):

    model = models.Category
    extra = 0


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):

    inlines = [CategoryInline]
    list_display = ['name', 'category', 'content_type']
    fields = ['content_type', 'category', 'name']


@admin.register(models.TvProduct, models.SmartphoneProduct,
                models.ClothingProduct, models.FoodProduct)
class ProductAdmin(admin.ModelAdmin):

    form = forms.ProductForm
    inlines = [SpecificationInline]
    list_display = ['category', 'name', 'marking']

    def get_fieldsets(self, request, obj=None):
        fields = super().get_fields(request, obj)
        sets = (None, {'fields': [
            'category', ('name', 'marking'), 'image',
            ('unit', 'unit_for_weight_vol'), 'description'
        ]})
        return [sets, ('Additional characteristics',
                       {'fields': fields[7:]})]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Extend parent method, filter categories for a specific product"""
        if db_field.name == "category":
            product_type = ContentType.objects.get_for_model(self.model)
            kwargs["queryset"] = models.Category.objects.filter(
                content_type_id=product_type.id, category__isnull=False
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):

    inlines = [
        CartItemInline,
        ShippingAddressInline,
        RateInline,
    ]
    list_display = ['username', 'email']
    exclude = [
        'password', 'is_superuser', 'groups',
        'user_permissions', 'is_staff', 'is_active',
    ]


admin.site.register(models.Rate, admin.ModelAdmin)
admin.site.register(models.CartItem, admin.ModelAdmin)
