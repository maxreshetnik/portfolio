from decimal import Decimal

from django.db import models, transaction, IntegrityError
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import SearchVector
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MaxValueValidator, MinValueValidator
from django.urls import reverse

from . import services


USER = get_user_model()


class Account(USER):

    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.username}'s account"


class CategoryManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Category(models.Model):
    """
    Creates model for product and parent categories.

    This model has a many-to-one relationship with itself,
    that is used for category and subcategory in the product catalog.
    """
    name = models.CharField(
        unique=True, max_length=40, verbose_name='name',
    )
    category = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True,
        blank=True, verbose_name='parent category',
        related_name='categories',
        limit_choices_to={'category__isnull': True},
    )
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        limit_choices_to={'app_label': 'shop',
                          'model__endswith': 'product'},
    )

    objects = CategoryManager()

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'
        indexes = (
            GinIndex(SearchVector('name', config='english'),
                     name='%(app_label)s_%(class)s_vector_idx'),
        )

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name,

    def get_absolute_url(self):
        if self.category is not None:
            kwargs = {
                'category': str(self.category.name).lower(),
                'subcategory': str(self.name).lower(),
            }
            return reverse('shop:subcategory', kwargs=kwargs)
        return reverse('shop:category', args=[str(self.name).lower()])


class Product(models.Model):
    """
    Abstract class with common fields for all product classes
    """
    UNIT_CHOICES = [
        ('Weight', (('KG', 'kilo'), ('LB', 'pound'))),
        ('Volume', (('L', 'liter'), ('GAL', 'gallon'))),
        ('PC', 'piece'), ('PCK', 'pack'), ('PR', 'pair'),
        ('BTL', 'bottle'), ('LT', 'lot')
    ]
    name = models.CharField(max_length=40)
    marking = models.CharField(
        help_text='Model or the main feature of the product.',
        max_length=40,
    )
    image = models.ImageField(
        upload_to=services.get_file_directory_path,
        help_text=('Minimal image sizes is {}x{} pixels. '
                   'Max upload file size up to {} {}.'
                   '').format(*services.IMG_SIZE, *services.FILE_SIZE),
        validators=[services.validate_image_size],
    )
    description = models.TextField(blank=True)
    unit = models.CharField(
        max_length=3, choices=UNIT_CHOICES, default='PC',
    )
    unit_for_weight_vol = models.CharField(
        max_length=3, choices=UNIT_CHOICES, default='KG',
        verbose_name='unit for weight/volume',
    )
    date_added = models.DateField(auto_now_add=True)
    category = models.ForeignKey(
        'Category', on_delete=models.PROTECT, related_name='+',
    )
    specs = GenericRelation('Specification')
    rates = GenericRelation('Rate')

    class Meta:
        abstract = True
        ordering = ['-date_added']
        indexes = (
            GinIndex(SearchVector('name', 'marking', config='english'),
                     name='%(class)s_vector_idx'),
        )

    def __str__(self):
        return f'{self.category} {self.name} {self.marking}'

    def save(self, *args, **kwargs):
        """
        Extends save method, resizes an image, updates specs category.

        When a category field is updated, it changes a category field
        in the specs related model.
        """
        services.handle_image_size(getattr(self, 'image'))
        is_category_updated = False
        if self.id is not None:
            model = getattr(self, '_meta').model
            is_category_updated = not model.objects.filter(
                pk=self.pk, category_id=self.category_id,
            ).exists()
        super().save(*args, **kwargs)
        if is_category_updated:
            self.specs.update(category_id=self.category_id)


class Specification(models.Model):
    """
    Creates a model with quantity and price characteristics.

    Links all product models through the ContentType model.
    This model has a many-to-many relationship with the Order
    model through an intermediate OrderItem model.
    """
    tag = models.CharField(max_length=20, blank=True)
    image = models.ImageField(
        upload_to=services.get_file_directory_path, blank=True,
        help_text=('Minimal image sizes is {}x{} pixels. '
                   'Max upload file size up to {} {}.'
                   '').format(*services.IMG_SIZE, *services.FILE_SIZE),
        validators=[services.validate_image_size],
    )
    pre_packing = models.DecimalField(
        max_digits=6, decimal_places=3, default='1',
        verbose_name='pre-packing',
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    weight_vol = models.DecimalField(
        max_digits=6, decimal_places=3, verbose_name='weight/volume',
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    price = models.DecimalField(
        max_digits=9, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    discount = models.IntegerField(
        default=0, help_text='A discount from 0 to 99%.',
        validators=[MinValueValidator(0), MaxValueValidator(99)]
    )
    discount_price = models.DecimalField(
        editable=False, max_digits=9, decimal_places=2, default=Decimal('0'),
    )
    sale_price = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text=('Special price replaces the discount price, '
                   '0 is disabled'),
    )
    available_qty = models.DecimalField(
        max_digits=6, decimal_places=3, verbose_name='available quantity',
        validators=[MinValueValidator(Decimal('0'))],
    )
    addition = models.CharField(
        max_length=100, blank=True, verbose_name='additional information',
    )
    date_added = models.DateField(auto_now_add=True)
    category = models.ForeignKey(
        'Category', on_delete=models.PROTECT, related_name='specs',
    )
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(available_qty__gte=0), name='qty_gte_0'),
        ]
        indexes = (
            GinIndex(SearchVector('tag', config='english'),
                     name='%(app_label)s_%(class)s_vector_idx'),
        )

    def __str__(self):
        product = self.content_object
        return f'{self.category} {product.name} {product.marking}, {self.tag}'

    def get_absolute_url(self):
        kwargs = {
            'category': str(self.category.category.name).lower(),
            'subcategory': str(self.category.name).lower(),
            'pk': self.pk
        }
        return reverse('shop:spec_detail', kwargs=kwargs)

    def save(self, *args, **kwargs):
        """
        Extends save method, resizes an image, calculates a discount price
        and adds category from a product model.
        """
        services.handle_image_size(getattr(self, 'image'))
        self.discount_price = self.price - (
                self.price * self.discount / 100
        ).quantize(self.price)
        if self.category_id is None:
            self.category_id = self.content_object.category_id
        super().save(*args, **kwargs)


class ShippingAddress(models.Model):

    user = models.ForeignKey(
        USER, on_delete=models.CASCADE, related_name='addresses'
    )
    full_name = models.CharField(max_length=90)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=60)
    region = models.CharField(max_length=60)
    postcode = models.CharField(max_length=10)
    country = models.CharField(max_length=60)
    phone = models.CharField(max_length=20)
    by_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'shipping addresses'
        constraints = [
            models.UniqueConstraint(
                fields=['user'], name='unique_default_address',
                condition=models.Q(by_default=True),
            ),
        ]

    def __str__(self):
        return f'{self.full_name}, {self.address}, {self.city}'


class Order(models.Model):
    """
    Creates a table in the database and manages user orders.

    The model has a many-to-many relationship with the Specification model
    through an intermediate OrderItem model.
    """
    CART = 1
    PROCESSING = 2
    SHIPPING = 3
    FINISHED = 4
    CANCELED = 5
    STATUS_CHOICES = [
        (CART, 'Cart'), (PROCESSING, 'Processing'), (SHIPPING, 'Shipping'),
        (FINISHED, 'Finished'), (CANCELED, 'Canceled'),
    ]
    status = models.PositiveIntegerField(
        choices=STATUS_CHOICES,
    )
    address = models.TextField(blank=True)
    order_cost = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    reserved = models.BooleanField(default=False)
    order_date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(USER, on_delete=models.CASCADE)
    specs = models.ManyToManyField(Specification, through='OrderItem')

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_cart',
                                    condition=models.Q(status=1)),
        ]

    def __str__(self):
        return f'{self.user} order No.{self.pk}'

    def reserve_available_quantity(self) -> bool:
        """
        Reduces the product spec available quantity by order item qty.
        """
        items = self.specs.through.objects.select_related(
            'specification',
        ).select_for_update().filter(order_id=self.id)
        try:
            with transaction.atomic():
                for item in items:
                    spec = item.specification
                    new_qty = models.F('available_qty') - item.quantity
                    spec.available_qty = new_qty
                    spec.save()
        except IntegrityError:
            return False
        else:
            self.reserved = True
            return True

    def cancel_reserved_quantity(self):
        """increase the available product quantity
        by item quantity from the order."""
        items = self.specs.through.objects.select_related(
            'specification',
        ).filter(order_id=self.id)
        for item in items:
            spec = item.specification
            spec.available_qty = models.F('available_qty') + item.quantity
            spec.save()
        self.reserved = False

    def save(self, *args, **kwargs):
        """Extends the method with a condition for
        canceled reserved orders."""
        if (self.status == self.CANCELED and
                self.reserved and self.id is not None):
            self.cancel_reserved_quantity()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Removes only completed or canceled orders."""
        # noinspection PyTypeChecker
        if self.status > self.SHIPPING:
            super().delete(*args, **kwargs)


class OrderItem(models.Model):
    """
    Creates intermediate table for m2m field in Order model and Specification.

    The table has a unique constraint on the specification and
    order fields to prevent duplicate specification in the same Order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    specification = models.ForeignKey(
        Specification, on_delete=models.PROTECT,
    )
    quantity = models.DecimalField(
        max_digits=6, decimal_places=3,
        validators=[MinValueValidator(Decimal('0'))],
    )
    price = models.DecimalField(
        max_digits=9, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['order', 'specification'],
                                    name='order_item_unique'),
        ]

    def __str__(self):
        return f'{self.specification}'

    def save(self, *args, **kwargs):
        # noinspection PyTypeChecker
        if self.quantity > 0:
            super().save(*args, **kwargs)


class Rate(models.Model):

    class PointValue(models.IntegerChoices):
        one, two, three, four, five = 1, 2, 3, 4, 5

    point = models.IntegerField(choices=PointValue.choices)
    review = models.TextField(blank=True)
    user = models.ForeignKey(USER, on_delete=models.CASCADE)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'object_id'],
                                    name='user_rate_unique'),
        ]

    def __str__(self):
        return f'{self.user} {self.point} to {self.content_object}'


class TvProduct(Product):

    screen_diagonal = models.CharField(max_length=10)
    screen_resolution = models.CharField(max_length=20)

    class Meta(Product.Meta):
        verbose_name = 'TV'


class SmartphoneProduct(Product):

    ram = models.CharField(max_length=30)
    memory = models.CharField(max_length=30)

    class Meta(Product.Meta):
        verbose_name = 'smartphone'


class ClothingProduct(Product):

    TYPE_CHOICES = [
        ('M', 'Men'), ('W', 'Women'), ('K', 'Kids')
    ]
    SIZE_CHOICES = [
        ('S', 'S'), ('M', 'M'), ('L', 'L'),
        ('XL', 'XL'), ('2X', 'XXL'),
    ]
    type = models.CharField(max_length=1, choices=TYPE_CHOICES)
    size = models.CharField(
        max_length=2, choices=SIZE_CHOICES, blank=True,
    )

    class Meta(Product.Meta):
        verbose_name = 'clothing'
        verbose_name_plural = 'clothing'


class FoodProduct(Product):

    class Meta(Product.Meta):
        verbose_name = 'foodstuff'
