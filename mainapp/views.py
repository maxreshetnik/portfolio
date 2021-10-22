from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.messages import get_messages, warning as msg_warning

from .models import Portfolio
from .forms import FeedbackForm


class HomePageView(SuccessMessageMixin, FormView):

    template_name = 'mainapp/base.html'
    form_class = FeedbackForm
    success_url = reverse_lazy('mainapp:feedback')
    success_message = "Your message has been sent."

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Extends context data with portfolio and projects info."""
        context = super().get_context_data(**kwargs)
        try:
            portfolio = Portfolio.objects.filter(homepage=True)[0]
        except IndexError:
            msg_warning(self.request, 'Sorry, the portfolio is not available '
                                      'at this time.')
        else:
            projects = portfolio.projects.all()
            context.update({'portfolio': portfolio, 'projects': projects})
        finally:
            context['messages'] = get_messages(self.request)
        return context
