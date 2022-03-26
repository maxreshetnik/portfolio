from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

from .. import views
from ..models import Specification, Order, Category


User = get_user_model()


class CreateAccountViewTests(TestCase):

    def test_get_sign_up_page(self):
        response = self.client.get(reverse('shop:sign_up'), secure=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'registration/sign_up.html')

    def test_user_create_account(self):
        """
        Send data to create account and try to log in.

        CreateAccountView redirects to next url if data is valid,
        response status code 302.
        """
        username = 'test'
        passwd = 'fdf24F42uih'
        response = self.client.post(
            reverse('shop:sign_up'),
            data={'username': username, 'password1': passwd,
                  'password2': passwd},
            secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(User.objects.filter(username='test').count(), 1)
        self.client.logout()
        self.assertTrue(self.client.login(username=username, password=passwd))


class HomePageViewTests(TestCase):

    fixtures = ['example_shop_data.json']

    @classmethod
    def setUpTestData(cls):
        username, passwd = 'test', 'fdf24F42uih'
        user = User.objects.create_user(
            username=username, password=passwd,
        )
        cls.cart_order = Order.objects.create(
            user=user, status=Order.CART,
        )
        cls.username = username
        cls.passwd = passwd
        cls.user = user

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

        A user cart is the instance of Order model with a cart status.
        First check if there are no items in the cart, then add item.
        """
        spec = self.specs.first()
        self.assertIsNotNone(spec, msg='No specification')
        self.request.user = self.user
        response = views.HomePageView.as_view()(self.request)
        self.assertIn('cart', response.context_data)
        self.assertFalse(response.context_data['cart'])
        defaults = {'quantity': spec.pre_packing, 'price': spec.price}
        self.cart_order.specs.add(spec, through_defaults=defaults)
        response = views.HomePageView.as_view()(self.request)
        self.assertIsInstance(response.context_data['cart'], dict)
        self.assertIn((spec.id, defaults['quantity']),
                      response.context_data['cart'].items())

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_add_to_cart_for_anonymous_user(self):
        """
        Only a logged-in user can add products to his cart,
        anonymous users will be redirected to the login page.
        """
        spec = self.specs[0]
        data = {'specification': spec.id,
                'quantity': spec.pre_packing}
        response = self.client.post(reverse('shop:home'), data=data)
        self.assertRedirects(
            response, f'{reverse("shop:login")}?next={reverse("shop:home")}'
        )

    def test_add_item_to_cart(self):
        """Logged-in user add items to his cart."""
        n = 2
        spec_list = list(self.specs[:n])
        self.assertGreaterEqual(
            len(spec_list), n, msg=f'Less than {n} specs in test db.',
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('shop:home'), secure=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        num_in_cart = len(response.context['cart'])
        for spec in spec_list:
            num_in_cart += 1
            response = self.client.post(
                reverse('shop:home'),
                data={'specification': spec.id,
                      'quantity': spec.pre_packing},
                secure=True,
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertIn(spec.id, response.context['cart'])
            self.assertEqual(
                len(response.context['cart']), num_in_cart,
                msg=f'The number of items is not equal to {num_in_cart}.'
            )

    def test_change_cart_item_qty(self):
        """Change the item quantity in user cart."""
        spec = self.specs[0]
        qty = spec.pre_packing
        defaults = {'quantity': qty, 'price': spec.price}
        self.cart_order.specs.add(spec, through_defaults=defaults)
        self.client.force_login(self.user)
        data = {'specification': spec.id, 'quantity': qty + spec.pre_packing}
        response = self.client.post(
            reverse('shop:home'), data=data, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        cart = response.context['cart']
        self.assertEqual(cart.get(spec.id), data['quantity'])

    def test_remove_item_from_cart(self):
        """Changing the quantity to zero remove an item from the cart."""
        spec = self.specs[0]
        defaults = {'quantity': spec.pre_packing, 'price': spec.price}
        self.cart_order.specs.add(spec, through_defaults=defaults)
        self.client.force_login(self.user)
        data = {'specification': spec.id, 'quantity': 0}
        response = self.client.post(
            reverse('shop:home'), data=data, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotIn(spec.id, response.context['cart'])
        self.assertFalse(self.cart_order.specs.filter(pk=spec.id).exists())


class SpecificationDetailTests(TestCase):

    fixtures = ['example_shop_data.json']

    @classmethod
    def setUpTestData(cls):
        username, passwd = 'test', 'fdf24F42uih'
        cls.username = username
        cls.passwd = passwd
        cls.user = User.objects.create_user(
            username=username, password=passwd,
        )

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_template_names(self):
        """
        Method get_template_names() adds a product model name to
        a template name and returns a list of template names.
        """
        spec = Specification.objects.select_related(
            'category__category',
        ).first()
        self.assertIsNotNone(spec, msg='No specification')
        category = spec.category
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

    fixtures = ['example_shop_data.json']

    def test_parent_category_search_result(self):
        """
        Returns all products from the parent category whose name
        was specified in the user search query.
        """
        category = Category.objects.filter(
            category__isnull=True,
        ).first()
        self.assertIsNotNone(category, msg='No category in test db')
        category_names = list(
            category.categories.order_by().values_list('name', flat=True)
        ) + [category.name]
        response = self.client.get(
            reverse('shop:search'), {'q': category_names[-1]}, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        for spec in response.context[views.SearchView.context_object_name]:
            self.assertIn(spec.category.name, category_names)

    def test_category_search_result(self):
        """
        Returns all products from the category whose name
        was specified in the user search query.
        """
        spec = Specification.objects.filter(
            available_qty__gt=0,
        ).select_related('category').last()
        self.assertIsNotNone(spec, msg='No spec in test db')
        category = spec.category
        response = self.client.get(
            reverse('shop:search'), {'q': category.name}, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        for spec in response.context[views.SearchView.context_object_name]:
            self.assertEqual(spec.category.name, category.name)

    def test_category_and_product_search_result(self):
        """
        Returns the product that was specified in the user search query.
        """
        spec = Specification.objects.filter(
            available_qty__gt=0,
        ).last()
        self.assertIsNotNone(spec, msg='No spec in test db')
        product = spec.content_object
        q = (f'{product.category.name} {product.name} '
             f'{product.marking}')
        response = self.client.get(
            reverse('shop:search'), {'q': q}, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        spec_list = list(
            response.context[views.SearchView.context_object_name]
        )
        self.assertTrue(spec_list, msg="The search didn't find any products.")
        self.assertEqual(
            spec_list[0].object_id, product.id,
            msg=(f'"{product}" should comes first on the list '
                 f'as best matching the query "{q}". '
                 f'Results: {", ".join(map(str, spec_list))}'),
        )

    def test_product_search_result(self):
        """
        Returns the products that best match the user search query
        without specifying a category.
        """
        spec = Specification.objects.filter(
            available_qty__gt=0,
        ).last()
        self.assertIsNotNone(spec, msg='No spec in test db')
        product = spec.content_object
        q = f'{product.name} {product.marking} {spec.tag}'
        response = self.client.get(
            reverse('shop:search'), {'q': q}, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        spec_list = list(
            response.context[views.SearchView.context_object_name]
        )
        self.assertTrue(spec_list, msg="The search didn't find any products.")
        self.assertEqual(
            spec_list[0].id, spec.id,
            msg=(f'"{spec}" should comes first on the list '
                 f'as best matching the query "{q}". '
                 f'Results: {", ".join(map(str, spec_list))}'),
        )
