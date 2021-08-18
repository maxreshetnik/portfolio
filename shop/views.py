from decimal import Decimal

from django.urls import reverse
from django.http import Http404, HttpResponseRedirect
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.list import MultipleObjectMixin
from django.views.generic.detail import SingleObjectMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.db.models import (Prefetch, Avg, Subquery, Count,
                              OuterRef, F, When, Case, Sum)

from .models import Category, Specification, Rate, CartItem
from .forms import (CartItemForm, CustomUserCreationForm,
                    CustomUserChangeForm)


class CreateAccountView(LoginView):
    """
    Display the sing-up form and handle the action if success.
    """
    form_class = CustomUserCreationForm
    template_name = 'registration/sign_up.html'

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        form.save()
        return super().form_valid(form)


def get_rate_subquery():
    rates = Rate.objects.filter(
        content_type_id=OuterRef('content_type_id'),
        object_id=OuterRef('object_id'),
    ).order_by().values('object_id').annotate(Avg('point'))
    return Subquery(rates.values('point__avg'))


def get_product_model(ct_id):
    return ContentType.objects.get_for_id(ct_id).model_class()


def get_product_subquery(ct_id):
    model = get_product_model(ct_id)
    products = model.objects.filter(id=OuterRef('object_id'))
    return Subquery(products.order_by().values('category__name'))


def get_specs(queryset=None, ct_id=None):
    queryset = queryset if queryset is not None else (
        Specification.objects.filter(available_qty__gt=0)
    )
    rate_subquery = get_rate_subquery()
    if ct_id is not None:
        product_subquery = get_product_subquery(ct_id)
        queryset = queryset.filter(
            content_type_id=ct_id,
        ).annotate(category_name=product_subquery)

    queryset = queryset.annotate(rating=rate_subquery)
    prefetch = Prefetch('content_object', to_attr='product')
    return queryset.prefetch_related(prefetch)


class ShopView(TemplateView):

    template_name = 'shop/base.html'
    categories = Category.objects.prefetch_related(
        Prefetch('categories', to_attr='subcategories')
    )

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return HttpResponseRedirect(
                f'{reverse("shop:login")}?next={request.path}'
            )
        form = CartItemForm(request.POST, auto_id=False)
        if form.is_valid():
            spec_id = form.cleaned_data.pop('specification')
            if form.cleaned_data['quantity'] > 0:
                CartItem.objects.update_or_create(
                    user=request.user, specification=spec_id,
                    defaults=form.cleaned_data,
                )
            else:
                CartItem.objects.filter(
                    user=request.user, specification_id=spec_id,
                ).delete()
            return self.get(request, *args, **kwargs)
        else:
            context = self.get_context_data(form=form, **kwargs)
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['catalog'] = self.categories.filter(
            category__isnull=True,
        )
        if 'form' not in kwargs:
            context['form'] = CartItemForm(auto_id=False)
        if not self.request.user.is_authenticated:
            context['form_login'] = AuthenticationForm(label_suffix='')
            context['form_sign_up'] = CustomUserCreationForm(label_suffix='')
        elif 'cart' not in kwargs:
            context['cart'] = {
                obj.specification_id: obj.quantity for obj in
                CartItem.objects.filter(user=self.request.user)
            }
            context['rating_scale'] = [
                (n - 0.2, n - 0.75) for n in Rate.PointValue.values
            ]
        return context


class HomePageView(ShopView):

    template_name = 'shop/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['spec_list'] = get_specs().order_by('-id')[:4]
        return context


class CategorySpecList(MultipleObjectMixin, ShopView):

    template_name = 'shop/specs_by_category.html'
    context_object_name = 'spec_list'
    queryset = None
    object_list = None
    ordering = ('category_name', 'price')
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
        ordering = self.get_ordering()
        category = self.get_category()
        ct_id = category.content_type_id
        queryset = get_specs(self.queryset, ct_id)
        if not category.subcategories:
            self.kwargs['category'] = category.category
            queryset = queryset.filter(category_name=category.name)
            return queryset.order_by(*ordering)
        for sub in category.subcategories:
            if sub.content_type_id != ct_id:
                qs = get_specs(self.queryset, sub.content_type_id)
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

    ordering = ('-num_customers',)
    queryset = Specification.objects.filter(
        available_qty__gt=0,
    ).annotate(num_customers=Count('customers'))


class SpecificationDetail(SingleObjectMixin, ShopView):

    template_name = 'shop/spec_detail/spec.html'
    context_object_name = 'spec'
    object = None

    def get_queryset(self):
        queryset = Specification.objects.filter(pk=self.kwargs['pk'])
        return get_specs(queryset)

    def get_template_names(self):
        ct_id = getattr(self.object, 'content_type_id', '')
        return [f'shop/spec_detail/spec{ct_id}.html']

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context['spec_template_name'] = self.template_name
        return context


class CartView(LoginRequiredMixin, ShopView):

    login_url = '/shop/account/login/'
    template_name = 'shop/cart.html'

    def get_context_data(self, **kwargs):
        prefetch = Prefetch('content_object', to_attr='product')
        cart_query = CartItem.objects.filter(
            user=self.request.user, specification_id=OuterRef('id')
        )
        price_case = Case(
            When(sale_price__gt=0, then=F('sale_price')),
            When(discount__gt=0, then=F('discount_price')),
            default=F('price'),
        )
        queryset = Specification.objects.filter(
            customers=self.request.user,
        ).annotate(
            cart_qty=Subquery(cart_query.values('quantity')),
            item_id=Subquery(cart_query.values('id')),
            customer_price=price_case,
            total_price=F('customer_price') * F('cart_qty')
        ).prefetch_related(prefetch)
        cart_sum = queryset.aggregate(Sum('total_price'))['total_price__sum']
        kwargs['total_cart_price'] = cart_sum.quantize(Decimal('1.00'))
        kwargs['cart'] = queryset.order_by('-item_id')
        context = super().get_context_data(**kwargs)
        print(context['cart'])
        return context


class ProfileView(LoginRequiredMixin, ShopView):

    login_url = '/shop/account/login/'
    template_name = 'shop/profile.html'

    def post(self, request, *args, **kwargs):
        form = SetPasswordForm(
            request.user, request.POST, label_suffix='',
        )
        if form.is_valid():
            form.save()
            context = self.get_context_data(**kwargs)
            context['show_info'], context['show_success'] = '', 'show active'
            return self.render_to_response(context)
        else:
            context = self.get_context_data(form=form, **kwargs)
            context['show_info'], context['show_pas'] = '', 'show active'
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        if 'form' not in kwargs:
            kwargs['form'] = SetPasswordForm(
                self.request.user, label_suffix='',
            )
        kwargs['cart'] = CartItem.objects.filter(
            user=self.request.user
        ).count()
        context = super().get_context_data(**kwargs)
        context['show_info'] = 'show active'
        return context


class PersonalInfoView(ProfileView):

    template_name = 'shop/personal_info.html'

    def get(self, request, *args, **kwargs):
        kwargs['form_info'] = CustomUserChangeForm(
            instance=self.request.user
        )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = CustomUserChangeForm(
            request.POST, instance=request.user,
        )
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(f'{reverse("shop:profile")}')
        else:
            context = self.get_context_data(form_info=form, **kwargs)
            return self.render_to_response(context)
