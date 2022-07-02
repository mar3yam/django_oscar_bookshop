from email.policy import default
from django import views
from django.urls import reverse
from azbankgateways import bankfactories, models as bank_models, default_settings as Settings
from azbankgateways.exceptions import AZBankGatewaysException
from oscar.apps.checkout.views import PaymentDetailsView as CorePaymentDetailsView
from django.http import HttpResponse, Http404
from django.views.generic.base import View
from oscar.apps.checkout.mixins import OrderPlacementMixin
from oscar.apps.checkout.views import PaymentMethodView as CorePaymentMethodView
from oscar.apps.partner.strategy import Default as DefaultStrategy
from oscar.core.prices import Price as DefaultPrice
from decimal import Decimal as D
from django.shortcuts import redirect, render
from oscar.apps.payment import models
from django.views.generic import FormView
from . import forms
from django.urls import reverse_lazy
from django.conf import settings
from eshop.settings import OSCAR_PAYMENT_METHODS
from oscar.apps.payment.exceptions import PaymentError
import logging
logger = logging.getLogger('oscar.checkout')

class PaymentMethodView(CorePaymentMethodView, FormView):
    """
    View for a user to choose which payment method(s) they want to use.

    This would include setting allocations if payment is to be split
    between multiple sources. It's not the place for entering sensitive details
    like bankcard numbers though - that belongs on the payment details view.
    """
    template_name = "checkout/payment_method.html"
    step = 'payment-method'
    form_class = forms.PaymentMethodForm
    success_url = reverse_lazy('checkout:payment-preview')

    pre_conditions = [
        'check_basket_is_not_empty',
        'check_basket_is_valid',
        'check_user_email_is_captured',
        'check_shipping_data_is_captured',
        'check_payment_data_is_captured',
    ]
    skip_conditions = ['skip_unless_payment_is_required']

    def get(self, request, *args, **kwargs):
        # if only single payment method, store that
        # and then follow default (redirect to preview)
        # else show payment method choice form
        if len(settings.OSCAR_PAYMENT_METHODS) == 1:
            self.checkout_session.pay_by(settings.OSCAR_PAYMENT_METHODS[0][0])
            return redirect(self.get_success_url())
        else:
            return FormView.get(self, request, *args, **kwargs)

    def get_success_url(self, *args, **kwargs):
        # Redirect to the correct payments page as per the method (different methods may have different views &/or additional views)
        return reverse_lazy('checkout:preview')

    def get_initial(self):
        return {
            'payment_method': self.checkout_session.payment_method(),
        }

    def form_valid(self, form):
        # Store payment method in the CheckoutSessionMixin.checkout_session (a CheckoutSessionData object)
        self.checkout_session.pay_by(form.cleaned_data['payment_method'])
        return super().form_valid(form)


class PaymentDetailsView(CorePaymentDetailsView):
    template_name = 'checkout/payment-details.html'
    template_name_preview = 'checkout/preview.html'
    def submit(self, user, basket, shipping_address, shipping_method,  # noqa (too complex (10))
               shipping_charge, billing_address, order_total,
               payment_kwargs=None, order_kwargs=None, surcharges=None):
        if payment_kwargs is None:
            payment_kwargs = {}
        if order_kwargs is None:
            order_kwargs = {}
        # Taxes must be known at this point
        try:
            assert basket.is_tax_known, (
                "Basket tax must be set before a user can place an order")
            assert shipping_charge.is_tax_known, (
                "Shipping charge tax must be set before a user can place an order")

            # We generate the order number first as this will be used
            # in payment requests (ie before the order model has been
            # created).  We also save it in the session for multi-stage
            # checkouts (e.g. where we redirect to a 3rd party site and place
            # the order on a different request).
            order_number = self.generate_order_number(basket)
            self.checkout_session.set_order_number(order_number)
            logger.info("Order #%s: beginning submission process for basket #%d",
                        order_number, basket.id)
            payment_method = self.checkout_session.payment_method()
            return self.handle_payment(
                basket,
                payment_method,
                shipping_address,
                order_total,
                order_number ,
                payment_kwargs=payment_kwargs,
                order_kwargs=order_kwargs,
            )
        except PaymentError as e:
            logger.exception("Order #%s: you should select django_oscar_zarinpal_gateway for payment method (%s)", order_number, e)
        except Exception as e :
            # Unhandled exception - hopefully, you will only ever see this in
            # development...
            logger.exception(
                "Order #%s: unhandled exception while taking payment (%s)", order_number, e)
            self.restore_frozen_basket()
        return self.render_preview(
                self.request, error="A problem occurred while processing payment for this "
                      "order - no payment has been taken.  Please "
                      "contact customer services if this problem persists", **payment_kwargs)

    def handle_payment(self, basket, payment_method, shipping_address,
                order_total, order_number ,
                payment_kwargs=None, order_kwargs=None):
        if payment_kwargs is None:
            payment_kwargs = {}
        if order_kwargs is None:
            order_kwargs = {}
        logger.info("Order #%s: beginning submission process for basket #%d",
                    order_number, basket.id)

        # Freeze the basket so it cannot be manipulated while the customer is
        # completing payment on a 3rd party site.  Also, store a reference to
        # the basket in the session so that we know which basket to thaw if we
        # get an unsuccessful payment response when redirecting to a 3rd party
        # site.
        self.freeze_basket(basket)
        self.checkout_session.set_submitted_basket(basket)

        return self.go_to_gateway_view(order_total, payment_method)


    def get_context_data(self, **kwargs):
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)
        payment_method = self.checkout_session.payment_method()
        ctx.update({'payment_method': payment_method})
        return ctx

    # def check_currency(self, currency):
    #     if not currency == 'IRR':
    #         return HttpResponse("مبلغ پرداختی ریال نمیباشد.لطفا دوباره تلاش کنید.")

    def go_to_gateway_view(self, order_total, payment_method):

        factory = bankfactories.BankFactory()
        try:
            
            # Banks = ['BMI', 'SEP', 'ZARINPAL', 'IDPAY', 'ZIBAL', 'BAHAMTA', 'MELLAT']
            # for Bank in Banks:
            #     IranianBankList = Bank
            bank = factory.create(getattr(bank_models.BankType, 'ZARINPAL'))

            bank.set_request(self.request)
            if order_total.currency == 'IRR':
                bank.set_amount(order_total.incl_tax)
            else:
                HttpResponse("مبلغ پرداختی ریال نمیباشد.لطفا دوباره تلاش کنید.")
            bank.set_client_callback_url(reverse("gateway-callback"))
        
            bank_record = bank.ready()
            return bank.redirect_gateway()
        except AZBankGatewaysException as e:
            logging.critical(e)
            # TODO: redirect to failed page.
            raise e

class GateWayCallBack(OrderPlacementMixin, View):
    template_name = 'oscar/checkout/thank_you.html'
    def get(self, request, *args, **kwargs):
        try : 
            tracking_code = request.GET.get(Settings.TRACKING_CODE_QUERY_PARAM, None)
        except:
            return HttpResponse("دریافت کد پیگیری امکان پذیر نیست.")
        if not tracking_code:
            logging.debug("این لینک معتبر نیست.")
            raise Http404

        try:
            bank_record = bank_models.Bank.objects.get(tracking_code=tracking_code)
        except bank_models.Bank.DoesNotExist:
            logging.debug("این لینک معتبر نیست.")
            raise Http404

        if bank_record.is_success:
           response = self.submit_order(**kwargs)
           return response
        
        return HttpResponse("پرداخت با شکست مواجه شده است. اگر پول کم شده است ظرف مدت ۴۸ ساعت پول به حساب شما بازخواهد گشت.")

    def submit_order(self, **kwargs):
        source = models.Source(
            currency='IRR',
            # order_total not defined
            amount_allocated=self.order_total.incl_tax,
        )

        self.add_payment_source(source)
        self.add_payment_event('Authorised', self.order_total.incl_tax)

        # finalising the order into oscar
        logger.info("Order #%s: payment successful, placing order", self.order_id)

        self.pay_transaction.basket.strategy = DefaultStrategy()
        submission = self.build_submission(basket=self.pay_transaction.basket)
        return self._save_order(self.pay_transaction.order_id, submission)
    
    def _save_order(self, order_id, submission):
        # Finalize the order that PaymentDetailsView.submit() started
        # If all is ok with payment, try and place order
        logger.info("Order #%s: payment started, placing order", order_id)

        shipping_charge = DefaultPrice(
            currency='IRR' ,
            excl_tax= D(0.0) ,
            incl_tax= D(0.0),
            tax= D(0.0),
        )

        return self.handle_order_placement(
            order_number=self.pay_transaction.order_id,
            basket=submission['basket'],
            order_total=submission['order_total'], 
            user=submission['user'],
            shipping_address = ['shipping_address'],
            shipping_method = submission['shipping_method'],
            shipping_charge = shipping_charge,
            billing_address=submission['billing_address'],
            **submission['order_kwargs'],
        )
