from django.urls import path
from django.views.decorators.cache import cache_page

from . import views


app_name = 'mainapp'

urlpatterns = [
    path('', cache_page(60 * 5)(views.HomePageView.as_view(
        http_method_names=['get', 'head', 'options'],
    )), name='home'),
    path('feedback/', views.HomePageView.as_view(
        template_name='mainapp/feedback_form.html',
    ), name='feedback'),
]
