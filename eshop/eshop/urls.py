"""eshop URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.apps import apps
from django.urls import include, path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from azbankgateways.urls import az_bank_gateways_urls
from payment.checkout.views import go_to_gateway_view
from payment.checkout.views import callback_gateway_view


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('bankgateways/', az_bank_gateways_urls()),
    path('go_to_gateway/', go_to_gateway_view),
    path('callback-gateway/', callback_gateway_view),
    path('', include(apps.get_app_config('oscar').urls[0])),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
