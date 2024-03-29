from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    pass


class Portfolio(models.Model):

    specialization = models.CharField(unique=True, max_length=30)
    homepage = models.BooleanField(default=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()
    about = models.TextField()
    photo = models.ImageField(upload_to='mainapp/')
    tech_stack = models.TextField()
    tools = models.TextField()
    github = models.URLField(blank=True, verbose_name='GitHub')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.first_name} {self.last_name} - {self.specialization}'

    def save(self, *args, **kwargs):
        if self.homepage:
            q = Portfolio.objects.all()
            if self.pk is not None:
                q = q.exclude(pk=self.pk)
            q.filter(homepage=True).update(homepage=False)
        super().save(*args, **kwargs)


class Project(models.Model):

    name = models.CharField(max_length=100)
    description = models.TextField()
    website = models.URLField(blank=True)
    code_source = models.URLField(blank=True)
    image = models.ImageField(blank=True, upload_to='mainapp/')
    date_added = models.DateField(auto_now_add=True)
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name='projects',
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name


class Feedback(models.Model):

    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    replied = models.BooleanField(default=False)
    date_added = models.DateTimeField(auto_now_add=True)
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name='feedbacks',
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.name}, {self.message[:30]}, {self.date_added}'
