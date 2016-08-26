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
import time
import uploader
from uploader import UploaderError
from .. import dropbox_api
from .. import db_auth
from ..db_auth import AUTH_URL
from .. import kodi
from ..kodi import i18n
from .. import log_utils

APP_KEY = '6943gzynff6zkcz'
APP_SECRET = 'fp8d96951grzf78'
INTERVALS = 5

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
                db.upload_file(full_path, log, overwrite=True)
                res = db.share(full_path)
                return res.get('url')
                
        except dropbox_api.ErrorResponse as e:
            raise UploaderError('Upload Failed: (%s): %s' % (e.status, e.reason))
    
    def __authorize(self):
        auth_flow = dropbox_api.DropboxOAuth2Flow(APP_KEY, APP_SECRET)
        authorize_url = auth_flow.start()
        with db_auth.DbAuth(authorize_url) as auth:
            result = auth.start_session()
            if result is None:
                raise UploaderError('Unable to start db auth session')
            else:
                pin, redirect_uri = result
            
            line1 = i18n('dropbox_visit') % (AUTH_URL)
            line2 = i18n('dropbox_pin') % (pin)
            line3 = i18n('directions')
            with kodi.ProgressDialog(i18n('dropbox_auth'), line1=line1, line2=line2, line3=line3) as pd:
                pd.update(100)
                start = time.time()
                expires = time_left = 60  # give user 1 minute
                interval = 5  # check url every 5 seconds
                while time_left > 0:
                    for _ in range(INTERVALS):
                        kodi.sleep(interval * 1000 / INTERVALS)
                        if pd.is_canceled():
                            raise UploaderError('Authorization Aborted')
                        
                        time_left = expires - int(time.time() - start)
                        if time_left < 0: time_left = 0
                        progress = time_left * 100 / expires
                        pd.update(progress)
                    
                    result = auth.get_code(pin)
                    if result.get('success'):
                        if result.get('auth_code'):
                            log_utils.log(result['auth_code'])
                            try:
                                access_token, _user_id = auth_flow.finish(result['auth_code'], redirect_uri)
                                kodi.set_setting('dropbox_token', access_token)
                                return access_token
                            except dropbox_api.ErrorResponse as e:
                                raise UploaderError('Authorization Failed (%s): %s' % (e.status, e.reason))
                else:
                    raise UploaderError('Authorization Time Out')
    
    def send_email(self, email, results):
        return None
