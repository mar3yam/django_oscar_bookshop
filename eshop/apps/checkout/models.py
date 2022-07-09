from oscar.apps.checkout.models import *  # noqa isort:skip
from django.db import models
from oscar.apps.basket.models import Basket


class Transaction(models.Model):
    """iranian gateway transaction model"""


    order_id = models.PositiveBigIntegerField()
    basket = models.ForeignKey(
        Basket,
        on_delete=models.CASCADE,
    )
    total_excl_tax = models.PositiveBigIntegerField()