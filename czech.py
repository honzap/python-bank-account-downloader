import datetime
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime

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
            date = parsedate_to_datetime(message['Date'])
            sbj_bytes, encoding = decode_header(message['Subject'])[0]
            subject = sbj_bytes.decode(encoding)
            if 'Avízo' in subject:
                if message.is_multipart():
                    for part in message.walk():
                        if part.get_content_type() == 'text/plain':
                            message = part
                            break
                charset = message.get_content_charset()
                body = base64.b64decode(message.get_payload().encode(charset)).decode(charset)
                body = body[0:body.index(':::::::::::::')]
                payment = Payment()
                payment.date = date
                if 'klientko' in body:
                    body = ''.join(body.split('\n\n')[1:])
                detail = False
                account_num_regex = re.compile(r'[^\d]+((\d+\-)?\d+/\d+)$')
                sender_message = False
                transaction_type = ''
                for line in body.split('\n'):
                    account_number_matches = account_num_regex.match(line)
                    if 'Zůstatek na účtu' in line:
                        yield payment
                        payment = Payment()
                        payment.date = date
                        detail = False
                        sender_message = False
                    elif line.startswith('dne'):
                        transaction_type = ' '.join(line.split(' ')[7:])[0:-1]
                    elif line.startswith('částka'):
                        payment.price = float(line.split(' ')[1].replace(',', '.'))
                    elif account_number_matches:
                        payment.account = account_number_matches.group(1)
                    elif line.startswith('detail'):
                        detail = True
                    elif detail:
                        if not line.startswith('splatnost') and not line.startswith('zpr') and 'SPO' not in line:
                            payment.detail_from = line
                        if 'SPO' in line:
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

    def get_message_date(self, date):
        date_tuple = email.utils.parsedate_tz(date)
        if date_tuple:
            return datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
        return datetime.datetime.now()

