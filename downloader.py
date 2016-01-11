import email
import imaplib


class DownloaderBase(object):
    def download(self):
        raise NotImplementedError()


class DownloadingError(RuntimeError):
    pass


class EmailDownloader(DownloaderBase):

    _handle = None

    def __init__(self, server, port, account, password, ssl=True):
        self.server = server
        self.port = port
        self.account = account
        self.password = password
        self.ssl = ssl

    def download(self, search_query='UNSEEN'):
        if self.ssl:
            self._handle = imaplib.IMAP4_SSL(self.server, self.port)
        else:
            self._handle = imaplib.IMAP4(self.server, self.port)
        try:
            self._handle.login(self.account, self.password)
        except imaplib.IMAP4.error:
            raise DownloadingError("cannot login")
        res, data = self._handle.select('INBOX')
        if res == 'OK':
            rv, data = self._handle.search(None, search_query)
            if rv != 'OK':
                raise DownloadingError("cannot find message")
            for num in data[0].split():
                rv, data = self._handle.fetch(num, '(RFC822)')
                if rv != 'OK':
                    raise DownloadingError("cannot fetch message")
                message = email.message_from_bytes(data[0][1])
                yield (num, message)
            self._handle.close()
        self._handle.logout()
        self._handle = None

    def set_unseen(self, num):
        if self._handle:
            self._handle.store(num, '-FLAGS', '\SEEN')
