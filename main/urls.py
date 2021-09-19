from django.urls import path

from . import views


app_name = 'main'

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home'),
    path('layout/shop/', views.shop_view, name='layout_shop'),
    path('layout/main/', views.main_view, name='layout_main'),
    path('layout/sidebar/', views.sidebar_view, name='layout_sidebar'),
    path('layout/sing-in/', views.sing_in_view, name='layout_sing_in'),
    path('layout/checkout/', views.checkout_view, name='layout_checkout'),
    path('layout/footer/', views.footer_view, name='layout_footer'),
    path('layout/scrolling/', views.scrolling_nav_view, name='scrolling_nav'),
]
