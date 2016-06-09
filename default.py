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
import re
import os
import sys
import xbmcgui
from lib import log_utils
from lib import kodi
from lib.kodi import i18n
from lib.uploaders import *
from lib.uploaders.uploader import UploaderError

def __enum(**enums):
    return type('Enum', (), enums)

MODES = __enum(
    UPLOAD_LOG='upload_log'
)

REPLACES = [
    ('://.+?:.+?@', '//USER:PASSWORD@'),
    ('<user>.+?</user>', '<user>USER</user>'),
    ('<pass>.+?</pass>', '<pass>PASSWORD</pass>')
]

FILES = [
    ('kodi.log', 'kodi.log'),
    ('kodi.old.log', 'kodi.old.log')
]

EMAIL_SENT = {True: 'Email Success', False: 'Email Failed', None: 'Email Not Supported'}
SERVER_ORDER = {'tvaddons': 1, 'pastebin': 2, 'pastie': 3}

def __get_logs():
    logs = []
    log_path = kodi.translate_path('special://logpath')
    for log in FILES:
        file_name, name = log
        full_path = os.path.join(log_path, file_name)
        if os.path.exists(full_path):
            logs.append((full_path, name))
    return logs

def upload_logs():
    logs = __get_logs()
    results = {}
    last_error = ''
    uploaders = uploader.Uploader.__class__.__subclasses__(uploader.Uploader)
    uploaders = [klass for klass in uploaders if SERVER_ORDER[klass.name]]
    uploaders.sort(key=lambda x: SERVER_ORDER[x.name])
    for log in logs:
        full_path, name = log
        if name != 'kodi.old.log' or kodi.get_setting('include_old') == 'true':
            with open(full_path, 'r') as f:
                log = f.read()
                
            for pattern, replace in REPLACES:
                log = re.sub(pattern, replace, log)
            
            for klass in uploaders:
                try:
                    log_service = klass()
                    result = log_service.upload_log(log)
                    success = log_service.send_email() if kodi.get_setting('email') else None
                    results[name] = {'result': result, 'email': success}
                    break
                except UploaderError as e:
                    log_utils.log('Uploader Error: (%s) %s: %s' % (log_service.__class__.__name__, name, e), log_utils.LOGWARNING)
                    last_error = str(e)
            else:
                log_utils.log('No succesful upload for: %s Last Error: %s' % (name, last_error), log_utils.LOGWARNING)
            
    if results:
        if 'kodi.log' in results:
            line1 = '%s: %s [I](%s)[/I]' % ('kodi.log', results['kodi.log']['result'], EMAIL_SENT[results['kodi.log']['email']])
        else:
            line1 = ''
            
        if 'kodi.old.log' in results:
            line2 = '%s: %s [I](%s)[/I]' % ('kodi.old.log', results['kodi.old.log']['result'], EMAIL_SENT[results['kodi.log']['email']])
        else:
            line2 = ''
            
        for log in results:
            log_utils.log('Log Uploaded: %s: %s' % (log, results[log]['result']), log_utils.LOGNOTICE)
        xbmcgui.Dialog().ok(i18n('logs_uploaded'), line1, line2)
    else:
        kodi.notify(i18n('logs_failed') % (last_error), duration=5000)

def __confirm_upload():
    return xbmcgui.Dialog().yesno(kodi.get_name(), i18n('upload_question'))
    
def main(argv=None):
    try:
        if kodi.get_setting('email_prompt') != 'true' and not kodi.get_setting('email'):
            kodi.set_setting('email_prompt', 'true')
            kodi.show_settings()
            
        if __confirm_upload():
            upload_logs()
    except UploaderError as e:
        log_utils.log('Uploader Error: %s' % (e), log_utils.LOGWARNING)
        kodi.notify(msg=str(e))

if __name__ == '__main__':
    sys.exit(main())
