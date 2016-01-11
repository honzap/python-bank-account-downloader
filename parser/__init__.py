from _csv import QUOTE_MINIMAL
from email.header import decode_header
from email.utils import parsedate_to_datetime

UCB_BANK_CODE = '2700'

class tsv:
    delimiter = ';'
    quotechar = '"'
    escapechar = None
    doublequote = False
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = QUOTE_MINIMAL


class Parser:

    def has_payments(self):
        return False

    def has_balance(self):
        return False

    def parse(self):
        raise NotImplementedError('Should be implemented!')


class EmailParser(Parser):

    def _get_message_part(self, message):
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == 'text/plain':
                    return part
        else:
            return message

    def _get_message_date(self, message):
        return parsedate_to_datetime(message['Date'])

    def _get_message_content(self, message):
        message = self._get_message_part(message)
        charset = message.get_content_charset()
        return message.get_payload(decode=True).decode(charset)

    def _get_subject(self, message):
        sbj_bytes, encoding = decode_header(message['Subject'])[0]
        return sbj_bytes.decode(encoding) if type(sbj_bytes) == bytes else sbj_bytes

    def _get_line_data(self, line):
        return ' '.join(line.split(':')[1:]).strip()


class CsvParser(Parser):

    def has_payments(self):
        return True
