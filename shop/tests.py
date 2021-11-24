from decimal import Decimal
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory
from django.urls import reverse

from . import views
from .models import Specification, Order


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
        self.spec = Specification.objects.filter(
            available_qty__gt=0,
        ).order_by('-id').first()
        self.request = self.factory.get(reverse('shop:home'))

    def test_context_data(self):
        self.assertIsNotNone(self.spec, msg='No specification')
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
        self.assertEqual(len(spec_list), 4)
        self.assertEqual(spec_list[0], self.spec.id)

    def test_cart_context_data(self):
        self.assertIsNotNone(self.spec, msg='No specification')
        self.request.user = self.user
        response = views.HomePageView.as_view()(self.request)
        self.assertIn('cart', response.context_data)
        self.assertFalse(response.context_data['cart'])
        order = Order.objects.create(
            user=self.user, status=Order.CART
        )
        defaults = {'quantity': Decimal('1'), 'price': self.spec.price}
        order.specs.add(self.spec, through_defaults=defaults)
        response = views.HomePageView.as_view()(self.request)
        self.assertDictEqual(
            response.context_data['cart'],
            {self.spec.id: defaults['quantity']}
        )

    def test_add_to_cart(self):
        data = {'specification': self.spec.id,
                'quantity': self.spec.pre_packing}
        response = self.client.post(reverse('shop:home'), data=data)
        self.assertRedirects(
            response, f'{reverse("shop:login")}?next={reverse("shop:home")}'
        )
        self.assertTrue(
            self.client.login(username=self.username, password=self.passwd)
        )
        for _ in range(2):
            response = self.client.post(reverse('shop:home'), data=data)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertEqual(len(response.context['cart']), 1)
            self.assertEqual(response.context['cart'][self.spec.id],
                             data['quantity'])
            data['quantity'] += self.spec.pre_packing
        data['quantity'] = 0
        response = self.client.post(reverse('shop:home'), data=data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(response.context['cart'])


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
