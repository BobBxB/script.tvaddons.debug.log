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
import uploader
from uploader import UploaderError
from .. import dropbox_api
from .. import kodi
from ..kodi import i18n
from .. import log_utils

APP_KEY = '6943gzynff6zkcz'
APP_SECRET = 'fp8d96951grzf78'
SHORT_URL = 'http://goo.gl/u26N0x'

class DropboxUploader(uploader.Uploader):
    name = 'dropbox'

    def upload_log(self, log, name=None):
        if name is None: name = 'kodi.log'
        token = kodi.get_setting('dropbox_token')
        if not token:
            token = self.__authorize()
            
        try:
            if token:
                full_path = '/%s' % (name)
                db = dropbox_api.DropboxClient(token)
                db.put_file(full_path, log, overwrite=True)
                res = db.share(full_path)
                return res.get('url')
        except dropbox_api.ErrorResponse as e:
            raise UploaderError('Upload Failed: (%s): %s' % (e.status, e.reason))
    
    def __authorize(self):
        auth_flow = dropbox_api.DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)
        authorize_url = auth_flow.start()
        line1 = i18n('dropbox_visit') % (SHORT_URL)
        log_utils.log('Visit: %s' % (authorize_url), log_utils.LOGNOTICE)
        kodi.ok(i18n('dropbox_auth'), line1=line1, line2=i18n('dropbox_pin'))
        auth_code = kodi.get_keyboard(i18n('enter_pin'))
        if not auth_code:
            raise UploaderError('Authorization Aborted')
        
        try:
            access_token, _user_id = auth_flow.finish(auth_code)
            kodi.set_setting('dropbox_token', access_token)
            return access_token
        except dropbox_api.ErrorResponse as e:
            raise UploaderError('Authorization Failed (%s): %s' % (e.status, e.reason))
    
    def send_email(self, email, results):
        return None
