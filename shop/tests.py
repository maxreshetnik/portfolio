from decimal import Decimal
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory
from django.urls import reverse

from . import views
from .models import Specification, Order, Category


User = get_user_model()


class CreateAccountViewTests(TestCase):

    def test_get_sign_up_page(self):
        response = self.client.get(reverse('shop:sign_up'))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'registration/sign_up.html')

    def test_user_create_account(self):
        username = 'test'
        passwd = 'fdf24F42uih'
        response = self.client.post(
            reverse('shop:sign_up'),
            data={'username': username, 'password1': passwd,
                  'password2': passwd},
        )
        # Test if form is valid then redirect to next url, code 302
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(User.objects.filter(username='test').count(), 1)
        self.client.logout()
        self.assertTrue(self.client.login(username=username, password=passwd))


class HomePageViewTests(TestCase):

    fixtures = ['shop_example_data.json']

    @classmethod
    def setUpTestData(cls):
        cls.username = 'test'
        cls.passwd = 'fdf24F42uih'
        cls.user = User.objects.create_user(
            username=cls.username, password=cls.passwd,
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.specs = Specification.objects.filter(
            available_qty__gt=0,
        ).order_by('-id')
        self.request = self.factory.get(reverse('shop:home'))

    def test_context_data(self):
        """Context data for anonymous users"""
        n = views.HomePageView.number_of_specs
        self.assertGreaterEqual(
            len(self.specs), n,
            msg=f'There are less than {n} specifications in the test db.',
        )
        self.request.user = AnonymousUser()
        response = views.HomePageView.as_view()(self.request)
        self.assertIn('rating_scale', response.context_data)
        self.assertIn('form_login', response.context_data)
        self.assertIn('form_sign_up', response.context_data)
        self.assertNotIn('cart', response.context_data)
        self.assertIn('spec_list', response.context_data)
        spec_list = list(
            response.context_data['spec_list'].values_list('id', flat=True)
        )
        self.assertEqual(len(spec_list), n)
        self.assertEqual(spec_list[0], self.specs[0].id)

    def test_cart_context_data(self):
        """
        Context data contains the user cart with the quantity and
        spec id as the dict key.
        """
        spec = self.specs.first()
        self.assertIsNotNone(spec, msg='No specification')
        self.request.user = self.user
        response = views.HomePageView.as_view()(self.request)
        self.assertIn('cart', response.context_data)
        # If there are no specs in the cart
        self.assertFalse(response.context_data['cart'])
        # A user cart is an order with a cart status.
        order = Order.objects.create(
            user=self.user, status=Order.CART
        )
        defaults = {'quantity': Decimal('1'), 'price': spec.price}
        order.specs.add(spec, through_defaults=defaults)
        response = views.HomePageView.as_view()(self.request)
        self.assertDictEqual(
            response.context_data['cart'],
            {spec.id: defaults['quantity']},
        )

    def test_add_to_cart(self):
        """
        Only a logged-in user can add products to his cart,
        change the quantity and remove products from the cart,
        changing the quantity to zero.
        """
        spec_list = list(self.specs[:2])
        self.assertEqual(len(spec_list), 2, msg='No specs in test db')
        spec1 = {'specification': spec_list[0].id,
                 'quantity': spec_list[0].pre_packing}
        spec2 = {'specification': spec_list[1].id,
                 'quantity': spec_list[1].pre_packing}
        response = self.client.post(reverse('shop:home'), data=spec1)
        self.assertRedirects(
            response, f'{reverse("shop:login")}?next={reverse("shop:home")}'
        )
        self.assertTrue(
            self.client.login(username=self.username, password=self.passwd)
        )
        # Test of adding and changing the quantity in the cart.
        for _ in range(2):
            response = self.client.post(reverse('shop:home'), data=spec1)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertEqual(len(response.context['cart']), 1)
            self.assertEqual(response.context['cart'][spec_list[0].id],
                             spec1['quantity'])
            spec1['quantity'] += spec_list[0].pre_packing
        # Test for adding another item to the cart and then removing it.
        response = self.client.post(reverse('shop:home'), data=spec2)
        self.assertEqual(len(response.context['cart']), 2)
        spec2['quantity'] = 0
        response = self.client.post(reverse('shop:home'), data=spec2)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.context['cart']), 1)


class SpecificationDetailTests(TestCase):

    fixtures = ['shop_example_data.json']

    @classmethod
    def setUpTestData(cls):
        cls.username = 'test'
        cls.passwd = 'fdf24F42uih'
        cls.user = User.objects.create_user(
            username=cls.username, password=cls.passwd,
        )

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_template_names(self):
        """
        Method get_template_names() adds a product model name to
        a template name and returns a list of template names.
        """
        spec = Specification.objects.first()
        self.assertIsNotNone(spec, msg='No specification')
        category = spec.content_object.category
        kwargs = {
            'category': str(category.category.name).lower(),
            'subcategory': str(category.name).lower(),
            'pk': str(spec.id),
        }
        request = self.factory.get(reverse(
            'shop:spec_detail', kwargs=kwargs,
        ))
        request.user = self.user
        response = views.SpecificationDetail.as_view()(request, **kwargs)
        t_name = f'shop/spec_detail/spec_{spec.content_type.model}.html'
        self.assertEqual(response.template_name[0], t_name)


class SearchViewTests(TestCase):

    fixtures = ['shop_example_data.json']

    def test_category_search_result(self):
        """
        Returns products with a category name in a user search query.
        """
        category = Category.objects.filter(
            category__isnull=True,
        ).first()
        self.assertIsNotNone(category, msg='No category in test db')
        category_names = list(
            category.categories.order_by().values_list('name', flat=True)
        ) + [category.name]
        # Test if parent category in search query
        response = self.client.get(
            reverse('shop:search'), {'q': category_names[-1]},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        for spec in response.context[views.SearchView.context_object_name]:
            self.assertIn(spec.category_name, category_names)
        # Test if subcategory in search query
        response = self.client.get(
            reverse('shop:search'), {'q': category_names[0]},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        for spec in response.context[views.SearchView.context_object_name]:
            self.assertEqual(spec.category_name, category_names[0])

    def test_product_search_result(self):
        """
        Returns the products that best match the user search query.
        """
        spec = Specification.objects.filter(
            available_qty__gt=0,
        ).last()
        product = spec.content_object
        self.assertIsNotNone(spec, msg='No spec in test db')
        q = (f'{product.category.name} {product.name} '
             f'{product.marking} {spec.tag}')
        response = self.client.get(reverse('shop:search'), {'q': q})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        spec_list = list(response.context[views.SearchView.context_object_name])
        self.assertTrue(spec_list)
        self.assertEqual(spec_list[0].id, spec.id)
        self.assertGreaterEqual(len(spec_list), product.specs.count())
