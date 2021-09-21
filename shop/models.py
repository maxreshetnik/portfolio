from io import BytesIO
from decimal import Decimal

from PIL import Image
from django.db import models
from django.urls import reverse
from django.core.files.images import ImageFile, File
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.validators import MaxValueValidator, MinValueValidator


USER = get_user_model()
IMG_SIZE = (600, 600)   # minimal image sizes in pixels
FILE_SIZE = (10, 'MB')   # maximal file size 'MB' or 'KB' only


def file_directory_path():
    pass


def handle_image(obj):
    """
    Changes dimensions of an image to the dimensions in IMG_SIZE constant.

    If an image is loaded, the function creates new image object and replaces old one.
    """
    if getattr(obj, '_committed', True) or not obj.name:
        return
    try:
        with obj.open(), Image.open(obj) as img:
            new_img = img.resize(IMG_SIZE, reducing_gap=3.0)
            file = getattr(obj, '_file')
            name = obj.name if not isinstance(file, File) else (
                str(obj.name).rpartition('/')[2])
            new_file = ImageFile(BytesIO(), name)
            new_img.save(new_file, img.format)
    except OSError:
        return
    setattr(obj, 'file', new_file)
    setattr(obj, 'name', name)


class Account(USER):

    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.username}'s account"


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
        blank=True, related_name='categories',
    )
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        limit_choices_to={'app_label': 'shop',
                          'model__endswith': 'product'},
    )

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

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
        upload_to='shop/',
        help_text=('Minimal image sizes is {}x{} pixels. '
                   'Max upload file size up to '
                   '{} {}.').format(*IMG_SIZE, *FILE_SIZE)
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

    def __str__(self):
        return f'{self.category} {self.name} {self.marking}'

    def save(self, *args, **kwargs):
        """Extends save method, resizes the loaded image"""
        handle_image(getattr(self, 'image'))
        super().save(*args, **kwargs)


class Specification(models.Model):
    """
    Creates a model with quantity and price characteristics.

    Links all product models through the ContentType model.
    Contains a field named customers, which is used to add
    products to the cart through an intermediate table with
    the quantity of items in user's cart.
    The model has a many-to-many relationship with the Order
    model through an intermediate OrderItem model.
    """
    tag = models.CharField(max_length=20, blank=True)
    image = models.ImageField(
        upload_to='shop/', blank=True,
        help_text=('Minimal image sizes is {}x{} pixels. '
                   'Max upload file size up to '
                   '{} {}.').format(*IMG_SIZE, *FILE_SIZE),
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
        default='0', help_text='A discount from 0 to 99%.',
        validators=[MinValueValidator(0), MaxValueValidator(99)]
    )
    discount_price = models.DecimalField(
        editable=False, max_digits=9, decimal_places=2, default='0',
    )
    sale_price = models.DecimalField(
        max_digits=9, decimal_places=2, default='0',
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

    def __str__(self):
        return f'{self.content_object}, {self.tag}'

    def save(self, *args, **kwargs):
        """Extends save method, resizes an image and calculates
        a value for the discount_price field.
        """
        handle_image(getattr(self, 'image'))
        self.discount_price = self.price - (
                self.price * self.discount / 100
        ).quantize(self.price)
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
            models.UniqueConstraint(fields=['user'], name='unique_default_address',
                                    condition=models.Q(by_default=True)),
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
        max_digits=9, decimal_places=2, default='0',
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

    def save(self, *args, **kwargs):
        if self.reserved and self.status == self.CART and self.id is not None:
            items = OrderItem.objects.select_related(
                'specification',
            ).filter(order_id=self.id)
            for item in items:
                spec = item.specification
                spec.available_qty = models.F('available_qty') + item.quantity
                spec.save()
            self.reserved = False
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # noinspection PyTypeChecker
        if self.status > self.SHIPPING:
            super().delete(*args, **kwargs)


class OrderItem(models.Model):
    """
    Creates intermediate table for ManyToMany field in Order model and Specification.

    The table has a unique constraint on the specification and
    user fields to prevent duplicate rows.
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
        return f'{self.point} from {self.user} to {self.content_object}'


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

    GENDER_CHOICES = [
        ('M', 'Men'), ('W', 'Women'), ('K', 'Kids')
    ]
    SIZE_CHOICES = [
        ('S', 'S'), ('M', 'M'), ('L', 'L'),
        ('XL', 'XL'), ('2X', 'XXL'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    size = models.CharField(
        max_length=2, choices=SIZE_CHOICES, blank=True,
    )

    class Meta(Product.Meta):
        verbose_name = 'clothing'
        verbose_name_plural = 'clothing'


class FoodProduct(Product):

    class Meta(Product.Meta):
        verbose_name = 'foodstuff'
