from .models import Transaction

class Bridge():
    """
    A bridge between oscar's and zarrinpal's objects
    """

    def start_transaction(self, order_id, basket, total_excl_tax, shipping_address):
        """
        creates a new transaction when redirecting to gateway
        """

        shipping_address.save()
        pay_transaction = Transaction.objects.create(
            order_id = order_id ,
            basket = basket , 
            total_excl_tax = total_excl_tax ,
            shipping_address = shipping_address ,
        )
        return pay_transaction.id

    def get_transaction_from_id_returned_by_bank_request_query(self, id):
        """
        returnes ZarrinPayTransaction instance from id,
        this id returned by zarrinpal gateway
        """
        return Transaction.objects.get(id=id)

    