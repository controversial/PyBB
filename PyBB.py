"""
An experimental interface to NodeBB forums. By Luke Taylor.

Implements classes for:
  - Forums
  - Users

I plan to add classes for:
  - Topics
  - Posts

Also tries to implement 'smart' methods for returning data:
  - Return a datetime object for any time-related value
"""

import datetime
from io import BytesIO
import json
import os
from PIL import Image
import requests
from urllib.parse import urlparse, urljoin


def process_data(data):
    '''Powers magical __getattr__ methods. Implements smart
       functions for returning from a dictionary, specifically
       converting dates and times to datetime objects.'''

    # Attempt to return a datetime object for a 13-digit timestamp
    if str(data).isdigit() and len(str(data)) == 13:
        return datetime.datetime.fromtimestamp(int(data) / 1000)
    # Attempt to return a datetime object for an ISO 8601-formatted date
    try:
        return datetime.datetime.strptime(data, "%Y-%m-%dT%H:%M:%S.%fZ")
    except (ValueError, TypeError):
        pass
    # Return the raw value if it can't be converted
    return data


   
class Forum:
    def __init__(self, url):
        self.url = url
        self.head = requests.head(url).headers
        if 'X-Powered-By' not in self.head or self.head['X-Powered-By'] != 'NodeBB':
            raise ValueError('That\'s not a NodeBB forum')
        # URL for the API page about the forum
        self.endpoint = urljoin(self.url, 'api/')
        self.api_url = self.endpoint
        # Requests object for the API call
        self.req = requests.get(self.api_url)
        # Dict representing API response
        self.data = json.loads(self.req.text)
        # Forum config
        self.configurl = urljoin(self.endpoint, 'config')
        self.configreq = requests.get(self.configurl)
        self.config = json.loads(self.configreq.text)
        # Forum title
        self.title = self.config['siteTitle']
        
    def dump_data(self, path='.'):
        '''Dump forum data to a JSON file'''
        path = os.path.join(path, 'forum' + '.json')
        with open(path, 'w') as f:
            f.write(json.dumps(self.data, indent=2, sort_keys=True))

    def __getattr__(self, key):
        '''Magic method that will try to return data directly
        from the API if no wrapper has been written.'''
        if key in self.data:
            out = self.data[key]
        elif key in self.config:
            out = self.config[key]
        else:
            out = None
        return process_data(out)

    # Methods for the creation of other related types
    def User(self, username):
        ''' Allows creation of Users by Forum('url').User('username') '''
        return User(self, username)


class User:
    def __init__(self, forum, username):
        self.forum = forum
        self.username = username
        # URL for the API page about the user
        self.api_url = urljoin(self.forum.endpoint, 'user/' + username)
        # Requests object for the API call
        self.req = requests.get(self.api_url)
        # Dict representing API response
        self.data = json.loads(self.req.text)

    @property
    def image(self):
        '''Returns a PIL image for the user's profile image'''
        imgurl = urljoin(self.forum.endpoint, self.picture)
        imgdata = requests.get(imgurl).content
        file = BytesIO(imgdata)
        return Image.open(file)
    
    def dump_data(self, path='.'):
        '''Dump user data to a JSON file'''
        path = os.path.join(path, self.username + '.json')
        with open(path, 'w') as f:
            f.write(json.dumps(self.data, indent=2, sort_keys=True))

    def __getattr__(self, key):
        '''Magic method that will try to return data directly
        from the API if no wrapper has been written.'''
        if key in self.data:
            out = self.data[key]
        else:
            out = None
        return process_data(out)


if __name__ == '__main__':
    # Get object for omz-software forums
    forum = Forum('https://forum.omz-software.com/')
    # Print forum title
    print(forum.title)
    # Get a forum user and show their profile picture 
    u = forum.User('Webmaster4o')
    u.image.show()
