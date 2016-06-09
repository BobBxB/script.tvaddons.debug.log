"""
    TVAddons Log Uploader Script
    Copyright (C) 2016 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import urllib2
import urlparse
import urllib
import uploader
from uploader import Functions
from uploader import UploaderError
from .. import log_utils

API_KEY = 'd34ab70196225eee022b176d99a4c274'
BASE_URL = 'http://pastebin.com'
EXPIRATION = '1W'

class PastebinUploader(uploader.Uploader):
    def upload_log(self, log):
        url = '/api/api_post.php'
        data = {'api_dev_key': API_KEY, 'api_option': 'paste', 'api_paste_code': log, 'api_paste_name': 'Kodi Log',
                'api_paste_private': 0, 'api_paste_expire_date': EXPIRATION}
        data = urllib.urlencode(data)
        url = urlparse.urljoin(BASE_URL, url)
        req = urllib2.Request(url, data=data)
        try:
            res = urllib2.urlopen(req)
            html = res.read()
            if html.startswith('http'):
                return html
            elif html.upper().startswith('BAD API REQUEST'):
                raise UploaderError(html[len('Bad API request, '):])
            else:
                raise UploaderError(html)
        except Exception as e:
            log_utils.log('Error (%s) during log upload: %s' % (str(e), url), log_utils.LOGWARNING)
            raise UploaderError(e)
            
    def send_email(self):
        return None
