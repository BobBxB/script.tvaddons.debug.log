import re
import sys
import urllib
import urllib2
import json
import log_utils

USER_AGENT = 'TVA Dropbox API'
API_HOST = "api.dropbox.com"
WEB_HOST = "www.dropbox.com"
API_CONTENT_HOST = "api-content.dropbox.com"
API_NOTIFICATION_HOST = "api-notify.dropbox.com"
API_VERSION = 1
_OAUTH2_ACCESS_TOKEN_PATTERN = re.compile(r'\A[-_~/A-Za-z0-9\.\+]+=*\Z')  # From the "Bearer" token spec, RFC 6750.

class ErrorResponse(Exception):
    def __init__(self, e):
        self.status = e.code
        self.reason = e.reason

class Client(object):
    def build_path(self, target, params=None):
        """Build the path component for an API URL.

        This method urlencodes the parameters, adds them
        to the end of the target url, and puts a marker for the API
        version in front.

        Parameters
            target
              A target url (e.g. '/files') to build upon.
            params
              Optional dictionary of parameters (name to value).

        Returns
            The path and parameters components of an API URL.
        """
        if sys.version_info < (3,) and type(target) == unicode:
            target = target.encode("utf8")

        target_path = urllib.quote(target)

        params = params or {}
        params = params.copy()

        if params:
            query_string = params_to_urlencoded(params)
            return "/%s%s?%s" % (API_VERSION, target_path, query_string)
        else:
            return "/%s%s" % (API_VERSION, target_path)

    def build_url(self, host, target, params=None):
        """Build an API URL.

        This method adds scheme and hostname to the path
        returned from build_path.

        Parameters
            target
              A target url (e.g. '/files') to build upon.
            params
              Optional dictionary of parameters (name to value).

        Returns
            The full API URL.
        """
        return "https://%s%s" % (host, self.build_path(target, params))
    
    def _call_dropbox(self, target, params=None, post_data=None, body=None, headers=None, method=None,
                      auth=True, content_server=False, notification_server=False):
        if params is None: params = {}
        if headers is None: headers = {}

        if content_server:
            host = API_CONTENT_HOST
        elif notification_server:
            host = API_NOTIFICATION_HOST
        else:
            host = API_HOST

        headers['User-Agent'] = USER_AGENT
        if auth:
            headers['Authorization'] = 'Bearer %s' % (self.token)

        if method in ('GET', 'PUT'):
            url = self.build_url(host, target, params)
        else:
            url = self.build_url(host, target)

        if body and method == 'PUT':
            data = body
            headers['Content-Length'] = len(body)
            headers['Content-Type'] = 'application/octet-stream'
        elif post_data is not None:
            if isinstance(post_data, basestring):
                data = post_data
            else:
                data = urllib.urlencode(post_data, True)

        try:
            log_utils.log('url: |%s| method: |%s| data: |%s| headers: |%s|' % (url, method, len(data), headers))
            request = urllib2.Request(url, data=data, headers=headers)
            if method is not None: request.get_method = lambda: method.upper()
            response = urllib2.urlopen(request)
            result = ''
            while True:
                data = response.read()
                if not data: break
                result += data
        except urllib2.HTTPError as e:
            raise ErrorResponse(e)
        
        return json.loads(result)
    
class DropboxClient(Client):
    def __init__(self, oauth2_access_token):
        self.token = oauth2_access_token
    
    def put_file(self, full_path, file_obj, overwrite=False, parent_rev=None):
        """Upload a file.

        A typical use case would be as follows::

            f = open('working-draft.txt', 'rb')
            response = client.put_file('/magnum-opus.txt', f)
            print "uploaded:", response

        which would return the metadata of the uploaded file, similar to::

            {
                'bytes': 77,
                'icon': 'page_white_text',
                'is_dir': False,
                'mime_type': 'text/plain',
                'modified': 'Wed, 20 Jul 2011 22:04:50 +0000',
                'path': '/magnum-opus.txt',
                'rev': '362e2029684fe',
                'revision': 221922,
                'root': 'dropbox',
                'size': '77 bytes',
                'thumb_exists': False
            }

        Parameters
            full_path
              The full path to upload the file to, *including the file name*.
              If the destination folder does not yet exist, it will be created.
            file_obj
              A file-like object to upload. If you would like, you can pass a string as file_obj.
            overwrite
              Whether to overwrite an existing file at the given path. (Default ``False``.)
              If overwrite is False and a file already exists there, Dropbox
              will rename the upload to make sure it doesn't overwrite anything.
              You need to check the metadata returned for the new name.
              This field should only be True if your intent is to potentially
              clobber changes to a file that you don't know about.
            parent_rev
              Optional rev field from the 'parent' of this upload.
              If your intent is to update the file at the given path, you should
              pass the parent_rev parameter set to the rev value from the most recent
              metadata you have of the existing file at that path. If the server
              has a more recent version of the file at the specified path, it will
              automatically rename your uploaded file, spinning off a conflict.
              Using this parameter effectively causes the overwrite parameter to be ignored.
              The file will always be overwritten if you send the most recent parent_rev,
              and it will never be overwritten if you send a less recent one.

        Returns
              A dictionary containing the metadata of the newly uploaded file.

              For a detailed description of what this call returns, visit:
              https://www.dropbox.com/developers/core/docs#files-put

        Raises
              A :class:`ErrorResponse` with an HTTP status of:

              - 400: Bad request (may be due to many things; check e.error for details).
              - 503: User over quota.
        """
        path = format_path('/files_put/auto/%s' % (full_path))
        params = {'overwrite': bool(overwrite)}
        if parent_rev is not None:
            params['parent_rev'] = parent_rev

        if hasattr(file_obj, 'read'):
            body = file_obj.read()
        else:
            body = file_obj
        
        return self._call_dropbox(path, params, body=body, method='PUT', content_server=True)

    def share(self, path, short_url=True):
        """Create a shareable link to a file or folder.

        Shareable links created on Dropbox are time-limited, but don't require any
        authentication, so they can be given out freely. The time limit should allow
        at least a day of shareability, though users have the ability to disable
        a link from their account if they like.

        Parameters
            path
              The file or folder to share.

        Returns
              A dictionary that looks like the following example::

                {'url': u'https://db.tt/c0mFuu1Y', 'expires': 'Tue, 01 Jan 2030 00:00:00 +0000'}

              For a detailed description of what this call returns, visit:
              https://www.dropbox.com/developers/core/docs#shares

        Raises
              A :class:`ErrorResponse` with an HTTP status of:

              - 400: Bad request (may be due to many things; check e.error for details).
              - 404: Unable to find the file at the given path.
        """
        path = format_path('/shares/auto/%s' % (path))
        data = {'short_url': short_url}
        return self._call_dropbox(path, post_data=data)

class DropboxOAuth2FlowBase(Client):

    def __init__(self, consumer_key, consumer_secret):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

    def _get_authorize_url(self, redirect_uri, state):
        params = {'response_type': 'code', 'client_id': self.consumer_key}
        if redirect_uri is not None:
            params['redirect_uri'] = redirect_uri
        if state is not None:
            params['state'] = state

        return self.build_url(WEB_HOST, '/oauth2/authorize', params)

    def _finish(self, code, redirect_uri):
        path = '/oauth2/token'
        data = {'grant_type': 'authorization_code', 'code': code,
                'client_id': self.consumer_key, 'client_secret': self.consumer_secret}
        if redirect_uri is not None:
            data['redirect_uri'] = redirect_uri

        response = self._call_dropbox(path, post_data=data, auth=False)
        return response["access_token"], response["uid"]

class DropboxOAuth2FlowNoRedirect(DropboxOAuth2FlowBase):
    """
    OAuth 2 authorization helper for apps that can't provide a redirect URI
    (such as the command-line example apps).

    Example::
        auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)

        authorize_url = auth_flow.start()
        print "1. Go to: " + authorize_url
        print "2. Click \\"Allow\\" (you might have to log in first)."
        print "3. Copy the authorization code."
        auth_code = raw_input("Enter the authorization code here: ").strip()

        try:
            access_token, user_id = auth_flow.finish(auth_code)
        except ErrorResponse, e:
            print('Error: %s' % (e,))
            return

        c = DropboxClient(access_token)
    """

    def __init__(self, consumer_key, consumer_secret):
        """
        Construct an instance.

        Parameters
          consumer_key
            Your API app's "app key"
          consumer_secret
            Your API app's "app secret"
        """
        super(self.__class__, self).__init__(consumer_key, consumer_secret)

    def start(self):
        """
        Starts the OAuth 2 authorization process.

        Returns
            The URL for a page on Dropbox's website.  This page will let the user "approve"
            your app, which gives your app permission to access the user's Dropbox account.
            Tell the user to visit this URL and approve your app.
        """
        return self._get_authorize_url(None, None)

    def finish(self, code):
        """
        If the user approves your app, they will be presented with an "authorization code".  Have
        the user copy/paste that authorization code into your app and then call this method to
        get an access token.

        Parameters
          code
            The authorization code shown to the user when they approved your app.

        Returns
            A pair of ``(access_token, user_id)``.  ``access_token`` is a string that
            can be passed to DropboxClient.  ``user_id`` is the Dropbox user ID (string) of the
            user that just approved your app.

        Raises
            The same exceptions as :meth:`DropboxOAuth2Flow.finish()`.
        """
        return self._finish(code, None)


def params_to_urlencoded(params):
    """
    Returns a application/x-www-form-urlencoded 'str' representing the key/value pairs in 'params'.
    
    Keys are values are str()'d before calling urllib.urlencode, with the exception of unicode
    objects which are utf8-encoded.
    """
    def encode(o):
        if isinstance(o, unicode):
            return o.encode('utf8')
        else:
            return str(o)
    utf8_params = {}
    for k, v in params.iteritems():
        utf8_params[encode(k)] = encode(v)
    return urllib.urlencode(utf8_params)

def format_path(path):
    """Normalize path for use with the Dropbox API.

    This function turns multiple adjacent slashes into single
    slashes, then ensures that there's a leading slash but
    not a trailing slash.
    """
    if not path:
        return path

    path = re.sub(r'/+', '/', path)

    if path == '/':
        return (u"" if isinstance(path, unicode) else "")
    else:
        return '/' + path.strip('/')
