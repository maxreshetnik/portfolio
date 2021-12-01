from decimal import Decimal
from io import BytesIO
from PIL import Image

from django.contrib.contenttypes.models import ContentType
from django.core.files.images import ImageFile
from django.test import TestCase

from ..services import IMG_SIZE
from ..models import Specification, Category, SmartphoneProduct


def get_data_for_image_field(img_size: tuple) -> ImageFile:
    img = Image.new('RGB', img_size)
    name = 'test_image.jpg'
    img_file = ImageFile(BytesIO(), name)
    img.save(img_file, 'JPEG')
    return img_file


class SmartphoneProductTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.ct_obj = ContentType.objects.get_for_model(SmartphoneProduct)
        cls.category = Category.objects.create(
            name='Smartphone',
            content_type=cls.ct_obj,
        )

    def setUp(self) -> None:
        self.smartphone = SmartphoneProduct(
            name='Samsung',
            marking='HE32BT',
            image='',
            category=self.category,
            ram='4GB',
            memory='64GB',
        )

    def test_create_product(self):
        product = self.smartphone
        product.save()
        self.assertIsNotNone(product.pk)
        self.assertEqual(
            SmartphoneProduct.objects.filter(pk=product.pk).count(), 1,
        )

    def test_image_save_in_storage(self):
        img_file = get_data_for_image_field(IMG_SIZE)
        product = self.smartphone
        product.image.save(img_file.name, img_file)
        self.assertTrue(product.image.storage.exists(product.image.path))
        product.image.delete(save=False)

    def test_image_resize(self):
        """All uploaded images are resized to the sizes specified in IMG_SIZE"""
        large_img_size = IMG_SIZE[0] * 2, IMG_SIZE[1] * 2
        product = self.smartphone
        product.image = get_data_for_image_field(large_img_size)
        product.save()
        actual_img_size = product.image.width, product.image.height
        self.assertTupleEqual(actual_img_size, IMG_SIZE)
        product.image.delete(save=False)


class SpecificationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.ct_obj = ContentType.objects.get_for_model(SmartphoneProduct)
        cls.category = Category.objects.create(
            name='Smartphone',
            content_type=cls.ct_obj,
        )
        cls.product = SmartphoneProduct.objects.create(
            name='Samsung',
            marking='HE32BT',
            image='',
            category=cls.category,
            ram='4GB',
            memory='64GB',
        )

    def setUp(self) -> None:
        self.specification = Specification(
            tag='64/128',
            image='',
            weight_vol=Decimal('1.000'),
            price=Decimal('10.00'),
            available_qty=Decimal('10.000'),
            content_object=self.product,
        )

    def test_create_specification(self):
        spec = self.specification
        spec.save()
        self.assertIsNotNone(spec.pk)
        self.assertEqual(
            Specification.objects.filter(pk=spec.pk).count(), 1,
        )

    def test_create_specification_with_blank_image(self):
        spec = self.specification
        setattr(spec.image, '_committed', False)
        spec.save()
        self.assertIsNotNone(spec.pk)
        self.assertEqual(
            Specification.objects.filter(pk=spec.pk).count(), 1,
        )

    def test_image_resize(self):
        """All uploaded images are resized to the sizes specified in IMG_SIZE"""
        large_img_size = IMG_SIZE[0] * 2, IMG_SIZE[1] * 2
        spec = self.specification
        spec.image = get_data_for_image_field(large_img_size)
        spec.save()
        actual_img_size = spec.image.width, spec.image.height
        self.assertTupleEqual(actual_img_size, IMG_SIZE)
        spec.image.delete(save=False)

    def test_image_resize_with_diff_width_height(self):
        """All uploaded images are resized to the sizes specified in IMG_SIZE"""
        diff_img_size = IMG_SIZE[0], IMG_SIZE[1] * 2
        spec = self.specification
        spec.image = get_data_for_image_field(diff_img_size)
        spec.save()
        actual_img_size = spec.image.width, spec.image.height
        self.assertTupleEqual(actual_img_size, IMG_SIZE)
        spec.image.delete(save=False)

    def test_discount_price(self):
        """The value for the discount_price field is calculated
        when the save() is called."""
        spec = self.specification
        spec.price = Decimal('10.00')
        spec.discount = 10
        spec.save()
        self.assertEqual(spec.discount_price, Decimal('9.00'))
