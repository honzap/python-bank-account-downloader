import csv
import datetime

from czech_banks.models import PaymentType, Payment
from czech_banks.parser import CsvParser, tsv, UCB_BANK_CODE


class Equabank(CsvParser):
    TYPE_MAP = (
        ('Odchozí platba v rámci ČR', PaymentType.TYPE_TRANSACTION),
        ('Platba kartou', PaymentType.TYPE_CARD),
        ('Platba v rámci Equa bank', PaymentType.TYPE_TRANSACTION),
        ('Poplatek za výběr z bankomatu', PaymentType.TYPE_FEES),
        ('Příchozí platba v rámci ČR', PaymentType.TYPE_TRANSACTION),
        ('Připsaný úrok', PaymentType.TYPE_SAVING),
        ('Srážková daň z úroků', PaymentType.TYPE_SAVING),
        ('Trvalý příkaz', PaymentType.TYPE_TRANSACTION),
        ('Výběr z bankomatu', PaymentType.TYPE_CARD),
    )

    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        with open(self.filename, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile, dialect=tsv)
            header = True
            for row in reader:
                if header:
                    header = False
                    continue
                my_account_num, iban, contra_account, name, date1, date2, price, detail, description, category, code = row
                payment = Payment()
                payment.price = float(price.replace(',', '.'))
                payment.detail_from = name.strip('.').strip() or None
                payment.date = datetime.datetime.strptime(date1, '%d.%m.%Y')
                payment.description = description or category
                payment.transaction_type = dict(self.TYPE_MAP).get(detail, PaymentType.TYPE_UNDEFINED)
                if payment.transaction_type != PaymentType.TYPE_CARD:
                    payment.account = contra_account
                yield payment


class Zuno(CsvParser):
    TYPE_MAP = (
        ('Manuální splátka KREDITKY z vašeho účtu', PaymentType.TYPE_CARD),
        ('Platba KARTOU', PaymentType.TYPE_CARD),
        ('Splátka KREDITKY inkasem z ÚČTU', PaymentType.TYPE_CARD),
        ('Odeslaná domácí platba', PaymentType.TYPE_TRANSACTION),
        ('Odeslaná SEPA platba', PaymentType.TYPE_TRANSACTION),
        ('Převod mezi vlastními účty:', PaymentType.TYPE_TRANSACTION),
        ('Převod základního vkladu', PaymentType.TYPE_TRANSACTION),
        ('Přijatá domácí platba', PaymentType.TYPE_TRANSACTION),
        ('Trvalý příkaz', PaymentType.TYPE_TRANSACTION),
        ('Poplatek', PaymentType.TYPE_FEES),
        ('Vrácení poplatku', PaymentType.TYPE_FEES),
        ('Platba z vlastního účtu:', PaymentType.TYPE_TRANSACTION),
        ('Úrok', PaymentType.TYPE_SAVING),
        ('Srážka daně', PaymentType.TYPE_SAVING),
        ('Trvalý příkaz', PaymentType.TYPE_TRANSACTION),
        ('Výběr z bankomatu', PaymentType.TYPE_CARD),
    )

    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        with open(self.filename, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = True
            for row in reader:
                if header:
                    header = False
                    continue
                date, tr_type, acc_name, contra_account, contra_account_code, description, price = row[0:7]
                payment = Payment()
                payment.price = float(price.replace(',', '.').replace(' ', ''))
                payment.date = datetime.datetime.strptime(date, '%d.%m.%Y')
                payment.message = description
                payment.description = description
                payment.account = (contra_account.lstrip('0') + '/' + contra_account_code).strip('/').strip()
                payment.transaction_type = dict(self.TYPE_MAP).get(tr_type, PaymentType.TYPE_UNDEFINED)
                yield payment


class Mbank(CsvParser):
    TYPE_MAP = (
        ('VÝBĚR Z BANKOMATU', PaymentType.TYPE_CARD),
        ('PLATBA KARTOU', PaymentType.TYPE_CARD),
        ('PLATBA KARTOU S VÝBĚREM HOTOVOSTI', PaymentType.TYPE_CARD),
        ('INKASO / SIPO', PaymentType.TYPE_TRANSACTION),
        ('ODCHOZÍ PLATBA DO JINÉ BANKY', PaymentType.TYPE_TRANSACTION),
        ('ODCHOZÍ PLATBA DO MBANK', PaymentType.TYPE_TRANSACTION),
        ('POPL. ZA VÝBĚR Z BANKOMATU V ZAHR.', PaymentType.TYPE_FEES),
        ('POPLATEK ZA VÝBĚR Z BANKOMATU V ČR', PaymentType.TYPE_FEES),
        ('PŘÍCHOZÍ PLATBA Z JINÉ BANKY', PaymentType.TYPE_TRANSACTION),
        ('ZÚČTOVÁNÍ ÚROKŮ', PaymentType.TYPE_SAVING),
    )

    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        with open(self.filename, 'r', newline='', encoding='iso-8859-2') as csvfile:
            reader = csv.reader(csvfile, dialect=tsv)
            header = True
            for row in reader:
                if header:
                    if len(row) > 1 and row[0].startswith('#Datum'):
                        header = False
                    continue
                if len(row) < 11:
                    continue
                date, date2, tr_type, description, from_name, contra_account, ks, vs, ss, price, balance = row[0:11]
                payment = Payment()
                payment.price = float(price.replace(',', '.').replace(' ', ''))
                payment.date = datetime.datetime.strptime(date, '%d-%m-%Y')
                description = description.strip(' \'')
                from_name = from_name.strip(' \'')
                contra_account = contra_account.strip(' \'')
                if '                            ' in description:
                    description = description.split('                            ')[0]
                if '/' in description:
                    parts = description.split('/')
                    from_name = '/'.join(parts[0:-1])
                    payment.place = parts[-1].strip()
                    description = ''
                payment.description = description.strip()
                payment.detail_from = from_name
                payment.account = contra_account.lstrip('0').lstrip('-').lstrip('0')
                payment.transaction_type = dict(self.TYPE_MAP).get(tr_type, PaymentType.TYPE_UNDEFINED)
                yield payment


class Unicredit(CsvParser):

    TYPE_MAP = (
        ('KARETNÍ TRANSAKCE', PaymentType.TYPE_CARD),
        ('VÝBĚR Z BANKOMATU', PaymentType.TYPE_CARD),
        ('PLATBA PLATEBNÍ KARTOU', PaymentType.TYPE_CARD),
        ('VÝBĚR Z BANKOMATU V ZAHRANIČÍ', PaymentType.TYPE_CARD),
        ('VKLAD BANKOMATEM', PaymentType.TYPE_CARD),
        ('SPRÁVA ÚVĚRU', PaymentType.TYPE_TRANSACTION),
        ('TUZEMSKÁ PLATBA ODCHOZÍ', PaymentType.TYPE_TRANSACTION),
        ('TUZEMSKÁ PLATBA PŘÍCHOZÍ', PaymentType.TYPE_TRANSACTION),
        ('POPLATKY', PaymentType.TYPE_FEES),
        ('TRVALÝ PŘÍKAZ', PaymentType.TYPE_TRANSACTION),
        ('ÚROKY', PaymentType.TYPE_SAVING),
        ('SRÁŽKOVÁ DAŇ', PaymentType.TYPE_SAVING),
    )

    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        with open(self.filename, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile, dialect=tsv)
            header = True
            for row in reader:
                if header:
                    if len(row) > 1 and row[0].startswith('Účet'):
                        header = False
                    continue
                if len(row) < 24:
                    continue
                acc, price, currency, date, date2, bank_code, bank_name, bank_name2, account, detail_from, add1, add2, add3, \
                    tr_type, detail1, detail2, detail3, detail4, detail5, ks, vs, ss, pay_title, ref_num = row[0:24]
                payment = Payment()
                payment.price = float(price.replace(',', '.'))
                payment.date = datetime.datetime.strptime(date, '%Y-%m-%d')
                payment.account = (account + '/' + bank_code).strip('/')
                payment.account_from = acc + '/' + UCB_BANK_CODE
                payment.detail_from = detail_from
                payment.transaction_type = dict(self.TYPE_MAP).get(tr_type, PaymentType.TYPE_UNDEFINED)
                if payment.transaction_type == PaymentType.TYPE_UNDEFINED:
                    if tr_type.lower().startswith('poplat'):
                        payment.transaction_type = PaymentType.TYPE_FEES
                    else:
                        payment.transaction_type = PaymentType.TYPE_TRANSACTION
                        payment.message = tr_type
                if payment.transaction_type == PaymentType.TYPE_CARD:
                    payment.place = detail5
                payment.description = ('%s %s %s' % (detail1, detail2, detail3)).strip()
                payment.vs = vs
                payment.ks = ks
                payment.ss = ss
                yield payment
