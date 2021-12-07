from decimal import Decimal
from io import BytesIO
from PIL import Image

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.images import ImageFile
from django.db.utils import IntegrityError
from django.test import TestCase

from ..services import IMG_SIZE
from ..models import (
    Specification, Category, SmartphoneProduct, Order,
)


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

    def test_available_qty_constraint(self):
        """
        Checking the model constraint on the value of available qty field.

        An IntegrityError exception should be raised if the field value
        is less than 0.
        """
        spec = self.specification
        spec.available_qty = Decimal('-1.000')
        msg = 'Add a CheckConstraint to the specification model Meta class.'
        with self.assertRaises(IntegrityError, msg=msg):
            spec.save()

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


class OrderTests(TestCase):

    fixtures = ['shop_example_data.json']

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.username = 'test'
        cls.passwd = 'fdf24F42uih'
        cls.user = User.objects.create_user(
            username=cls.username, password=cls.passwd,
        )

    def setUp(self):
        self.cart_order = Order(user=self.user, status=Order.CART)

    def fill_cart_order_with_items(self, num_items: int) -> list:
        self.cart_order.save()
        spec_list = list(Specification.objects.filter(
            available_qty__gt=0,
        )[:num_items])
        for spec in spec_list:
            self.cart_order.specs.add(
                spec,
                through_defaults={'quantity': spec.pre_packing,
                                  'price': spec.price},
            )
        return spec_list

    def test_create_order(self):
        self.cart_order.save()
        self.assertIsNotNone(self.cart_order.pk)
        shipping_order = Order(user=self.user, status=Order.SHIPPING)
        shipping_order.save()
        self.assertIsNotNone(shipping_order.pk)
        # create another order with the shipping status
        shipping_order.pk = None
        shipping_order.save()
        self.assertEqual(
            Order.objects.filter(user_id=self.user.pk).count(), 3,
        )

    def test_unique_order_with_cart_status(self):
        """The same user can have one order with a cart status
        and more than one with other status."""
        self.cart_order.save()
        self.cart_order.pk = None
        msg = 'Check the unique constraint in the Order model.'
        with self.assertRaises(IntegrityError, msg=msg):
            self.cart_order.save()

    def test_add_items_to_order(self):
        num_items = 2
        self.fill_cart_order_with_items(num_items)
        self.assertEqual(self.cart_order.specs.count(), num_items)

    def test_cancel_reserved_quantity(self):
        """Increase the available spec quantity by item quantity
        from the order."""
        num_items = 3
        spec_list = self.fill_cart_order_with_items(num_items)
        available_qty_result = {
            s.id: s.available_qty + s.pre_packing for s in spec_list
        }
        self.cart_order.reserved = True
        self.cart_order.cancel_reserved_quantity()
        self.assertFalse(self.cart_order.reserved)
        for spec in self.cart_order.specs.all():
            self.assertEqual(
                spec.available_qty,
                available_qty_result.get(spec.id, None),
            )

    def test_cancel_reserved_quantity_pre_delete_signal(self):
        """Increase the available qty when deleting unshipped orders."""
        num_items = 1
        self.cart_order.status = self.cart_order.PROCESSING
        self.cart_order.reserved = True
        spec_list = self.fill_cart_order_with_items(num_items)
        spec = spec_list[0]
        available_qty_result = spec.available_qty + spec.pre_packing
        Order.objects.filter(pk=self.cart_order.id).delete()
        spec.refresh_from_db()
        self.assertEqual(spec.available_qty, available_qty_result)

    def test_save_canceled_order_with_reserved_quantity(self):
        """The method cancel_reserved_quantity() is called when
        an existing order is saved with a canceled status."""
        num_items = 1
        spec_list = self.fill_cart_order_with_items(num_items)
        spec = spec_list[0]
        available_qty_result = spec.available_qty + spec.pre_packing
        self.cart_order.status = self.cart_order.CANCELED
        self.cart_order.reserved = True
        self.cart_order.save()
        spec.refresh_from_db()
        self.assertEqual(spec.available_qty, available_qty_result)

    def test_reserve_available_quantity(self):
        """
        Decrease available qty on a product spec by each item qty.

        Method reserve_available_quantity() returns True if the decrease
        in the available quantity was successful for all items.
        """
        num_items = 3
        spec_list = self.fill_cart_order_with_items(num_items)
        available_qty_result = {
            s.id: s.available_qty - s.pre_packing for s in spec_list
        }
        self.cart_order.status = self.cart_order.PROCESSING
        is_reserved = self.cart_order.reserve_available_quantity()
        self.assertTrue(is_reserved, msg='The order was not reserved.')
        for spec in self.cart_order.specs.all():
            self.assertEqual(
                spec.available_qty,
                available_qty_result.get(spec.id, None),
                msg=('The actual available qty has not been reduced by '
                     'the item qty.')
            )
        self.assertTrue(
            self.cart_order.reserved,
            msg='Value of reserved field should be changed to True.'
        )

    def test_item_qty_not_available_for_reservation(self):
        """Cancel the reservation of all products if there is not enough
        the available quantity for any product."""
        num_items = 3
        spec_list = self.fill_cart_order_with_items(num_items)
        # One of the items is out of stock.
        spec_list[-1].available_qty = Decimal('0')
        spec_list[-1].save()
        available_qty_result = {
            s.id: s.available_qty for s in spec_list
        }
        # Decreases available qty on a product spec by each item qty.
        is_reserved = self.cart_order.reserve_available_quantity()
        self.assertFalse(
            is_reserved, msg=('The order was reserved with an item '
                              'that is out of stock.')
        )
        for spec in self.cart_order.specs.all():
            self.assertEqual(
                spec.available_qty,
                available_qty_result.get(spec.id, None),
                msg=('Actual available qty was changed, '
                     'unable to rollback db transaction.')
            )

    def test_order_specs_unique_constraint(self):
        """The same order contains unique product specifications."""
        self.cart_order.save()
        spec = Specification.objects.first()
        item = self.cart_order.specs.through(
            order=self.cart_order,
            specification=spec,
            quantity=spec.pre_packing,
            price=spec.price,
        )
        item.save()
        item.pk = None
        msg = ('Add a unique constraint for order and specification '
               'fields to the intermediate model specified in '
               'the many-to-many field specs.')
        with self.assertRaises(IntegrityError, msg=msg):
            item.save()
