"""
PyBB - an experimental interface to NodeBB forums by Luke Taylor

Features:
    - Implements classes for Forums and Users
    - Automatically exposes all information that is available through the API
      through the use of Python's __getattr__ magic method
    - Implements certain "smart" data enrichments, such as:
        - Returns user profile images as PIL images if PIL is installed
        - Returns values that represent times as Python datetime objects
Planned features:
    - Classes for Topics and Posts
    - More data enrichments

Also tries to implement 'smart' methods for returning data:
    - Return a datetime object for any time-related value
"""

import datetime
import inspect
from io import BytesIO
import json
import os

try:  # Python 3
    from urllib.parse import urlparse, urljoin
except ImportError:  # Python 2
    from urlparse import urlparse, urljoin
# Try to import PIL, if it's not installed fail gracefully
try:
    from PIL import Image
    hasPIL = True
except ImportError:
    hasPIL = False

import requests


# ------ HELPER CLASSES ------ #

class AttrDict (object):
    """ A pseudo-dict class that allows accessing of items either by item
        access or by attribute access """
    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        return self.data[key]

    def __getitem__(self, key):
        return self.data[key]


class _ForumObjectBase (object):
    """ Base class inherited by all forum-related classes """
    def __init__(self, *args, **kwargs):
        self._name = "data"
        self.data = {}
        self.aliases = {}  # __getattr__ looks at this
        self._setup(*args, **kwargs)

    def _setup(self):
        pass

    def dump_data(self, path="."):
        """Dump data to a JSON file"""
        path = os.path.join(path, self._name + ".json")
        with open(path, "w") as f:
            f.write(json.dumps(self.data, indent=2, sort_keys=True))

    def __getattr__(self, key):
        """ Powers magical __getattr__ methods. Implements smart
            functions for returning from a dictionary, specifically
            converting dates and times to datetime objects. """
        # Handle data if key is directly in data
        if key in self.data:
            out = self.data[key]
            # Attempt to return a datetime for a 13-digit timestamp
            if str(out).isdigit() and len(str(out)) == 13:
                return datetime.datetime.fromtimestamp(int(out) / 1000)

            # Attempt to return a datetime for an ISO 8601-formatted date
            try:
                return datetime.datetime.strptime(out, "%Y-%m-%dT%H:%M:%S.%fZ")
            except (ValueError, TypeError):
                pass

            # Return the raw value if it can't be converted
            return out
        # Handle aliases to properties
        elif key in self.aliases:
            return self.__getattr__(self.aliases[key])
        # Throw an error if key does not exist
        else:
            raise AttributeError(self.__class__.__name__ +
                                 " instance has no attribute '" + key + "'")

    def __str__(self):
        return self._name

# ------ MAIN CLASSES ------ #


class Forum(_ForumObjectBase):
    """ Represents a NodeBB forum. Forums are composed of Users and Topics """
    def _setup(self, url):
        # Assert that the URL goes to a NodeBB forum
        if requests.head(url).headers.get("X-Powered-By") != "NodeBB":
            raise ValueError("That\'s not a NodeBB forum")

        # Store some basic forum info upon instantination
        self.url = url
        self.endpoint = urljoin(self.url, "api/")   # URL for the API page
        self.api_url = self.endpoint                # ^ Alias to that ^
        self._req = requests.get(self.api_url)      # Request for the API call
        self.basedata = json.loads(self._req.text)  # API response as a dict

        self.cfurl = urljoin(self.endpoint, "config")  # |\
        self.configreq = requests.get(self.cfurl)  # |- Forum config
        self.config = json.loads(self.configreq.text)  # |/

        self._name = self.config["siteTitle"]

        self.aliases = {"title": "siteTitle"}

        self.data = dict(                  # Combination of data from:
            list(self.basedata.items()) +  # Front page
            list(self.config.items())      # Forum config
        )

    # -- Methods for the creating subordinate types -- #
    def User(self, username):
        """ Allows creation of Users by Forum("url").User("username") """
        return User(self, username)

    @property
    def topics(self):
        return [Topic(data, self) for data in self.data["topics"]]


class User(_ForumObjectBase):
    def _setup(self, forum, username):
        self.forum = forum
        self.username = username
        self._name = username
        # URL for the API page about the user
        self.api_url = urljoin(self.forum.endpoint, "user/" + username)
        # Requests object for the API call
        self.req = requests.get(self.api_url)
        # Dict representing API response
        self.data = json.loads(self.req.text)

    @property
    def image(self):
        """Returns a PIL image for the user"s profile image"""
        imgurl = urljoin(self.forum.endpoint, self.picture)
        if not hasPIL:
            return imgurl
        else:
            imgdata = requests.get(imgurl).content
            file = BytesIO(imgdata)
            return Image.open(file)


class Topic(_ForumObjectBase):
    def _setup(self, data, forum):
        self.forum = forum
        self.data = data
        self.category = self.category["name"]
        self.user = forum.User(self.user["username"])


if __name__ == "__main__":
    # This is my pitiful excuse for "unit tests," just to make sure I didn't
    # break anything

    # Get object for omz-software forums
    forum = Forum("https://forum.omz-software.com/")
    # Print some random info about the forum
    print("Forum title: " + str(forum))  # Title of forum
    print("Version: " + forum.version)  # Version of NodeBB


    # Get a forum user and display some random info
    user1 = forum.User("Webmaster4o")
    print("Logged in: " + str(user1.loggedIn))  # Is the user logged in?
    print("Post count: " + str(user1.postcount))  # How many posts the user has
    weekday = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
               4: "Friday", 5: "Saturday", 6: "Sunday"}[
                   user1.joindate.weekday()
    ]
    print("Joined on a " + weekday)  # Day of week joined


    topic1 = forum.topics[0]
    print("Recent topic: " + topic1.title)
    topic1.user.image.show()
