from decimal import Decimal

from django.db.models import (
    Prefetch, FilteredRelation, Q, Subquery, OuterRef, Exists,
    Count, Avg, F, When, Case, prefetch_related_objects,
)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import (
    AuthenticationForm, SetPasswordForm,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector,
)
from django.http import Http404, HttpResponseRedirect
from django.views.generic import TemplateView
from django.views.generic.edit import DeletionMixin
from django.views.generic.list import MultipleObjectMixin
from django.views.generic.detail import SingleObjectMixin
from django.urls import reverse, reverse_lazy
from django.utils import timezone

from .models import (
    Category, Specification, Rate, Order, OrderItem,
)
from .forms import (CustomUserCreationForm, CustomUserChangeForm,
                    PartialOrderItemForm, PartialOrderForm)


class CreateAccountView(LoginView):
    """
    Display the sing-up form and handle the action if success.
    """
    form_class = CustomUserCreationForm
    template_name = 'registration/sign_up.html'

    def form_valid(self, form):
        """Form check complete. Saves the user then logs in."""
        form.save()
        return super().form_valid(form)


def get_rate_subquery():
    rates = Rate.objects.filter(
        content_type_id=OuterRef('content_type_id'),
        object_id=OuterRef('object_id'),
    ).order_by().values('object_id').annotate(Avg('point'))
    return Subquery(rates.values('point__avg'))


def get_specs(queryset=None, ct_id=None):
    """
    Returns an annotated and product prefetched specification queryset,
    filters if ContentType id of product model is passed.
    """
    queryset = queryset if queryset is not None else (
        Specification.objects.filter(available_qty__gt=0)
    )
    rate_subquery = get_rate_subquery()
    if ct_id is not None:
        queryset = queryset.filter(content_type_id=ct_id)
    prefetch = Prefetch('content_object', to_attr='product')
    queryset = queryset.annotate(rating=rate_subquery).select_related(
        'category__category',
    ).prefetch_related(prefetch)
    return queryset


class ShopView(TemplateView):
    """
    Base class for other views, contains navbar data.

    If user is authenticated displays form for add and remove
    products in cart, other way form for login and sign-up.

    Category queryset with prefetched subcategories are used for catalog and
    single category object in child classes.
    """
    template_name = 'shop/base.html'
    categories = Category.objects.prefetch_related(
        Prefetch('categories', to_attr='subcategories')
    )

    def post(self, request, *args, **kwargs):
        """
        Receives and handles form data when user adds a product to user cart.

        Saves the form if data is valid, creates order with
        cart status.
        """
        if not self.request.user.is_authenticated:
            return HttpResponseRedirect(
                f'{reverse("shop:login")}?next={request.path}'
            )
        order, create = Order.objects.get_or_create(
            user=request.user, status=Order.CART
        )
        form = PartialOrderItemForm(
            request.POST, auto_id=False, instance=OrderItem(order=order),
        )
        if form.is_valid():
            form.save()
            return self.render_to_response(self.get_context_data(**kwargs))
        else:
            context = self.get_context_data(form=form, **kwargs)
            return self.render_to_response(context)

    def get_cart_items(self):
        items = OrderItem.objects.annotate(user_orders=FilteredRelation(
            'order', condition=Q(order__user_id=self.request.user.id),
        )).filter(user_orders__status=Order.CART)
        return items

    def get_context_data(self, **kwargs):
        """
        Extends context data with catalog, cart items, scale to
        display rating stars, and unbound forms if needed.
        """
        context = super().get_context_data(**kwargs)
        context['catalog'] = self.categories.filter(
            category__isnull=True,
        )
        context['rating_scale'] = [
            (n - 0.2, n - 0.75) for n in Rate.PointValue.values
        ]
        if 'form' not in kwargs:
            context['form'] = PartialOrderItemForm(auto_id=False)
        if not self.request.user.is_authenticated:
            context['form_login'] = AuthenticationForm(
                auto_id='login_%s', label_suffix='',
            )
            context['form_sign_up'] = CustomUserCreationForm(
                auto_id='sign_up_%s', label_suffix='',
            )
        elif 'cart' not in kwargs:
            context['cart'] = {obj.specification_id: obj.quantity for
                               obj in self.get_cart_items()}
        return context


class HomePageView(ShopView):
    """
    Display the latest products on the home page.
    """
    template_name = 'shop/home.html'
    number_of_specs = 4

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        spec_qs = get_specs().order_by('-id')
        context['spec_list'] = spec_qs[:self.number_of_specs]
        return context


class SearchView(MultipleObjectMixin, ShopView):
    """
    Display the paginated list of products for a search query.

    Uses full-text search, first searches for matches in category names
    to narrow down the search, then for all product models.
    """
    template_name = 'shop/search.html'
    context_object_name = 'spec_list'
    ordering = ('-rank',)
    num_obj = 100
    q = None
    query = None
    object_list = None
    paginate_by = 20

    @staticmethod
    def get_category_vector() -> SearchVector:
        return SearchVector('name', config='english')
        
    @staticmethod
    def get_specs_vector() -> SearchVector:
        return SearchVector('tag', config='english')
        
    @staticmethod
    def get_products_vector() -> SearchVector:
        return SearchVector('name', 'marking', config='english')

    def get_category_search_rank(self):
        """Rank and filter category by search text"""
        query = self.query
        vector = self.get_category_vector()
        qs = self.categories.annotate(search=vector).filter(search=query)
        return qs.annotate(rank=SearchRank(vector, query))

    def get_products_search(self, ct_obj: ContentType):
        """Filter products by search text"""
        vector = self.get_products_vector()
        model = ct_obj.model_class()
        qs = model.objects.annotate(search=vector).filter(search=self.query)
        return qs

    def get_specs_search_rank(self, ct_obj: ContentType, cat_list=None):
        """Rank and filter specifications by search text"""
        query = self.query
        vector = self.get_specs_vector()
        qs_prod = self.get_products_search(ct_obj)
        product = qs_prod.filter(id=OuterRef('object_id'))
        product_rank = product.annotate(rank=SearchRank('search', query))
        qs = get_specs(ct_id=ct_obj.id).annotate(search=vector)
        if cat_list is None:
            qs = qs.filter(Q(Exists(product)) | Q(search=query))
        else:
            qs = qs.filter(category_id__in=cat_list)
        qs = qs.annotate(
            rank_prod=Subquery(product_rank.order_by().values('rank')), 
            rank_spec=SearchRank('search', query),
        ).annotate(rank=Case(
            When(rank_prod__isnull=True, then='rank_spec'),
            default=(F('rank_prod') + F('rank_spec')),
        ))
        return qs

    def search_in_category(self, category):
        """Search the query text in a specific category."""
        ct_obj = category.content_type
        cat_list = [category.id] + [c.id for c in category.subcategories]
        qs = self.get_specs_search_rank(ct_obj, cat_list=cat_list)
        for sub in category.subcategories:
            if sub.content_type_id != category.content_type_id:
                qs_other = self.get_specs_search_rank(
                    sub.content_type, cat_list=cat_list,
                )
                qs = qs.union(qs_other)
        return qs

    def search_in_products(self):
        """Search the query text in all product models"""
        ct_list = list(ContentType.objects.filter(model__iendswith='product'))
        search_list = [
            ct for ct in ct_list if self.get_products_search(ct).exists()
        ]
        if not search_list:
            id_list = Specification.objects.annotate(
                search=self.get_specs_vector()
            ).filter(search=self.query).order_by().distinct(
                'content_type_id'
            ).values_list(
                'content_type_id', flat=True
            )
            search_list = [ContentType.objects.get_for_id(i) for i in id_list]
        if search_list:
            ct_obj = search_list.pop()
            qs = self.get_specs_search_rank(ct_obj)
            for obj in search_list:
                qs = qs.union(self.get_specs_search_rank(obj))
        else:
            qs = self.get_specs_search_rank(ct_list[0]).none()
        return qs

    def get_queryset(self):
        if not self.q:
            return Specification.objects.none()
        ordering = self.get_ordering()
        query = SearchQuery(self.q[0])
        for s in self.q[1:]:
            query |= SearchQuery(s)
        self.query = query
        category_qs = self.get_category_search_rank()
        try:
            category = category_qs.order_by('-rank')[0]
        except IndexError:
            qs = self.search_in_products()
        else:
            qs = self.search_in_category(category)
        return qs.order_by(*ordering)[:self.num_obj]

    def get_context_data(self, **kwargs):
        q_string = self.request.GET.get('q', '')
        self.q = q_string.split()
        self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        context.update({
            'q': q_string, 'url_keys': f'&q={"+".join(self.q)}',
            'empty_msg': f'No products were found for "{q_string}".',
        })
        return context


class CategorySpecList(MultipleObjectMixin, ShopView):
    """
    Display a paginated list of products for the selected category.
    """
    template_name = 'shop/specs_by_category.html'
    context_object_name = 'spec_list'
    queryset = None
    object_list = None
    ordering = ('category__name', 'price')
    paginate_by = 2

    def get_category(self):
        try:
            category = self.categories.get(
                category__isnull=True,
                name__iexact=self.kwargs['category'],
            )
        except Category.DoesNotExist:
            raise Http404("No category matches the given name.")
        return category

    def get_queryset(self):
        """
        Returns a queryset for a specification model that links all products
        through the ContentType field.

        Object of the specification has the attribute
        product to which it belongs.
        Queryset for different products are combined.
        """
        ordering = self.get_ordering()
        category = self.get_category()
        ct_id = category.content_type_id
        queryset = get_specs(self.queryset, ct_id)
        queryset = queryset.select_related(None).select_related('category')
        if not category.subcategories:
            self.kwargs['category'] = category.category
            queryset = queryset.filter(category_id=category.id)
            return queryset.order_by(*ordering)
        for sub in category.subcategories:
            if sub.content_type_id != ct_id:
                qs = get_specs(self.queryset, sub.content_type_id)
                qs = qs.select_related(None).select_related('category')
                queryset = queryset.union(qs)
        self.kwargs['category'] = category
        return queryset.order_by(*ordering)

    def get_context_data(self, **kwargs):
        self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        context['category'] = self.kwargs['category']
        return context


class SubcategorySpecList(CategorySpecList):

    ordering = ('price',)

    def get_category(self):
        category = self.categories.filter(
            name__iexact=self.kwargs['subcategory'],
        ).select_related('category')
        try:
            category = category.get()
        except Category.DoesNotExist:
            raise Http404("No subcategory matches the given name.")
        return category


class NewArrivalSpecList(CategorySpecList):

    ordering = ('-date_added',)
    new_date = timezone.now().date() - timezone.timedelta(days=14)
    queryset = Specification.objects.filter(
        date_added__gte=new_date, available_qty__gt=0,
    )


class PopularSpecList(CategorySpecList):

    ordering = ('-num_orders',)
    queryset = Specification.objects.filter(
        available_qty__gt=0,
    ).annotate(num_orders=Count('order')).filter(num_orders__gt=0)


class SpecificationDetail(SingleObjectMixin, ShopView):
    """
    Display product details, uses a custom template for different ContentTypes.
    """
    template_name = 'shop/spec_detail/spec.html'
    context_object_name = 'spec'
    object = None

    def get_queryset(self):
        queryset = Specification.objects.filter(pk=self.kwargs['pk'])
        return get_specs(queryset)

    def get_template_names(self):
        t_names = super().get_template_names()
        model_name = self.object.content_type.model
        return [f'shop/spec_detail/spec_{model_name}.html'] + t_names

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context['spec_template_name'] = self.template_name
        return context


class CartView(LoginRequiredMixin, ShopView):
    """
    Display the items in the user cart and the total cost.
    """
    login_url = reverse_lazy('shop:login')
    template_name = 'shop/cart.html'

    def get_context_data(self, **kwargs):
        """
        Extends the context by adding the user's cart with products.

        Check if items have changed in price or available qty
        and calculate the cost of the order.
        """
        items = self.get_cart_items().annotate(
            total_price=F('price') * F('quantity'),
        ).select_related('order').order_by('-id')
        kwargs.update({'num_in_cart': 0, 'cart': list(items),
                       'order_cost': Decimal('0.00')})
        if not kwargs['cart']:
            return super().get_context_data(**kwargs)

        price_case = Case(
            When(sale_price__gt=0, then=F('sale_price')),
            When(discount__gt=0, then=F('discount_price')),
            default=F('price'),
        )
        spec_queryset = Specification.objects.annotate(
            best_price=price_case,
        ).select_related('category__category').prefetch_related(
            Prefetch('content_object', to_attr='product'),
        )
        spec_prefetch = Prefetch(
            'specification', queryset=spec_queryset, to_attr='spec',
        )
        prefetch_related_objects(kwargs['cart'], spec_prefetch)
        msg = 'Some items have changed in price or available qty.'
        for item in kwargs['cart']:
            if item.quantity > item.spec.available_qty:
                item.error_msg = (f'{item.spec.available_qty.normalize()} '
                                  f'in stock.')
                kwargs['error_msg'] = msg
            elif item.price != item.spec.best_price:
                item.error_msg = 're-add to cart or update quantity.'
                kwargs['error_msg'] = msg
            kwargs['order_cost'] += item.total_price
            kwargs['num_in_cart'] += 1
        kwargs['order_cost'] = kwargs['order_cost'].quantize(Decimal('0.00'))

        context = super().get_context_data(**kwargs)
        context['order'] = kwargs['cart'][0].order
        context['messages'] = messages.get_messages(self.request)
        return context


class AccountView(LoginRequiredMixin, ShopView):

    login_url = reverse_lazy('shop:login')

    def get_context_data(self, **kwargs):
        kwargs['cart'] = self.get_cart_items().count()
        context = super().get_context_data(**kwargs)
        context['messages'] = messages.get_messages(self.request)
        return context


class PlaceOrderView(AccountView):
    """
    Updates the user's order status from cart to processing and
    handles order data.
    """
    template_name = 'shop/order_placed.html'

    def post(self, request, *args, **kwargs):
        try:
            order = Order.objects.get(
                user=request.user, status=Order.CART,
            )
        except Order.DoesNotExist:
            empty_msg = ('There are no items in your order, '
                         'add a product to your cart.')
            kwargs['cart_is_empty'] = empty_msg
            return self.render_to_response(self.get_context_data(**kwargs))
        order.status = Order.PROCESSING
        form = PartialOrderForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            if order.reserved:
                kwargs.update({'success_info': 'Order placed successfully.',
                               'order': order})
                context = self.get_context_data(**kwargs)
                return self.render_to_response(context)
            else:
                msg = 'Quantity is not available for some items'
                messages.error(request, msg, extra_tags='danger')
                return HttpResponseRedirect(f'{reverse("shop:cart")}')
        if form.has_error('order_cost', code='price'):
            messages.error(request, 'Some items have changed in price',
                           extra_tags='danger')
            return HttpResponseRedirect(f'{reverse("shop:cart")}')
        else:
            for error in form.errors.values():
                messages.warning(request, '\n'.join(error))
            return HttpResponseRedirect(f'{reverse("shop:cart")}')

    def get_context_data(self, **kwargs):
        kwargs['form'] = ''
        context = super().get_context_data(**kwargs)
        return context


class OrderListView(MultipleObjectMixin, AccountView):
    """Displays user orders."""
    template_name = 'shop/order_list.html'
    context_object_name = 'order_list'
    object_list = None
    paginate_by = 2
    queryset = None

    def get_queryset(self):
        queryset = Order.objects.filter(
            user_id=self.request.user.id,
        ).exclude(status=Order.CART)
        return queryset

    def get_context_data(self, **kwargs):
        self.object_list = self.get_queryset()
        kwargs['form'] = ''
        context = super().get_context_data(**kwargs)
        return context


class OrderDetailView(SingleObjectMixin, AccountView):
    """Displays order details and provides the ability to change
    order status and handle available qty."""
    template_name = 'shop/order_detail.html'
    context_object_name = 'order'
    object = None

    def get_queryset(self):
        queryset = Order.objects.filter(
            user_id=self.request.user.id,
        ).exclude(status=Order.CART)
        return queryset

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        spec_queryset = Specification.objects.select_related(
            'category__category',
        ).prefetch_related(
            Prefetch('content_object', to_attr='product'),
        )
        spec_prefetch = Prefetch(
            'specification', queryset=spec_queryset, to_attr='spec',
        )
        kwargs['items'] = self.object.orderitem_set.annotate(
            total_price=F('price') * F('quantity'),
        ).prefetch_related(spec_prefetch)
        context = self.get_context_data(object=self.object, **kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Changes the user's order status to 'confirmed' or 'canceled'.

        If the order has not been shipped, the available quantity of
        each product is increased.
        """
        self.object = self.get_object()
        if self.object.status < self.object.SHIPPING:
            self.object.status = self.object.CANCELED
            self.object.save()
            messages.info(request, 'Your order has been canceled.')
        elif self.object.status == self.object.SHIPPING:
            self.object.status = self.object.FINISHED
            self.object.save()
            messages.info(request, 'Confirmed.')
        if next_url := request.POST.get('next', ''):
            return HttpResponseRedirect(next_url)
        context = self.get_context_data(object=self.object, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        kwargs['form'] = ''
        context = super().get_context_data(**kwargs)
        return context


class OrderDeleteView(DeletionMixin, OrderDetailView):
    """Provides the ability to delete an order."""
    success_url = reverse_lazy('shop:order_list')


class ProfileView(AccountView):
    """
    Displays user personal information on the account page and
    manages the password change form.
    """
    template_name = 'shop/profile.html'

    def post(self, request, *args, **kwargs):
        form = SetPasswordForm(
            request.user, request.POST, label_suffix='',
        )
        if form.is_valid():
            form.save()
            context = self.get_context_data(**kwargs)
            messages.success(request, 'Password changed.')
        else:
            context = self.get_context_data(form=form, **kwargs)
        context['show_info'], context['show_pas'] = '', 'show active'
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        if 'form' not in kwargs:
            kwargs['form'] = SetPasswordForm(
                self.request.user, label_suffix='',
            )
        context = super().get_context_data(**kwargs)
        context['show_info'] = 'show active'
        return context


class PersonalInfoView(ProfileView):
    """
    Displays and manages the form for changing the user's personal information.
    """
    template_name = 'shop/personal_info.html'

    def get(self, request, *args, **kwargs):
        form = CustomUserChangeForm(instance=self.request.user)
        context = self.get_context_data(form_info=form, **kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = CustomUserChangeForm(
            request.POST, instance=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Personal information changed.')
            return HttpResponseRedirect(f'{reverse("shop:profile")}')
        else:
            context = self.get_context_data(form_info=form, **kwargs)
            return self.render_to_response(context)
