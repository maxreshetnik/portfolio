from django.shortcuts import render
from django.views.generic import TemplateView


def shop_view(request):
    return render(request, 'main/layouts/shop_homepage.html', {})


def main_view(request):
    return render(request, 'main/layouts/small_business.html', {})


def sidebar_view(request):
    return render(request, 'main/layouts/sidebar.html', {})


def sing_in_view(request):
    return render(request, 'main/layouts/sing_in.html', {})


def checkout_view(request):
    return render(request, 'main/layouts/checkout_form.html', {})


def footer_view(request):
    return render(request, 'main/layouts/sticky_footer_navbar.html', {})


class HomePageView(TemplateView):

    template_name = 'main/base.html'
