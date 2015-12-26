import email
import imaplib


class DownloaderBase(object):
    def download(self):
        raise NotImplementedError()


class DownloadingError(RuntimeError):
    pass


class EmailDownloader(DownloaderBase):
    def __init__(self, server, port, account, password, ssl=True):
        self.server = server
        self.port = port
        self.account = account
        self.password = password
        self.ssl = ssl

    def download(self, search_query='UNSEEN'):
        if self.ssl:
            handle = imaplib.IMAP4_SSL(self.server, self.port)
        else:
            handle = imaplib.IMAP4(self.server, self.port)
        try:
            handle.login(self.account, self.password)
        except imaplib.IMAP4.error:
            raise DownloadingError("cannot login")
        res, data = handle.select('INBOX')
        if res == 'OK':
            result = self.process_mailbox(handle, search_query)
            handle.close()
        handle.logout()
        return result

    def process_mailbox(self, handle, search_query):
        rv, data = handle.search(None, search_query)
        if rv != 'OK':
            raise DownloadingError("cannot find message")
        messages = []
        for num in data[0].split():
            rv, data = handle.fetch(num, '(RFC822)')
            if rv != 'OK':
                raise DownloadingError("cannot fetch message")
            message = email.message_from_bytes(data[0][1])
            messages.append(message)
        return messages
