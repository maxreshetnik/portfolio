from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import TemplateView, DetailView
from django.views.generic.list import MultipleObjectMixin
from django.views.generic.detail import SingleObjectMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import (Prefetch, F, Min, Max, Avg,
                              Subquery, Count, OuterRef, Exists)

from .models import Category, Specification, Rate, Cart
from .forms import CartForm


def layout_view(request):
    return render(request, 'shop/layout.html', {})


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

    template_name = 'shop/home.html'
    category = Category.objects.prefetch_related(
        Prefetch('categories', to_attr='subcategories')
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['navbar_template_name'] = 'shop/navbar/navbar.html'
        context['rating_scale'] = [(n - 0.2, n - 0.75) for n in
                                   Rate.PointValue.values]
        context['catalog'] = self.category.filter(
            category__isnull=True,
        )
        context['num_in_cart'] = Cart.objects.filter(
            user=self.request.user,
        ).count() if self.request.user.is_authenticated else 0
        return context


class HomePageView(ShopView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['spec_list'] = get_specs().order_by('-id')[:4]
        return context


class CategorySpecList(MultipleObjectMixin, ShopView):

    template_name = 'shop/specs_by_category.html'
    context_object_name = 'spec_list'
    queryset = None
    object_list = None
    # paginate_by = 5

    def get_category(self):
        try:
            category = self.category.get(
                category__isnull=True,
                name__iexact=self.kwargs['category'],
            )
        except Category.DoesNotExist:
            raise Http404("No category matches the given name.")
        return category

    def get_queryset(self):

        category = self.get_category()
        ct_id = category.content_type_id
        queryset = get_specs(self.queryset, ct_id)
        if not category.subcategories:
            self.kwargs['category'] = category.category
            return queryset.filter(category_name=category.name)
        for sub in category.subcategories:
            if sub.content_type_id != ct_id:
                qs = get_specs(self.queryset, sub.content_type_id)
                queryset = queryset.union(qs)
        self.kwargs['category'] = category
        return queryset

    def get_context_data(self, **kwargs):
        self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        context['category'] = self.kwargs['category']
        return context


class SubcategorySpecList(CategorySpecList):

    def get_category(self):
        category = self.category.filter(
            name__iexact=self.kwargs['subcategory'],
        ).select_related('category')
        try:
            category = category.get()
        except Category.DoesNotExist:
            raise Http404("No subcategory matches the given name.")
        return category


class NewArrivalsSpecList(CategorySpecList):

    new_date = timezone.now().date() - timezone.timedelta(days=14)
    queryset = Specification.objects.filter(
        date_added__gte=new_date, available_qty__gt=0,
    ).order_by('-date_added')


class PopularSpecList(CategorySpecList):

    queryset = Specification.objects.filter(
        available_qty__gt=0,
    ).annotate(
        num_customers=Count('customers'),
    ).order_by('-num_customers')


class SpecificationDetail(SingleObjectMixin, ShopView):

    template_name = 'shop/spec_detail/spec.html'
    context_object_name = 'spec'
    object = None

    def get_queryset(self):
        prefetch = Prefetch('content_object', to_attr='product')
        queryset = Specification.objects.annotate(
            rating=get_rate_subquery(),
        ).prefetch_related(prefetch)
        return queryset

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context['spec_template_name'] = self.template_name
        context['form'] = CartForm()
        return context

    def get_template_names(self):
        ct_id = getattr(self.object, 'content_type_id', 0)
        return [f'{self.template_name[:-5]}_{ct_id}.html',
                self.template_name]


class ProductList(MultipleObjectMixin, ShopView):

    template_name = 'shop/products_by_category.html'
    context_object_name = 'product_list'
    object_list = None

    def get_queryset(self):
        category = Category.objects.select_related('category')
        category = category.prefetch_related(
            Prefetch('categories', to_attr='subcategories'),
        )
        try:
            category = category.get(
                name__iexact=self.kwargs['category'],
            )
        except Category.DoesNotExist:
            raise Http404("No category matches the given name.")
        self.kwargs['category'] = category

        product_model = ContentType.objects.get_for_id(
            category.content_type_id
        ).model_class()

        queryset = product_model.objects.filter(
            specs__available_qty__gt=0,
        ).select_related('category')

        if not category.subcategories:
            queryset = queryset.filter(category_id=category.id)
        # elif category.category_id is not None:
        #     queryset = queryset.filter(
        #         category__in=category.subcategories
        #     )
        # specs = Specification.objects.filter(
        #     content_type_id=category.content_type_id,
        # ).annotate(
        #     min_price=Case(
        #         When(discount_price__gt=0, then='discount_price'),
        #         default='price'
        #     ),
        # ).order_by('discount_price')
        #
        spec_sale = Specification.objects.filter(
            object_id=OuterRef('pk'),
            discount_price__lt=F('price')
        )

        queryset = queryset.annotate(
            min_discount_price=Min('specs__discount_price'),
            min_price=Min('specs__price'),
            max_discount_price=Max('specs__discount_price'),
            specs_count=Count('specs'),
            sale=Exists(spec_sale),
            rating=Avg('rates__point'),
        )
        # for q in queryset:
        #     print(q.min_discount_price)
        #     print(q.min_price)
        #     print(q.max_discount_price)
        #     print(q.sale)

        return queryset

    def get_context_data(self, **kwargs):
        self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        context['category'] = self.kwargs['category']
        return context


class ProductDetail(DetailView):
    pass
