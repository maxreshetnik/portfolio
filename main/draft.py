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


# class CartItem(models.Model):
#     """
#     Creates intermediate table for ManyToMany field in Specification model and user one.
#
#     The table has a unique constraint on the specification and
#     user fields to prevent duplicate rows.
#     """
#     specification = models.ForeignKey(
#         Specification, on_delete=models.CASCADE,
#     )
#     user = models.ForeignKey(USER, on_delete=models.CASCADE)
#     quantity = models.DecimalField(
#         max_digits=6, decimal_places=3,
#         validators=[MinValueValidator(Decimal('0'))],
#     )
#
#     class Meta:
#         verbose_name_plural = 'cart'
#         constraints = [
#             models.UniqueConstraint(fields=['specification', 'user'],
#                                     name='user_item_unique'),
#         ]
#
#     def __str__(self):
#         return f"{self.specification} {self.quantity}"


# class CartItemForm(Form):
#
#     specification = ModelChoiceField(
#         queryset=Specification.objects.all(),
#         widget=HiddenInput, required=True,
#     )
#     quantity = DecimalField(max_digits=6, decimal_places=3,
#                             min_value=Decimal('0'))
#
#     def clean_quantity(self):
#         qty = self.cleaned_data['quantity']
#         if qty > (av_qty := self.cleaned_data['specification'].available_qty):
#             raise ValidationError(
#                 f'Only {av_qty.normalize()} left.'
#             )
#         if (pack_qty := self.cleaned_data['specification'].pre_packing) != 1:
#             qty = (qty // pack_qty) * pack_qty
#         else:
#             qty = qty.to_integral_value(rounding=ROUND_FLOOR)
#         return qty


# form = CartItemForm(request.POST, auto_id=False)

# spec = form.cleaned_data.pop('specification')
# if form.cleaned_data['quantity'] > 0:
#     CartItem.objects.update_or_create(
#         user=request.user, specification=spec,
#         defaults=form.cleaned_data,
#     )
# else:
#     CartItem.objects.filter(
#         user=request.user, specification_id=spec,
#     ).delete()


# class CartView(LoginRequiredMixin, ShopView):
#     """
#     Display the items in the user's cart and the total cost.
#     """
#     login_url = '/shop/account/login/'
#     template_name = 'shop/cart.html'
#
#     def get_context_data(self, **kwargs):
#         prefetch = Prefetch('content_object', to_attr='product')
#         cart_query = CartItem.objects.filter(
#             user=self.request.user, specification_id=OuterRef('id')
#         )
#         price_case = Case(
#             When(sale_price__gt=0, then=F('sale_price')),
#             When(discount__gt=0, then=F('discount_price')),
#             default=F('price'),
#         )
#         queryset = Specification.objects.filter(
#             customers=self.request.user,
#         ).annotate(
#             cart_qty=Subquery(cart_query.values('quantity')),
#             item_id=Subquery(cart_query.values('id')),
#             customer_price=price_case,
#             total_price=F('customer_price') * F('cart_qty')
#         ).prefetch_related(prefetch)
#         kwargs['num_in_cart'] = 0
#         kwargs['total_cart_price'] = Decimal('0.00')
#         kwargs['cart'] = []
#         for item in queryset.order_by('-item_id'):
#             kwargs['cart'].append(item)
#             kwargs['total_cart_price'] += item.total_price
#             kwargs['num_in_cart'] += 1
#         context = super().get_context_data(**kwargs)
#         return context


# class CartItemForm(ModelForm):
#
#     class Meta:
#         model = CartItem
#         fields = '__all__'
#
#     def clean_quantity(self):
#         qty = self.cleaned_data['quantity']
#         if qty > (av_qty := self.cleaned_data['specification'].available_qty):
#             raise ValidationError(
#                 f'Only {av_qty.normalize()} left.'
#             )
#         if (pack_qty := self.cleaned_data['specification'].pre_packing) != 1:
#             qty = (qty // pack_qty) * pack_qty
#         else:
#             qty = qty.to_integral_value(rounding=ROUND_FLOOR)
#         return qty
#
#     def save(self, commit=True):
#         obj = super().save(commit=False)
#         if obj.quantity > 0:
#             obj = self._meta.model.objects.update_or_create(
#                 user_id=obj.user_id, specification_id=obj.specification_id,
#                 defaults={'quantity': obj.quantity},
#             )[0]
#         else:
#             self._meta.model.objects.filter(
#                 user_id=obj.user.id, specification_id=obj.specification.id,
#             ).delete()
#         return obj
#
#
# class PartialCartItemForm(CartItemForm):
#
#     class Meta:
#         model = CartItem
#         fields = ('specification', 'quantity')
#         widgets = {'specification': HiddenInput}
