# @register.simple_tag
# def cart_qty(instance, cart):
#     """
#     Returns cart quantity or pre_packing.
#     """
#     return cart.get(instance.id, instance.pre_packing).normalize()
#
#
# @register.filter
# def decimal_normalize(value):
#     """
#     Normalize decimal value like cut zero ending.
#     """
#     return value.normalize()
#
#
# @register.filter
# def has_item(cart, key):
#     return cart.get(key, False)


# class ProductList(MultipleObjectMixin, ShopView):
#
#     template_name = 'shop/products_by_category.html'
#     context_object_name = 'product_list'
#     object_list = None
#
#     def get_queryset(self):
#         category = Category.objects.select_related('category')
#         category = category.prefetch_related(
#             Prefetch('categories', to_attr='subcategories'),
#         )
#         try:
#             category = category.get(
#                 name__iexact=self.kwargs['category'],
#             )
#         except Category.DoesNotExist:
#             raise Http404("No category matches the given name.")
#         self.kwargs['category'] = category
#
#         product_model = ContentType.objects.get_for_id(
#             category.content_type_id
#         ).model_class()
#
#         queryset = product_model.objects.filter(
#             specs__available_qty__gt=0,
#         ).select_related('category')
#
#         if not category.subcategories:
#             queryset = queryset.filter(category_id=category.id)
#         # elif category.category_id is not None:
#         #     queryset = queryset.filter(
#         #         category__in=category.subcategories
#         #     )
#         # specs = Specification.objects.filter(
#         #     content_type_id=category.content_type_id,
#         # ).annotate(
#         #     min_price=Case(
#         #         When(discount_price__gt=0, then='discount_price'),
#         #         default='price'
#         #     ),
#         # ).order_by('discount_price')
#         #
#         spec_sale = Specification.objects.filter(
#             object_id=OuterRef('pk'),
#             discount_price__lt=F('price')
#         )
#
#         queryset = queryset.annotate(
#             min_discount_price=Min('specs__discount_price'),
#             min_price=Min('specs__price'),
#             max_discount_price=Max('specs__discount_price'),
#             specs_count=Count('specs'),
#             sale=Exists(spec_sale),
#             rating=Avg('rates__point'),
#         )
#         # for q in queryset:
#         #     print(q.min_discount_price)
#         #     print(q.min_price)
#         #     print(q.max_discount_price)
#         #     print(q.sale)
#
#         return queryset
#
#     def get_context_data(self, **kwargs):
#         self.object_list = self.get_queryset()
#         context = super().get_context_data(**kwargs)
#         context['category'] = self.kwargs['category']
#         return context
#
#
# class ProductDetail(DetailView):
#     pass