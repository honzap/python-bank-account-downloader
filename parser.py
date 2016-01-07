from email.utils import parsedate_to_datetime

import base64
from email.header import decode_header


class Parser:

    def has_payments(self):
        raise False

    def has_balance(self):
        raise False

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

    def _get_message_content(self, message, use_base64=False):
        message = self._get_message_part(message)
        if use_base64:
            charset = message.get_content_charset()
            return base64.b64decode(message.get_payload().encode(charset)).decode(charset)
        else:
            return message.get_payload()

    def _get_subject(self, message):
        sbj_bytes, encoding = decode_header(message['Subject'])[0]
        return sbj_bytes.decode(encoding)