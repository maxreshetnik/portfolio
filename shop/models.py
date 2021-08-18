from io import BytesIO
from decimal import Decimal

from PIL import Image
from django.db import models
from django.urls import reverse
from django.core.files.images import ImageFile, File
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation


USER = get_user_model()
IMG_SIZE = (600, 600)   # minimal image sizes in pixels
FILE_SIZE = (10, 'MB')   # maximal file size 'MB' or 'KB' only


def file_directory_path():
    pass


def handle_image(obj):
    """
    Change dimensions of an image to the dimensions in IMG_SIZE constant.

    If an image is loaded, the function create new image object and replace old one.
    """
    if getattr(obj, '_committed', True) or not obj.name:
        return
    try:
        with obj.open(), Image.open(obj) as img:
            # img.thumbnail(IMG_SIZE)
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


class Category(models.Model):

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

    """Abstract class with common fields for all product type classes"""

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
        """extend save method, resize loaded image"""
        handle_image(getattr(self, 'image'))
        super().save(*args, **kwargs)

    def get_ct_id(self):
        return ContentType.objects.get_for_model(self).pk


class Specification(models.Model):

    """
    create a model with quantity and price characteristics.

    link all product models through the ContentType model.
    Contains a field named customers, which is used to add
    products to the cart through an intermediate table with
    the quantity of items in user's cart.
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
    customers = models.ManyToManyField(USER, through='CartItem')

    def __str__(self):
        return f'{self.content_object}, {self.tag}'

    def save(self, *args, **kwargs):
        """extend save method, resize image and calculate discount_price field"""
        handle_image(getattr(self, 'image'))
        self.discount_price = self.price - (
                self.price * self.discount / 100
        ).quantize(self.price)
        super().save(*args, **kwargs)


class Account(USER):

    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.username}'s account"


class CartItem(models.Model):

    """
    Create intermediate table for ManyToMany field in Specification model and user one.

    The table has a unique constraint on the specification and
    user fields to prevent duplicate rows.
    """

    specification = models.ForeignKey(
        Specification, on_delete=models.CASCADE,
    )
    user = models.ForeignKey(USER, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=6, decimal_places=3,
        validators=[MinValueValidator(Decimal('0'))],
    )

    class Meta:
        verbose_name_plural = 'cart'
        constraints = [
            models.UniqueConstraint(fields=['specification', 'user'],
                                    name='user_item_unique'),
        ]

    def __str__(self):
        return f"{self.specification} {self.quantity}"


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


class ShippingAddress(models.Model):

    user = models.ForeignKey(
        USER, on_delete=models.CASCADE, related_name='addresses'
    )
    full_name = models.CharField(max_length=90)
    country = models.CharField(max_length=60)
    region = models.CharField(max_length=60)
    city = models.CharField(max_length=60)
    postcode = models.CharField(max_length=10)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)

    class Meta:
        verbose_name_plural = 'shipping addresses'

    def __str__(self):
        return f"{self.full_name}'s address"


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
