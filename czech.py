import datetime
import email

import base64
import re
from account_downloader.models import Payment, PaymentType


class Csob:
    TYPE_CARD = 'transakce platební kartou'
    TYPE_TRANSACTION = 'transakce TPS'
    TYPE_MOBILE = 'služby mobilního operátora'
    TYPE_FEES = 'poplatky'
    TYPE_SAVING = 'úroky'

    TYPES_MAP = (
        (TYPE_CARD, PaymentType.TYPE_CARD),
        (TYPE_TRANSACTION, PaymentType.TYPE_TRANSACTION),
        (TYPE_MOBILE, PaymentType.TYPE_MOBILE),
        (TYPE_FEES, PaymentType.TYPE_FEES),
        (TYPE_SAVING, PaymentType.TYPE_SAVING)
    )

    def __init__(self, downloader):
        self.downloader = downloader

    def parse(self):
        messages = self.downloader.download('UNSEEN HEADER Subject "Info 24"')
        for message in messages:
            date = message['Date']
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_type() == 'text/plain':
                        message = part
                        break
            charset = message.get_content_charset()
            body = base64.b64decode(message.get_payload().encode(charset)).decode(charset)
            parts = body[0:body.index(':::::::::::::')].split('\n\n\n')[1:]
            for part in parts:
                payment = self.process_message_part(part.strip())
                if payment.price:
                    payment.date = self.get_message_date(date)
                    yield payment

    def get_message_date(self, date):
        print(date)
        date_tuple = email.utils.parsedate_tz(date)
        if date_tuple:
            return datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
        return datetime.datetime.now()

    def process_message_part(self, part):
        payment = Payment()
        transaction_type = " ".join(part.split('\n')[0].split(' ')[7:])[0:-1]
        detail = False
        account_num_regex = re.compile(r'[^\d]+((\d+\-)?\d+/\d+)$')
        sender_message = False
        for line in part.split('\n'):
            account_number_matches = account_num_regex.match(line)
            if line.startswith('částka'):
                payment.price = float(line.split(' ')[1].replace(',', '.'))
            elif account_number_matches:
                payment.account = account_number_matches.group(1)
            elif line.startswith('detail'):
                detail = True
            elif detail:
                if not line.startswith('splatnost') and not line.startswith('zpr'):
                    payment.description = line
                detail = False
            elif line.startswith('KS'):
                payment.ks = line.split(' ')[1]
            elif line.startswith('VS'):
                payment.vs = line.split(' ')[-1].lstrip('0')
            elif line.startswith('SS'):
                payment.ss = line.split(' ')[1]
            elif line.startswith('zpráva pro'):
                sender_message = True
            elif sender_message:
                payment.message = line
                sender_message = False
            elif line.startswith('Od'):
                payment.detail_from = " ".join(line.split(' ')[1:])
            elif line.startswith('Místo'):
                payment.place = " ".join(line.split(' ')[1:])
            elif 'úroku' in line:
                transaction_type = self.TYPE_SAVING
            payment.transaction_type = dict(self.TYPES_MAP).get(transaction_type, PaymentType.TYPE_UNDEFINED)
        return payment
