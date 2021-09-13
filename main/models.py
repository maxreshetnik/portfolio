from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    pass


class Portfolio(models.Model):

    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()
    about = models.TextField()
    photo = models.ImageField(upload_to='main/')
    tools = models.TextField()
    github = models.URLField(blank=True, verbose_name='GitHub')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Project(models.Model):

    name = models.CharField(max_length=100)
    description = models.TextField()
    website = models.URLField(blank=True)
    code_source = models.URLField(blank=True)
    image = models.ImageField(blank=True, upload_to='main/')
    date_added = models.DateField(auto_now_add=True)
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name='projects',
    )

    class Meta:
        ordering = ['-date_added']

    def __str__(self):
        return self.name
