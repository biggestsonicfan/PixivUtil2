import sys
from time import sleep
import time
import traceback

from cloudscraper import CloudScraper
import requests
from bs4 import BeautifulSoup

import PixivHelper
from PixivException import PixivException

class PixivLogin(CloudScraper):
    _config = None
    
    def __init__(self):
        CloudScraper.__init__(self)
        self.scraper = CloudScraper(
            # Browser specifications.
            browser={
                    "browser": "firefox",
                    "platform": "windows",
                    "desktop": True,
                    "mobile": False
                },
            # JavaScript Engine
            interpreter="nodejs",
            debug=True
            )
    def _configureBrowser(self, config):
        if config is None:
            PixivHelper.get_logger().info("No config given")
            return

        global defaultConfig
        if defaultConfig is None:
            defaultConfig = config

        self._config = config

    def send_request(self, url, data=None, timeout=None, method="GET", **kwargs):
        """
        Send a request using the CloudScraper session.
        :param url: The URL to send the request to
        :param data: Data to include in the request body (for POST/PUT requests)
        :param timeout: Timeout for the request (in seconds)
        :param method: HTTP method to use ("GET", "POST", etc.)
        :param kwargs: Additional arguments to pass to the request
        :return: Response html
        """
        method = method.upper()
        html = None
        if method == "GET":
            html = self.scraper.get(url, timeout=timeout, **kwargs)
        elif method == "POST":
            html = self.scraper.post(url, data=data, timeout=timeout, **kwargs)
        elif method == "PUT":
            html = self.scraper.put(url, data=data, timeout=timeout, **kwargs)
        elif method == "DELETE":
            html = self.scraper.delete(url, timeout=timeout, **kwargs)
        else:
            PixivHelper.print_and_log('error', f'Unsupported HTTP method: {method}')
            raise PixivException(f"Unsupported HTTP method: {method} - Something is wrong in the code.",
                        errorCode=PixivException.OTHER_ERROR)
        
        time.sleep(10)
        return html.text
            

    
    def open_with_retry(self, url, data=None, timeout=60, retry=0, method="GET"):
        ''' Return response object with retry.'''
        retry_count = 0
        if retry == 0 and self._config is not None:
            retry = self._config.retry

        while True:
            res = None
            try:
                res = self.send_request(url, data, timeout, method)
                return res
            except requests.exceptions.HTTPError as fanboxError:
                if res is not None:
                    print(f"Error Code: {res.status_code}")
                    print(f"Response Headers: {res.headers}")
                    if res.code == '302':
                        print(f"Redirect to {res.headers['location']}")
                else:
                    # Issue #1342
                    if "challenge_basic_security_FANBOX" in str(fanboxError.text) and fanboxError.status_code == 403:
                        return fanboxError
                raise
            except BaseException:
                exc_value = sys.exc_info()[1]
                if retry_count < retry:
                    print(exc_value, end=' ')
                    for t in range(1, self._config.retryWait):
                        print(t, end=' ')
                        PixivHelper.print_delay(2)
                    print('')
                    retry_count = retry_count + 1
                else:
                    temp = url
                    if isinstance(url, (requests.Request, requests.PreparedRequest)):
                        temp = url.url

                    PixivHelper.print_and_log('error', f'Error at open_with_retry(): {sys.exc_info()}')
                    raise PixivException(f"Failed to get page: {temp}, please check your internet connection/firewall/antivirus.",
                                         errorCode=PixivException.SERVER_ERROR)

    def login(self, username, password):
        parsed = None
        try:
            PixivHelper.print_and_log('info', 'Logging in...')
            url = "https://accounts.pixiv.net/login"
            # get the post key
            res = self.open_with_retry(url)
            parsed = BeautifulSoup(res, features="html5lib")
            post_key = parsed.find('input', attrs={'name': 'post_key'})
            # js_init_config = self._getInitConfig(parsed)

            data = {}
            data['pixiv_id'] = username
            data['password'] = password
            # data['captcha'] = ''
            # data['g_recaptcha_response'] = ''
            data['return_to'] = 'https://www.pixiv.net'
            data['lang'] = 'en'
            data['post_key'] = post_key['value']
            data['source'] = "accounts"
            data['ref'] = ''

            request = self.scraper.request("https://accounts.pixiv.net/api/login?lang=en", data, method='POST')
            response = self.open_with_retry(request)

            result = self.processLoginResult(response, username, password)
            response.close()
            return result
        except BaseException:
            traceback.print_exc()
            PixivHelper.print_and_log('error', f'Error at login(): {sys.exc_info()}')
            PixivHelper.dump_html("login_error.html", str(parsed))
            raise
        finally:
            if parsed is not None:
                parsed.decompose()
                del parsed