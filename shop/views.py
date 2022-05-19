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
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.views.generic import TemplateView, FormView
from django.views.generic.edit import DeletionMixin
from django.views.generic.list import MultipleObjectMixin
from django.views.generic.detail import SingleObjectMixin
from django.urls import reverse, reverse_lazy
from django.utils import timezone

from .models import (
    Category, Specification, Rate, Order, OrderItem,
)
from .forms import (CustomUserCreationForm, CustomUserChangeForm,
                    PartialOrderItemForm, PartialOrderForm,
                    PartialRatingForm)


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


def get_specs(queryset=None, ct_id=None):
    """
    Returns specification queryset with product prefetched,
    filters if ContentType id of product model is passed.
    """
    queryset = queryset if queryset is not None else (
        Specification.objects.filter(available_qty__gt=0)
    )
    if ct_id is not None:
        queryset = queryset.filter(content_type_id=ct_id)
    prefetch = Prefetch('content_object', to_attr='product')
    queryset = queryset.select_related(
        'category__category',
    ).prefetch_related(prefetch)
    return queryset


def get_specs_with_rating(queryset):
    """Annotate specs objects with rating and number of rate"""
    rates = Rate.objects.filter(
        content_type_id=OuterRef('content_type_id'),
        object_id=OuterRef('object_id'),
    ).order_by().values('object_id')
    queryset = queryset.annotate(
        rating_avg=Subquery(
            rates.annotate(Avg('point')).values('point__avg'),
        ),
        rating_count=Subquery(
            rates.annotate(Count('user')).values('user__count'),
        ),
    )
    return queryset


class ShopView(TemplateView):
    """
    Base class for views, which displays products.

    If user is authenticated displays form for add and remove
    products in cart, other way form for login and sign-up.
    Provide category queryset with prefetched subcategories
    using for catalog and single category object.
    """
    template_name = 'shop/base.html'
    categories = Category.objects.prefetch_related(
        Prefetch('categories', to_attr='subcategories')
    )

    def post(self, request, *args, **kwargs):
        """
        Receives and handles data when user adds a product to cart.

        Passes data to be processed in the CartItemFormView.
        Add context data to response.
        """
        view = CartItemFormView.as_view(template_name=self.template_name)
        response = view(request, *args, **kwargs)
        if isinstance(response, self.response_class):
            self.extra_context = {'form': response.context_data['form']}
            response.context_data.update(self.get_context_data(**kwargs))
        return response

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
        context['form_rating'] = PartialRatingForm(auto_id=False)
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
        spec_qs = get_specs()
        spec_qs = get_specs_with_rating(spec_qs).order_by('-id')
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
        return get_specs_with_rating(qs)

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
    ordering = ('category__name', 'price')
    paginate_by = 2
    object_list = None

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
        Queryset for different product type are combined.
        """
        ordering = self.get_ordering()
        category = self.get_category()
        self.kwargs['category'] = category
        ct_id = category.content_type_id
        queryset = get_specs(queryset=self.queryset, ct_id=ct_id)
        if not category.subcategories:
            queryset = queryset.filter(category_id=category.id)
            queryset = get_specs_with_rating(queryset)
            return queryset.order_by(*ordering)
        queryset = get_specs_with_rating(queryset)
        for sub in category.subcategories:
            if sub.content_type_id != ct_id:
                qs = get_specs(self.queryset, sub.content_type_id)
                qs = get_specs_with_rating(qs)
                queryset = queryset.union(qs)
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
    Display product details, uses a custom template
    for different ContentTypes.
    """
    template_name = 'shop/spec_detail/spec.html'
    context_object_name = 'spec'
    object = None

    def post(self, request, *args, **kwargs):
        """
        Receive and handle data when user rate a product.

        Pass data to be processed in the RatingFormView.
        Add context data to response.
        """
        if 'point' in request.POST:
            view = RatingFormView.as_view(template_name=self.template_name)
            response = view(request, *args, **kwargs)
            if isinstance(response, self.response_class):
                context = self.get_context_data(**kwargs)
                context['form_rating'] = response.context_data['form']
                response.context_data.update(context)
            return response
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        queryset = get_specs(
            queryset=Specification.objects.filter(pk=self.kwargs['pk']),
        )
        if self.request.user.is_authenticated:
            rates = Rate.objects.filter(
                user_id=self.request.user.id,
                content_type_id=OuterRef('content_type_id'),
                object_id=OuterRef('object_id'),
            ).order_by()
            queryset = queryset.annotate(
                point=Subquery(rates.values('point')),
                review=Subquery(rates.values('review')),
            )
        return get_specs_with_rating(queryset)

    def get_template_names(self):
        t_names = super().get_template_names()
        model_name = self.object.content_type.model
        return [f'shop/spec_detail/spec_{model_name}.html'] + t_names

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context['spec_template_name'] = self.template_name
        context['rating_list'] = Rate.objects.filter(
            content_type_id=self.object.content_type_id,
            object_id=self.object.object_id,
        ).select_related('user').order_by('-id')[:10]
        return context


class CartView(LoginRequiredMixin, ShopView):
    """
    Display the items in the user cart and the total cost.
    """
    login_url = reverse_lazy('shop:login')
    template_name = 'shop/cart.html'

    def get_cart_items_with_specs(self) -> list:
        item_list = list(self.get_cart_items().annotate(
            total_price=F('price') * F('quantity'),
        ).select_related('order').order_by('-id'))
        if item_list:
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
            prefetch_related_objects(item_list, spec_prefetch)
        return item_list

    def get_context_data(self, **kwargs):
        """
        Extends the context by adding the user's cart with products.

        Check if items have changed in price or available qty
        and calculate the cost of the order.
        """
        item_list = self.get_cart_items_with_specs()
        num_in_cart, order_cost = 0, Decimal('0.00')
        msg = 'Some items have changed in price or available qty.'
        for item in item_list:
            if item.quantity > item.spec.available_qty:
                item.error_msg = (f'{item.spec.available_qty.normalize()} '
                                  f'in stock.')
                kwargs['error_msg'] = msg
            elif item.price != item.spec.best_price:
                item.error_msg = 're-add to cart or update quantity.'
                kwargs['error_msg'] = msg
            order_cost += item.total_price
            num_in_cart += 1
        kwargs.update({'order_cost': order_cost.quantize(Decimal('0.00')),
                       'num_in_cart': num_in_cart, 'cart': item_list})
        context = super().get_context_data(**kwargs)
        context['order'] = Order.objects.filter(
                user=self.request.user, status=Order.CART,
        ).first()
        context['messages'] = messages.get_messages(self.request)
        return context


class CartItemFormView(LoginRequiredMixin, FormView):
    """
    Add item to user cart, display items in cart on GET.

    Create the order with cart status if it doesn't exist.
    Instantiate a partial form with OrderItem instance.
    Return template or json response.
    """
    form_class = PartialOrderItemForm

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('shop:cart'))

    def get_login_url(self):
        return f'{reverse("shop:login")}?next={self.request.path}'

    def get_success_url(self):
        return self.request.get_full_path()

    def get_form_instance(self):
        """Provide instance for instantiating the form."""
        cart_order, create = Order.objects.get_or_create(
            user=self.request.user, status=Order.CART
        )
        return OrderItem(order=cart_order)

    def get_form_kwargs(self):
        """Provide OrderItem instance for instantiating the form."""
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'instance': self.get_form_instance(), 'auto_id': False,
        })
        return kwargs

    def get_success_json_response(self, obj):
        num_in_cart = OrderItem.objects.annotate(
            user_orders=FilteredRelation(
                'order', condition=Q(order__user_id=self.request.user.id),
            ),
        ).filter(user_orders__status=Order.CART).count()
        context = {
            'num_in_cart': num_in_cart,
            "success": ("The quantity of the item has changed." if
                        obj.quantity else "Item removed from cart."),
        }
        return JsonResponse(context, status=200)

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        obj = form.save()
        if self.request.is_ajax():
            return self.get_success_json_response(obj)
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
        return super().form_invalid(form)


class AccountView(LoginRequiredMixin, TemplateView):
    """
    Base class for views, which displays user personal menus.

    Provide category queryset for navbar catalog and
    number of items in cart.
    """
    template_name = 'shop/base.html'
    login_url = reverse_lazy('shop:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_num = OrderItem.objects.annotate(
            user_orders=FilteredRelation(
                'order', condition=Q(order__user_id=self.request.user.id),
            ),
        ).filter(user_orders__status=Order.CART).count()
        catalog = Category.objects.prefetch_related(
            Prefetch('categories', to_attr='subcategories'),
        ).filter(category__isnull=True)
        context.update({
            'cart': cart_num, 'catalog': catalog,
            'messages': messages.get_messages(self.request),
        })
        return context


class PlaceOrderView(AccountView):
    """
    Updates the user's order status from cart to processing and
    handles order data.
    """
    template_name = 'shop/order_placed.html'

    def post(self, request, **kwargs):
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
                return HttpResponseRedirect(reverse("shop:cart"))
        if form.has_error('order_cost', code='price'):
            messages.error(request, 'Some items have changed in price',
                           extra_tags='danger')
            return HttpResponseRedirect(reverse("shop:cart"))
        else:
            for error in form.errors.values():
                messages.warning(request, '\n'.join(error))
            return HttpResponseRedirect(reverse("shop:cart"))


class OrderListView(MultipleObjectMixin, AccountView):
    """Displays user orders."""
    template_name = 'shop/order_list.html'
    context_object_name = 'order_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.filter(
            user_id=self.request.user.id,
        ).exclude(status=Order.CART)
        return queryset

    def get_context_data(self, **kwargs):
        object_list = self.get_queryset()
        return super().get_context_data(object_list=object_list, **kwargs)


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

    def post(self, request, **kwargs):
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
            return HttpResponseRedirect(reverse("shop:profile"))
        else:
            context = self.get_context_data(form_info=form, **kwargs)
            return self.render_to_response(context)


class RatingListView(MultipleObjectMixin, AccountView):
    """Displays user ratings and reviews."""
    template_name = 'shop/rating_list.html'
    context_object_name = 'rating_list'
    paginate_by = 20
    ordering = ('id',)

    def post(self, request, *args, **kwargs):
        """
        Receives and handles data when a user rates a product.

        Passes data to be processed in the RatingFormView.
        Add context data to response.
        """
        view = RatingFormView.as_view(template_name=self.template_name)
        response = view(request, *args, **kwargs)
        if isinstance(response, self.response_class):
            response.context_data.update(
                self.get_context_data(**response.context_data)
            )
        return response

    def get_queryset(self):
        ordering = self.get_ordering()
        queryset = Rate.objects.filter(
            user_id=self.request.user.id,
        ).prefetch_related(Prefetch('content_object', to_attr='product'))
        return queryset.order_by(*ordering)

    def get_context_data(self, **kwargs):
        object_list = self.get_queryset()
        if 'form' not in kwargs:
            kwargs['form'] = PartialRatingForm(auto_id=False)
        return super().get_context_data(object_list=object_list, **kwargs)


class RatingFormView(CartItemFormView):
    """
    Update product rating and review, display ratings on GET.

    Instantiate a partial form with Rate model instance.
    Return template or json response.
    """
    template_name = 'shop/rating_list.html'
    form_class = PartialRatingForm

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('shop:rating_list'))

    def get_form_instance(self):
        """Provide instance for instantiating the form."""
        return Rate(user=self.request.user)

    def get_success_json_response(self, obj):
        context = Rate.objects.filter(
            content_type_id=obj.content_type_id,
            object_id=obj.object_id,
        ).aggregate(
            rating_avg=Avg('point'),
            rating_count=Count('user'),
        )
        context['success'] = 'Rating saved.'
        return JsonResponse(context, status=200)
