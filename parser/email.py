import datetime

import re
from czech_banks.models import Payment, PaymentType, Balance
from czech_banks.parser import EmailParser


class Csob(EmailParser):
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

    def has_payments(self):
        return True

    def parse(self):
        messages = self.downloader.download('UNSEEN HEADER Subject "Info 24"')
        for message in messages:
            date = self._get_message_date(message)
            subject = self._get_subject(message)
            if 'Avízo' in subject:
                body = self._get_message_content(message, True)
                body = body[0:body.index(':::::::::::::')]
                payment = Payment()
                payment.date = date
                if 'klientko' in body:
                    body = '\n'.join(body.split('\n\n')[1:])
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
                    elif 'úrok' in line:
                        transaction_type = self.TYPE_SAVING
                    payment.transaction_type = dict(self.TYPES_MAP).get(transaction_type, PaymentType.TYPE_UNDEFINED)


class Raiffeisenbank(EmailParser):
    """
    Format of defined e-mails:
    - Incoming:
        PRICHOZI
        Z: %DN%
        Na: %CN%
        Castka: %RA% %CC%
        Dne: %RD%
        KS: %TCS%
        VS: %CVS%
        SS: %TSS%
        Zprava: %CI%
    - Outgoing:
        ODCHOZI
        Z: %DN%
        Na: %CN%
        Castka: %RA% %CC%
        Dne: %RD%
        KS: %TCS%
        VS: %CVS%
        SS: %TSS%
        Zprava: %CI%
    """

    TYPE_OUTGOING = 1
    TYPE_INCOMING = 2

    def __init__(self, downloader):
        self.downloader = downloader

    def has_payments(self):
        return True

    def parse(self):
        messages = self.downloader.download('UNSEEN HEADER From "info@rb.cz"')
        for message in messages:
            body = self._get_message_content(message)
            payment = Payment()
            payment_type = 0
            for line in body.split('\n'):
                if 'ODCHOZI' in line:
                    payment.transaction_type = PaymentType.TYPE_TRANSACTION
                    payment_type = self.TYPE_OUTGOING
                elif 'PRICHOZI' in line:
                    payment.transaction_type = PaymentType.TYPE_TRANSACTION
                    payment_type = self.TYPE_INCOMING
                elif (line.startswith('Z:') and payment_type == self.TYPE_INCOMING) or (line.startswith('Na') and payment_type == self.TYPE_OUTGOING):
                    payment.account = '/'.join(self._get_line_data(line).split('/')[0:2])
                elif (line.startswith('Z:') and payment_type == self.TYPE_OUTGOING) or (line.startswith('Na') and payment_type == self.TYPE_INCOMING):
                    payment.account_from = '/'.join(self._get_line_data(line).split('/')[0:2])
                elif line.startswith('Castka:'):
                    payment.price = float(''.join(self._get_line_data(line).split(' ')[0:-1]).replace(',', '.'))
                    if payment_type == self.TYPE_OUTGOING:
                        payment.price = -1 * payment.price
                elif line.startswith('KS:'):
                    payment.ks = self._get_line_data(line)
                elif line.startswith('VS:'):
                    payment.vs = self._get_line_data(line)
                elif line.startswith('SS:'):
                    payment.ss = self._get_line_data(line)
                elif line.startswith('Dne:'):
                    try:
                        payment.date = datetime.datetime.strptime(self._get_line_data(line), '%d.%m.%Y %H:%M')
                    except ValueError as e:
                        payment.date = self._get_message_date(message)
                elif line.startswith('Zprava:'):
                    payment.message = self._get_line_data(line)
            yield payment

    def _get_line_data(self, line):
        return ' '.join(line.split(':')[1:]).strip()


class Equabank(EmailParser):

    def __init__(self, downloader):
        self.downloader = downloader

    def has_balance(self):
        return True

    def parse(self):
        balances = {}
        messages = self.downloader.download('UNSEEN HEADER From "info@equabank.cz"')
        for message in messages:
            message_balance = Balance()
            body = self._get_message_content(message)
            for line in body.split('\n'):
                parts = line.split(' ')
                if 'stka' in line:
                    message_balance.account = self._extract_line_part(parts, 3, 4, '')
                elif 'dne' in line:
                    message_balance.balance = float(self._extract_line_part(parts, -2, -1, '').replace(',', '.'))
                    message_balance.currency = self._extract_line_part(parts, -1, None, '').strip('.')
                    try:
                        message_balance.date = datetime.datetime.strptime(self._extract_line_part(parts, 3, 5, ' '), '%d.%m.%Y %H:%M')
                    except ValueError:
                        message_balance.date = self._get_message_date(message)
            if (message_balance.account not in balances.keys() or balances[message_balance.account].date < message_balance.date):
                balances[message_balance.account] = message_balance
        return balances.values()

    def _extract_line_part(self, parts, start, end, delimiter):
        return delimiter.join(parts[start:end if end is not None else len(parts)]).strip()


class Mbank(EmailParser):

    def __init__(self, downloader):
        self.downloader = downloader

    def has_balance(self):
        return True

    def parse(self):
        balance = Balance()
        messages = self.downloader.download('UNSEEN HEADER From "kontakt@mbank.cz"')
        for message in messages:
            if 'Email Push' in self._get_subject(message):
                message_balance = Balance()
                if not message.is_multipart():
                    continue
                body = None
                for part in message.walk():
                    if part.get_content_type() == 'text/html' and 'Vlast.prostr' in part.get_payload():
                        body = part.get_payload()
                        break
                if not body:
                    continue
                tmp = body[body.rindex('Vlast.prostr'):]
                tmp = ''.join(tmp[0:tmp.index('<')].split(':')[1]).strip('.').strip()
                message_balance.date = self._get_message_date(message)
                message_balance.balance = float(''.join(tmp.split(' ')[0]).replace(',', '.'))
                message_balance.currency = ''.join(tmp.split(' ')[-1])
                if balance.balance is None or balance.date < message_balance.date:
                    balance = message_balance
        return [balance]
