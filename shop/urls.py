from django.urls import path, include

from . import views


app_name = 'shop'

account_patterns = [
    path('', include('django.contrib.auth.urls')),
    path('cart/',
         views.CartView.as_view(), name='cart'),
    path('add-to-cart/',
         views.CartItemFormView.as_view(), name='add_to_cart'),
    path('orders/',
         views.OrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/',
         views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/delete/',
         views.OrderDeleteView.as_view(), name='order_delete'),
    path('place-order/',
         views.PlaceOrderView.as_view(), name='place_order'),
    path('rate-product/',
         views.RatingFormView.as_view(), name='rate_product'),
    path('ratings-and-reviews/',
         views.RatingListView.as_view(), name='rating_list'),
    path('sign-up/',
         views.CreateAccountView.as_view(), name='sign_up'),
    path('profile/',
         views.ProfileView.as_view(), name='profile'),
    path('profile/change-personal-info/',
         views.PersonalInfoView.as_view(), name='personal_info'),
]

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home'),
    path('account/', include(account_patterns)),
    path('search/', views.SearchView.as_view(), name='search'),
    path('<category>/',
         views.CategorySpecList.as_view(), name='category'),
    path('<category>/new/',
         views.NewArrivalSpecList.as_view(), name='new'),
    path('<category>/popular/',
         views.PopularSpecList.as_view(), name='popular'),
    path('<category>/<subcategory>/',
         views.SubcategorySpecList.as_view(), name='subcategory'),
    path('<category>/<subcategory>/<int:pk>/',
         views.SpecificationDetail.as_view(), name='spec_detail'),
]
