from http import HTTPStatus

from django.db.models import F, Q, Case, When, Sum, Count
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory, override_settings
from django.test import TransactionTestCase
from django.urls import reverse

from .. import views
from ..models import Specification, Order, Category, Rate


User = get_user_model()


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
        home_url = reverse('shop:home')
        self.request = self.factory.get(home_url)
        self.url = home_url

    def test_context_data(self):
        """Context data for all users include anonymous one"""
        n = views.HomePageView.number_of_specs
        self.assertGreaterEqual(
            len(self.specs), n,
            msg=f'There are less than {n} specifications in the test db.',
        )
        self.request.user = AnonymousUser()
        response = views.HomePageView.as_view()(self.request)
        self.assertIn('form', response.context_data)
        self.assertIn('form_rating', response.context_data)
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

    def test_get_home_page(self):
        """Display home page on GET."""
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_add_item_to_cart(self):
        """Logged-in user add items to his cart."""
        n = 2
        spec_list = list(self.specs[:n])
        self.assertGreaterEqual(
            len(spec_list), n, msg=f'Less than {n} specs in test db.',
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url, secure=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        num_in_cart = len(response.context['cart'])
        for spec in spec_list:
            num_in_cart += 1
            data = {'specification': spec.id, 'quantity': spec.pre_packing}
            response = self.client.post(
                self.url, data=data, secure=True, follow=True,
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertIn(spec.id, response.context['cart'])
            self.assertEqual(
                len(response.context['cart']), num_in_cart,
                msg=f'The number of items is not equal to {num_in_cart}.'
            )


class SearchViewTests(TestCase):

    fixtures = ['example_shop_data.json']

    def setUp(self):
        self.url = reverse('shop:search')

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
            self.url, {'q': category_names[-1]}, secure=True,
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
            self.url, {'q': category.name}, secure=True,
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
            self.url, {'q': q}, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        spec_list = list(
            response.context[views.SearchView.context_object_name]
        )
        self.assertTrue(
            spec_list, msg="The search didn't find any products.",
        )
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
            self.url, {'q': q}, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        spec_list = list(
            response.context[views.SearchView.context_object_name]
        )
        self.assertTrue(
            spec_list, msg="The search didn't find any products.",
        )
        self.assertEqual(
            spec_list[0].id, spec.id,
            msg=(f'"{spec}" should comes first on the list '
                 f'as best matching the query "{q}". '
                 f'Results: {", ".join(map(str, spec_list))}'),
        )


class CategorySpecListTests(TestCase):

    fixtures = ['example_shop_data.json']

    def setUp(self):
        self.category_qs = Category.objects.filter(
            category__isnull=True,
        )

    def test_get_category_page(self):
        """Display the same content type products from a category."""
        category = self.category_qs.exclude(
            Q(categories__content_type_id__lt=F('content_type_id')) |
            Q(categories__content_type_id__gt=F('content_type_id')),
        ).first()
        kwargs = {'category': str(category.name).lower()}
        response = self.client.get(
            reverse('shop:category', kwargs=kwargs),
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_context_data(self):
        """
        Context data for a page with a product list from a category.

        Context contains different content type products.
        """
        factory = RequestFactory()
        category = self.category_qs.filter(
            Q(categories__content_type_id__lt=F('content_type_id')) |
            Q(categories__content_type_id__gt=F('content_type_id')),
        ).first()
        self.assertIsNotNone(
            category, msg='the test data needs category with'
                          'different content type products.'
        )
        kwargs = {'category': str(category.name).lower()}
        request = factory.get(reverse('shop:category', kwargs=kwargs))
        request.user = AnonymousUser()
        view = views.CategorySpecList.as_view(paginate_by=None)
        response = view(request, **kwargs)
        self.assertIn('category', response.context_data)
        self.assertEqual(response.context_data['category'], category)
        self.assertIn('spec_list', response.context_data)
        n = Specification.objects.filter(
            available_qty__gt=0,
            category__category_id=category.id,
        ).count()
        spec_list = list(response.context_data['spec_list'])
        self.assertEqual(len(spec_list), n)


class SubcategorySpecListTests(TestCase):

    fixtures = ['example_shop_data.json']

    def setUp(self):
        self.category_qs = Category.objects.filter(
            category__isnull=False,
        ).select_related('category')

    def test_get_subcategory_page(self):
        """Display a product list from a subcategory."""
        category = self.category_qs.first()
        kwargs = {'category': str(category.category.name).lower(),
                  'subcategory': str(category.name).lower()}
        response = self.client.get(
            reverse('shop:subcategory', kwargs=kwargs),
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn('category', response.context)
        self.assertEqual(response.context['category'], category)


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
        spec = Specification.objects.select_related(
            'category__category',
        ).first()
        kwargs = {
            'category': str(spec.category.category.name).lower(),
            'subcategory': str(spec.category.name).lower(),
            'pk': str(spec.id),
        }
        self.url = reverse('shop:spec_detail', kwargs=kwargs)
        self.url_kwargs = kwargs
        self.spec = spec

    def test_get_template_names(self):
        """
        Method get_template_names() adds a product model name to
        a template name and returns a list of template names.
        """
        spec = self.spec
        kwargs = self.url_kwargs
        self.assertIsNotNone(spec, msg='No specification')
        request = self.factory.get(self.url)
        request.user = self.user
        response = views.SpecificationDetail.as_view()(request, **kwargs)
        t_name = f'shop/spec_detail/spec_{spec.content_type.model}.html'
        self.assertEqual(response.template_name[0], t_name)

    def test_context_data_with_rating_list(self):
        """
        Context data contains queryset with ratings from users.
        """
        spec = self.spec
        kwargs = self.url_kwargs
        rating_obj = Rate.objects.create(
            point=Rate.PointValue.one, review='test',
            user=self.user, object_id=spec.object_id,
            content_type_id=spec.content_type_id,
        )
        request = self.factory.get(self.url)
        request.user = self.user
        response = views.SpecificationDetail.as_view()(request, **kwargs)
        self.assertIn('rating_list', response.context_data)
        self.assertEqual(
            rating_obj, response.context_data['rating_list'].first(),
        )

    def test_get_spec_detail(self):
        """Display specification and product details on GET."""
        spec = self.spec
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn('spec', response.context_data)
        self.assertEqual(response.context_data['spec'].id, spec.id)
        self.assertTrue(
            hasattr(response.context_data['spec'], 'product'),
            msg='Product was not prefetched to spec attribute.',
        )

    def test_rate_and_review_product(self):
        """Logged-in user rate and review product on detail page."""
        spec = self.spec
        data = {'point': Rate.PointValue.one, 'review': 'test',
                'content_type': spec.content_type_id,
                'object_id': spec.object_id}
        self.assertFalse(
            Rate.objects.filter(user=self.user, **data).exists(),
            msg='The rating is already in the database.',
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, data=data, secure=True, follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Rate.objects.filter(user=self.user, **data).exists(),
            msg='The rating was not created in the database.',
        )

    def test_add_item_to_cart(self):
        """Logged-in user add product to cart on detail page."""
        spec = self.spec
        data = {'specification': spec.id,
                'quantity': spec.pre_packing}
        item = Order.specs.through.objects.filter(
            order__user=self.user, order__status=Order.CART, **data,
        )
        self.assertFalse(
            item.exists(), msg='The item is already in cart.',
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, data=data, secure=True, follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            item.exists(), msg='The item was not created in the database.',
        )


class CartViewTests(TestCase):

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
        cls.user = user

    def setUp(self):
        self.specs = Specification.objects.filter(
            available_qty__gt=0,
        )
        self.url = reverse('shop:cart')
        self.items = Order.specs.through.objects.filter(
            order_id=self.cart_order.id,
        )

    def test_get_cart_page(self):
        """Display cart items with order cost."""
        spec = self.specs.first()
        self.assertIsNotNone(spec, msg='No specification in test db.')
        item = Order.specs.through.objects.create(
            order=self.cart_order, specification=spec,
            quantity=spec.pre_packing, price=spec.price,
        )
        cart_aggr = self.cart_order.specs.annotate(
            best_price=Case(
                When(sale_price__gt=0, then=F('sale_price')),
                When(discount__gt=0, then=F('discount_price')),
                default=F('price'),
            ),
        ).aggregate(
            order_cost=Sum('best_price'), item_count=Count('id'),
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url, secure=True, follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        context = response.context
        self.assertIn(item, context['cart'])
        self.assertEqual(len(context['cart']), cart_aggr['item_count'])
        self.assertEqual(context['num_in_cart'], cart_aggr['item_count'])
        self.assertEqual(context['order'], self.cart_order)
        self.assertEqual(context['order_cost'], cart_aggr['order_cost'])


class CartItemFormViewTests(TestCase):

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
        cls.user = user

    def setUp(self):
        self.specs = Specification.objects.filter(
            available_qty__gt=0,
        ).order_by('-id')
        self.url = reverse('shop:add_to_cart')
        self.items = Order.specs.through.objects.filter(
            order_id=self.cart_order.id,
        )

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_add_to_cart_for_anonymous_user(self):
        """
        Only a logged-in user can add products to his cart,
        anonymous users will be redirected to the login page.
        """
        spec = self.specs[0]
        data = {'specification': spec.id,
                'quantity': spec.pre_packing}
        response = self.client.post(self.url, data=data)
        self.assertRedirects(
            response, f'{reverse("shop:login")}?next={self.url}'
        )

    def test_add_item_to_cart(self):
        """Logged-in user add items to his cart."""
        n = 2
        spec_list = list(self.specs[:n])
        self.assertGreaterEqual(
            len(spec_list), n, msg=f'Less than {n} specs in test db.',
        )
        self.client.force_login(self.user)
        for n, spec in enumerate(spec_list, 1):
            data = {'specification': spec.id,
                    'quantity': spec.pre_packing}
            item_qs = self.items.filter(specification=spec)
            self.assertFalse(
                item_qs.exists(), msg='The item is already in cart.',
            )
            response = self.client.post(
                self.url, data=data, secure=True, follow=True,
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertTrue(
                item_qs.filter(quantity=data['quantity']).exists(),
                msg=f'The {n} item was not created in the database.',
            )

    def test_change_cart_item_qty(self):
        """Change the item quantity in user cart."""
        spec = self.specs[0]
        qty = spec.pre_packing
        item = Order.specs.through.objects.create(
            order=self.cart_order, specification=spec,
            quantity=qty, price=spec.price,
        )
        self.client.force_login(self.user)
        data = {'quantity': qty + spec.pre_packing,
                'specification': spec.id}
        response = self.client.post(
            self.url, data=data, secure=True, follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        item.refresh_from_db()
        self.assertEqual(item.quantity, data['quantity'])

    def test_remove_item_from_cart(self):
        """Changing the quantity to zero remove an item from the cart."""
        spec = self.specs[0]
        defaults = {'quantity': spec.pre_packing, 'price': spec.price}
        self.cart_order.specs.add(spec, through_defaults=defaults)
        self.client.force_login(self.user)
        data = {'specification': spec.id, 'quantity': 0}
        response = self.client.post(
            self.url, data=data, secure=True, follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(self.items.filter(specification=spec).exists())


class RatingFormViewTests(TransactionTestCase):
    """
    Tests the creation or update of the rating for products.

    TransactionTestCase is used to correctly catch a database exception
    in the rating form.
    """
    fixtures = ['example_shop_data.json']

    def setUp(self):
        username, passwd = 'test', 'fdf24F42uih'
        self.user = User.objects.create_user(
            username=username, password=passwd,
        )
        spec = Specification.objects.first()
        self.data = {'point': Rate.PointValue.five, 'review': 'test',
                     'content_type': spec.content_type_id,
                     'object_id': spec.object_id}
        self.spec = spec
        self.url = reverse('shop:rate_product')

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_rate_product_by_anonymous_user(self):
        """
        Only a logged-in user can add rating for products,
        anonymous users will be redirected to the login page.
        """
        response = self.client.post(self.url, data=self.data)
        self.assertRedirects(
            response, f'{reverse("shop:login")}?next={self.url}'
        )

    def test_rate_and_review_product(self):
        """Logged-in user rate and review products."""
        data = self.data
        self.assertFalse(
            Rate.objects.filter(user=self.user, **data).exists(),
            msg='The rating is already in the database.',
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, data=data, secure=True, follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Rate.objects.filter(user=self.user, **data).exists(),
            msg='The rating was not created in the database.',
        )
        data.update({'point': Rate.PointValue.two})
        response = self.client.post(
            self.url, data=data, secure=True, follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Rate.objects.filter(user=self.user, **data).exists(),
            msg='The rating was not updated in the database.',
        )

    def test_change_product_rating(self):
        """Change product rating, review will not change."""
        spec = self.spec
        data = self.data
        review = data.pop('review', '')
        rating, created = Rate.objects.get_or_create(
            user=self.user, object_id=spec.object_id,
            content_type=spec.content_type,
            defaults={'point': Rate.PointValue.one, 'review': review},
        )
        factory = RequestFactory()
        for point in Rate.PointValue.values:
            data['point'] = point
            request = factory.post(self.url, data=data)
            request.user = self.user
            response = views.RatingFormView.as_view()(request, **data)
            self.assertEqual(response.status_code, HTTPStatus.FOUND)
            rating.refresh_from_db()
            self.assertEqual(rating.point, data['point'])
            self.assertEqual(
                rating.review, review, msg='The review should not change.',
            )


class CreateAccountViewTests(TestCase):

    def setUp(self):
        self.username = 'test'
        self.passwd = 'fdf24F42uih'

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
        username = self.username
        passwd = self.passwd
        response = self.client.post(
            reverse('shop:sign_up'),
            data={'username': username, 'password1': passwd,
                  'password2': passwd},
            secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(User.objects.filter(username='test').count(), 1)
        self.client.logout()
        self.assertTrue(
            self.client.login(username=username, password=passwd)
        )


class AccountViewTests(TestCase):

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

    def test_get_login_page(self):
        response = self.client.get(reverse('shop:login'), secure=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_user_login(self):
        """Send data to log in and redirect to next url with code 302."""
        data = {'username': self.username, 'password': self.passwd}
        response = self.client.post(
            reverse('shop:login'), data=data, secure=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_context_data(self):
        """
        Context data contains catalog and a number of items in cart.
        """
        cart = self.cart_order
        factory = RequestFactory()
        request = factory.get('')
        request.user = self.user
        spec = Specification.objects.filter(available_qty__gt=0).first()
        self.assertIsNotNone(spec, msg='No specification in test db.')
        defaults = {'quantity': spec.pre_packing, 'price': spec.price}
        cart.specs.add(spec, through_defaults=defaults)
        num_in_cart = cart.specs.count()
        response = views.AccountView.as_view()(request)
        self.assertIn('cart', response.context_data)
        self.assertIn('catalog', response.context_data)
        self.assertEqual(response.context_data['cart'], num_in_cart)
