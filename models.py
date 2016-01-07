class PaymentType:
    TYPE_UNDEFINED = 0
    TYPE_CARD = 1
    TYPE_TRANSACTION = 2
    TYPE_MOBILE = 3
    TYPE_FEES = 4
    TYPE_SAVING = 5


class Payment:
    transaction_type = PaymentType.TYPE_UNDEFINED
    price = 0
    account = None
    ks = None
    ss = None
    vs = None
    detail_from = None
    description = None
    message = None
    place = None
    date = None
    account_from = None

    def __str__(self):
        return '%s %s' % (self.price, self.account)
