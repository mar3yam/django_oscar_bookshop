import oscar.apps.checkout.apps as apps
from django.urls import path

class CheckoutConfig(apps.CheckoutConfig):
    name = 'apps.checkout'

    def ready(self):
        super().ready()
        from . import views
        self.gateway_callback = views.GateWayCallBack

    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path('callback/<int:bridge_id>/', self.gateway_callback.as_view(), name='gateway-callback'),
        ]
        return self.post_process_urls(urls)
