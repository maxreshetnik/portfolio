from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.admin import GenericStackedInline

from . import models, forms


class SpecificationInline(GenericStackedInline):

    form = forms.CustomValidationImageFieldForm
    model = models.Specification
    extra = 0


class OrderItemInline(admin.StackedInline):

    form = forms.OrderItemForm
    model = models.OrderItem
    extra = 0
    list_select_related = ('specification',)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.reserved:
            return self.get_fields(request)
        else:
            return 'price',


class OrderInline(admin.StackedInline):

    form = forms.OrderForm
    model = models.Order
    classes = ('collapse ',)
    extra = 0
    readonly_fields = ('order_cost', 'reserved')
    fieldsets = (
        (None, {'fields': (('status', 'order_cost', 'reserved'),)}),
        ('Shipping address', {'classes': ('collapse',),
                              'fields': ('address',)}),
    )


class ShippingAddressInline(admin.StackedInline):

    model = models.ShippingAddress
    classes = ('collapse ',)
    extra = 0


class RateInline(admin.StackedInline):

    model = models.Rate
    classes = ('collapse ',)
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

    form = forms.CustomValidationImageFieldForm
    inlines = [SpecificationInline]
    list_display = ['category', 'name', 'marking']
    list_select_related = ('category',)

    def get_fieldsets(self, request, obj=None):
        fields = super().get_fields(request, obj)
        sets = (None, {'fields': [
            'category', ('name', 'marking'), 'image',
            ('unit', 'unit_for_weight_vol'), 'description'
        ]})
        return [sets, ('Additional characteristics',
                       {'fields': fields[7:]})]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Extends parent method, filter categories for a specific product"""
        if db_field.name == "category":
            product_type = ContentType.objects.get_for_model(self.model)
            kwargs["queryset"] = models.Category.objects.filter(
                content_type_id=product_type.id, category__isnull=False
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):

    inlines = [
        ShippingAddressInline,
        OrderInline,
        RateInline,
    ]
    fields = ['username', 'email', 'first_name', 'last_name']
    list_display = ['username', 'email']
    search_fields = ['username']


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):

    form = forms.OrderForm
    inlines = [OrderItemInline]
    fields = ['user', 'status', 'address', ('order_cost', 'reserved')]
    radio_fields = {'status': admin.HORIZONTAL}
    list_display = ('id', 'user', 'status', 'order_cost', 'reserved')
    list_select_related = ('user',)
    list_filter = ('status',)
    search_fields = ['id__exact', 'user__username']

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return 'order_cost', 'reserved'
        f = ['user', 'order_cost', 'reserved']
        return f if obj.status < obj.SHIPPING else f + ['address']

    def save_related(self, request, form, formset, change):
        super().save_related(request, form, formset, change)
        if not change:
            return
        order = form.instance
        if order.status <= order.PROCESSING:
            qs = models.Order.objects.filter(id=order.id)
            kwargs = {'order_cost': form.get_current_cost()}
            if order.status == order.PROCESSING and not order.reserved:
                if form.reduce_available_quantity():
                    kwargs['reserved'] = True
                else:
                    kwargs['status'] = order.CART
            qs.update(**kwargs)
