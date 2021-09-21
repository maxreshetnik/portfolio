from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.forms import modelform_factory
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.messages import get_messages

from .models import Portfolio, Feedback


class FeedbackCreate(SuccessMessageMixin, CreateView):

    model = Feedback
    fields = ['name', 'email', 'message', 'portfolio']
    success_url = reverse_lazy('main:home')
    success_message = "Your message has been sent."


class HomePageView(TemplateView):

    template_name = 'main/base.html'

    def get(self, request, *args, **kwargs):
        FeedbackForm = modelform_factory(
            Feedback, fields=('name', 'email', 'message', 'portfolio'),
        )
        context = self.get_context_data(form=FeedbackForm(), **kwargs)
        context['messages'] = get_messages(request)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        view = FeedbackCreate.as_view(extra_context=self.get_context_data())
        return view(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Extends context data with portfolio and projects info."""
        context = super().get_context_data(**kwargs)
        portfolio = get_object_or_404(
            Portfolio, specialization='python developer',
        )
        projects = portfolio.projects.all()
        context.update({'portfolio': portfolio, 'projects': projects})
        return context
