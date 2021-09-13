from django.urls import path, include

from . import views


app_name = 'shop'

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home'),
    path('account/', include('django.contrib.auth.urls')),
    path('account/cart/',
         views.CartView.as_view(), name='cart'),
    path('account/orders/',
         views.OrderListView.as_view(), name='order_list'),
    path('account/orders/<int:pk>/',
         views.OrderDetailView.as_view(), name='order_detail'),
    path('account/orders/<int:pk>/delete/',
         views.OrderDeleteView.as_view(), name='order_delete'),
    path('account/place-order/',
         views.PlaceOrderView.as_view(), name='place_order'),
    path('account/sign-up/',
         views.CreateAccountView.as_view(), name='sign_up'),
    path('account/profile/',
         views.ProfileView.as_view(), name='profile'),
    path('account/profile/change-personal-info/',
         views.PersonalInfoView.as_view(), name='personal_info'),
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
