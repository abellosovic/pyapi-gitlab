# -*- coding: utf-8 -*-
"""
pyapi-gitlab, a gitlab python wrapper for the gitlab API
by Itxaka Serrano Garcia <itxakaserrano@gmail.com>
Check the license on the LICENSE file
"""

import requests as rq

from .proxy import ProxyRequests
from . import exceptions

try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus
    basestring = str


class Gitlab(object):
    """Gitlab class"""

    def __init__(self, host, token="", oauth_token="", verify_ssl=True, auth=None, timeout=None, proxies=None):
        """on init we setup the token used for all the api calls and all the urls

        :param host: host of gitlab
        :param token: token
        :param proxies:
        {
          'http': 'http://10.10.1.10:3128',
          'https': 'http://10.10.1.10:1080',
        }
        """
        if token != "":
            self.token = token
            self.headers = {"PRIVATE-TOKEN": self.token}
        if oauth_token != "":
            self.oauth_token = oauth_token
            self.headers = {"Authorization": 'Bearer {}'.format(self.oauth_token)}
        if not host:
            raise ValueError("host argument may not be empty")
        self.host = host.rstrip('/')
        if self.host.startswith('http://') or self.host.startswith('https://'):
            pass
        else:
            self.host = 'https://' + self.host

        self.auth = auth
        self.api_url = self.host + "/api/v3"
        self.projects_url = self.api_url + "/projects"
        self.users_url = self.api_url + "/users"
        self.keys_url = self.api_url + "/user/keys"
        self.groups_url = self.api_url + "/groups"
        self.search_url = self.api_url + "/projects/search"
        self.hook_url = self.api_url + "/hooks"
        self.namespaces_url = self.api_url + "/namespaces"
        self.session_url = self.api_url + "/session"
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.requests = ProxyRequests(proxies=proxies) if proxies else rq
        self.rq_params = { "headers": self.headers, "verify": self.verify_ssl, "auth": self.auth, "timeout": self.timeout }

    def login(self, email=None, password=None, user=None):
        """Logs the user in and setups the header with the private token

        :param user: gitlab user
        :param password: gitlab password
        :return: True if login successfull
        """
        if user != None:
            data = {"login": user, "password": password}
        elif email != None:
            data = {"email": email, "password": password}
        else:
            raise ValueError('Neither username nor email provided to login')

        request = self.requests.post("{0}/api/v3/session".format(self.host), data=data,
                                     verify=self.verify_ssl,
                                     auth=self.auth,
                                     timeout=self.timeout,
                                     headers={"connection": "close"})
        if request.status_code == 201:
            self.token = request.json()['private_token']
            self.headers = {"PRIVATE-TOKEN": self.token, "connection": "close"}
            return True
        else:
            msg = request.json()['message']
            raise exceptions.HttpError(msg)

    def setsudo(self, user=None):
        """Set the subsequent API calls to the user provided

        :param user: User id or username to change to, None to return to the logged user
        :return: Nothing
        """
        if user is None:
            try:
                self.headers.pop("SUDO")
            except KeyError:
                pass
        else:
            self.headers["SUDO"] = user

    def getusers(self, search=None, page=1, per_page=20):
        """Return a user list

        :param search: Optional search query
        :param page: Which page to return (default is 1)
        :param per_page: Number of items to return per page (default is 20)
        :return: returs a dictionary of the users, false if there is an error
        """
        data = {'page': page, 'per_page': per_page}
        if search:
            data['search'] = search
        request = self.requests.get(self.users_url, params=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getuser(self, user_id):
        """Get info for a user identified by id

        :param user_id: id of the user
        :return: False if not found, a dictionary if found
        """
        request = self.requests.get("{0}/{1}".format(self.users_url, user_id), **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createuser(self, name, username, password, email, **kwargs):
        """Create a user

        :param name: Obligatory
        :param username: Obligatory
        :param password: Obligatory
        :param email: Obligatory
        :param kwargs: Any param the the Gitlab API supports
        :return: True if the user was created,false if it wasn't(already exists)
        """
        data = {"name": name, "username": username, "password": password, "email": email}

        if kwargs:
            data.update(kwargs)

        request = self.requests.post(self.users_url, data=data, **self.rq_params)
        if request.status_code == 201:
            return request.json()
        elif request.status_code == 404:
            return False

    def deleteuser(self, user_id):
        """Deletes an user by ID

        :param user_id: id of the user to delete
        :return: True if it deleted, False if it couldn't. False could happen for several reasons, but there isn't a good way of differenting them
        """
        request = self.requests.delete("{0}/{1}".format(self.users_url, user_id), **self.rq_params)
        return request.status_code == 200

    def currentuser(self):
        """Returns the current user parameters. The current user is linked
        to the secret token

        :return: a list with the current user properties
        """
        request = self.requests.get("{0}/api/v3/user".format(self.host), **self.rq_params)
        return request.json()

    def edituser(self, user_id, **kwargs):
        """Edits an user data.

        :param user_id: id of the user to change
        :param kwargs: Any param the the Gitlab API supports
        :return: Dict of the user
        """
        data = {}

        if kwargs:
            data.update(kwargs)

        request = self.requests.put("{0}/{1}".format(self.users_url, user_id), data=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def blockuser(self, user_id, **kwargs):
        """Block a user.

        :param user_id: id of the user to change
        :param kwargs: Any param the the Gitlab API supports
        :return: Dict of the user
        """
        data = {}

        if kwargs:
            data.update(kwargs)

        request = self.requests.put("{0}/{1}/block".format(self.users_url, user_id), data=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getsshkeys(self):
        """Gets all the ssh keys for the current user

        :return: a dictionary with the lists
        """
        request = self.requests.get(self.keys_url, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getsshkey(self, key_id):
        """Get a single ssh key identified by key_id

        :param key_id: the id of the key
        :return: the key itself
        """
        request = self.requests.get("{0}/{1}".format(self.keys_url, key_id), **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:

            return False

    def addsshkey(self, title, key):
        """Add a new ssh key for the current user

        :param title: title of the new key
        :param key: the key itself
        :return: true if added, false if it didn't add it (it could be because the name or key already exists)
        """
        data = {"title": title, "key": key}
        request = self.requests.post(self.keys_url, data=data, **self.rq_params)
        return request.status_code == 201

    def addsshkeyuser(self, user_id, title, key):
        """Add a new ssh key for the user identified by id

        :param user_id: id of the user to add the key to
        :param title: title of the new key
        :param key: the key itself
        :return: true if added, false if it didn't add it (it could be because the name or key already exists)
        """
        data = {"title": title, "key": key}

        request = self.requests.post("{0}/{1}/keys".format(self.users_url, user_id), data=data, **self.rq_params)
        return request.status_code == 201

    def deletesshkey(self, key_id):
        """Deletes an sshkey for the current user identified by id

        :param key_id: the id of the key
        :return: False if it didn't delete it, True if it was deleted
        """
        request = self.requests.delete("{0}/{1}".format(self.keys_url, key_id),**self.rq_params)
        return request.content == b"null"

    def getprojects(self, page=1, per_page=20):
        """Returns a dictionary of all the projects

        :return: list with the repo name, description, last activity,web url, ssh url, owner and if its public
        """
        data = {'page': page, 'per_page': per_page}

        request = self.requests.get(self.projects_url, params=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getprojectsall(self, page=1, per_page=20):
        """Returns a dictionary of all the projects for admins only

        :return: list with the repo name, description, last activity,web url, ssh url, owner and if its public
        """
        data = {'page': page, 'per_page': per_page}

        request = self.requests.get("{0}/all".format(self.projects_url), params=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getprojectsowned(self, page=1, per_page=20):
        """Returns a dictionary of all the projects for the current user

        :return: list with the repo name, description, last activity, web url, ssh url, owner and if its public
        """
        data = {'page': page, 'per_page': per_page}

        request = self.requests.get("{0}/owned".format(self.projects_url), params=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getproject(self, project_id):
        """Get info for a project identified by id or namespace/project_name

        :param project_id: id or namespace/project_name of the project
        :return: False if not found, a dictionary if found
        """
        if isinstance(project_id, basestring):
            project_id = quote_plus(project_id)
        request = self.requests.get("{0}/{1}".format(self.projects_url, project_id), **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getprojectevents(self, project_id, page=1, per_page=20):
        """Get the project identified by id, events(commits)

        :param project_id: id of the project
        :return: False if no project with that id, a dictionary with the events if found
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/events".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createproject(self, name, **kwargs):
        """Creates a new project owned by the authenticated user.

        :param name: new project name
        :param path: custom repository name for new project. By default generated based on name
        :param namespace_id: namespace for the new project (defaults to user)
        :param description: short project description
        :param issues_enabled:
        :param merge_requests_enabled:
        :param wiki_enabled:
        :param snippets_enabled:
        :param public: if true same as setting visibility_level = 20
        :param visibility_level:
        :param sudo:
        :param import_url:
        :return:
        """
        data = {"name": name}

        if kwargs:
            data.update(kwargs)

        request = self.requests.post(self.projects_url, data=data, **self.rq_params)
        if request.status_code == 201:
            return request.json()
        elif request.status_code == 403:
            if "Your own projects limit is 0" in request.text:
                print(request.text)
                return False
        else:
            return False

    def editproject(self, project_id, **kwargs):
        """Edit an existing project.

        :param name: new project name
        :param path: custom repository name for new project. By default generated based on name
        :param default_branch: they default branch
        :param description: short project description
        :param issues_enabled:
        :param merge_requests_enabled:
        :param wiki_enabled:
        :param snippets_enabled:
        :param public: if true same as setting visibility_level = 20
        :param visibility_level:
        :return:
        """
        data = {"id": project_id}

        if kwargs:
            data.update(kwargs)

        request = self.requests.put("{0}/{1}".format(self.projects_url, project_id), data=data, **self.rq_params)

        if request.status_code == 200:
            return True
        elif request.status_code == 400:
            if "Your param's are invalid" in request.text:
                print(request.text)
                return False
        else:
            return False

    def shareproject(self, project_id, group_id, group_access):
        """Allow to share project with group.

        :param project_id: The ID of a project
        :param group_id: The ID of a group
        :param group_access: Level of permissions for sharing
        :return: True is success
        """
        data = {"id": project_id, "group_id": group_id, "group_access": group_access}
        request = self.requests.post("{0}/{1}/share".format(self.projects_url, project_id),data=data, **self.rq_params)
        return request.status_code == 201

    def deleteproject(self, project_id):
        """Delete a project

        :param project_id: project id
        :return: always true
        """
        request = self.requests.delete("{0}/{1}".format(self.projects_url, project_id), **self.rq_params)
        return request.status_code == 200

    def createprojectuser(self, user_id, name, **kwargs):
        """Creates a new project owned by the specified user. Available only for admins.

        :param user_id: user_id of owner
        :param name: new project name
        :param description: short project description
        :param default_branch: 'master' by default
        :param issues_enabled:
        :param merge_requests_enabled:
        :param wiki_enabled:
        :param snippets_enabled:
        :param public: if true same as setting visibility_level = 20
        :param visibility_level:
        :param import_url:
        :param sudo:
        :return:
        """
        data = {"name": name}

        if kwargs:
            data.update(kwargs)

        request = self.requests.post("{0}/user/{1}".format(self.projects_url, user_id), data=data, **self.rq_params)
        return request.status_code == 201

    def getprojectmembers(self, project_id, query=None, page=1, per_page=20):
        """Lists the members of a given project id

        :param project_id: the project id
        :param query: Optional search query
        :param page: Which page to return (default is 1)
        :param per_page: Number of items to return per page (default is 20)
        :return: the projects memebers, false if there is an error
        """
        data = {'page': page, 'per_page': per_page}
        if query:
            data['query'] = query
        request = self.requests.get(
            "{0}/{1}/members".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def addprojectmember(self, project_id, user_id, access_level):
        """Adds a project member to a project

        :param project_id: project id
        :param user_id: user id
        :param access_level: "owner", "master", "developer", "reporter", "guest"
        :return: True if success
        """
        access_level = self.get_access_level_code(access_level=access_level)
        data = {"id": project_id, "user_id": user_id, "access_level": access_level}

        request = self.requests.post(
            "{0}/{1}/members".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        return request.status_code == 201

    def editprojectmember(self, project_id, user_id, access_level):
        """Edit a project member

        :param project_id: project id
        :param user_id: user id
        :param access_level: "owner", "master", "developer", "reporter", "guest"
        :return: True if success
        """
        access_level = self.get_access_level_code(access_level)
        data = {"id": project_id, "user_id": user_id, "access_level": access_level}
        request = self.requests.put(
            "{0}/{1}/members/{2}".format(self.projects_url, project_id, user_id), data=data, **self.rq_params)
        return request.status_code == 200

    def deleteprojectmember(self, project_id, user_id):
        """Delete a project member

        :param project_id: project id
        :param user_id: user id
        :return: always true
        """
        request = self.requests.delete(
            "{0}/{1}/members/{2}".format(self.projects_url, project_id, user_id), **self.rq_params
        )
        return request.status_code == 200

    def getprojecthooks(self, project_id, page=1, per_page=20):
        """Get all the hooks from a project

        :param project_id: project id
        :return: the hooks
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/hooks".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getprojecthook(self, project_id, hook_id):
        """Get a particular hook from a project

        :param project_id: project id
        :param hook_id: hook id
        :return: the hook
        """
        request = self.requests.get(
            "{0}/{1}/hooks/{2}".format(self.projects_url, project_id, hook_id), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def addprojecthook(self, project_id, url, push=False, issues=False, merge_requests=False, tag_push=False, **kwargs):
        """Add a hook to a project

        :param id_: project id
        :param url: url of the hook
        :param push: Trigger hook on push events
        :param issues: Trigger hook on issues events
        :param merge_requests: Trigger hook on merge_requests events
        :param tag_push:  Trigger hook on push_tag events
        :param kwargs: Any other param the the Gitlab API supports
        :return: True if success
        """
        data = {"id": project_id, "url": url}
        data['push_events'] = int(bool(push))
        data['issues_events'] = int(bool(issues))
        data['merge_requests_events'] = int(bool(merge_requests))
        data['tag_push_events'] = int(bool(tag_push))
        if kwargs:
            for key, value in kwargs.iteritems():
                data[key] = int(bool(value))

        request = self.requests.post("{0}/{1}/hooks".format(self.projects_url, project_id), data=data, **self.rq_params)
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def editprojecthook(self, project_id, hook_id, url, push=False,
                        issues=False, merge_requests=False, tag_push=False, **kwargs):
        """Edit an existing hook from a project

        :param id_: project id
        :param hook_id: hook id
        :param url: the new url
        :param push: Trigger hook on push events
        :param issues: Trigger hook on issues events
        :param merge_requests: Trigger hook on merge_requests events
        :param tag_push:  Trigger hook on push_tag events
        :param kwargs: Any other param the the Gitlab API supports
        :return: True if success
        """
        data = {"id": project_id, "hook_id": hook_id, "url": url}
        data['push_events'] = int(bool(push))
        data['issues_events'] = int(bool(issues))
        data['merge_requests_events'] = int(bool(merge_requests))
        data['tag_push_events'] = int(bool(tag_push))
        if kwargs:
            for key, value in kwargs.iteritems():
                data[key] = int(bool(value))

        request = self.requests.put(
            "{0}/{1}/hooks/{2}".format(self.projects_url, project_id, hook_id), data=data, **self.rq_params
        )
        return request.status_code == 200

    def deleteprojecthook(self, project_id, hook_id):
        """Delete a project hook

        :param project_id: project id
        :param hook_id: hook id
        :return: True if success
        """
        request = self.requests.delete(
            "{0}/{1}/hooks/{2}".format(self.projects_url, project_id, hook_id), **self.rq_params)
        return request.status_code == 200

    def getsystemhooks(self, page=1, per_page=20):
        """Get all system hooks

        :return: list of hooks
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(self.hook_url, params=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def addsystemhook(self, url):
        """Add a system hook

        :param url: url of the hook
        :return: True if success
        """
        data = {"url": url}
        request = self.requests.post(self.hook_url, data=data, **self.rq_params)
        return request.status_code == 201

    def testsystemhook(self, hook_id):
        """Test a system hook

        :param hook_id: hook id
        :return: list of hooks
        """
        data = {"id": hook_id}
        request = self.requests.get(self.hook_url, data=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def deletesystemhook(self, hook_id):
        """Delete a project hook

        :param hook_id: hook id
        :return: True if success
        """
        data = {"id": hook_id}
        request = self.requests.delete("{0}/{1}".format(self.hook_url, hook_id), data=data, **self.rq_params)
        return request.status_code == 200

    def getbranches(self, project_id):
        """Get a list of repository branches from a project, sorted by name alphabetically.
        GET /projects/:id/repository/branches
        :param (int) project_id: project id
        :return:
        [
          {
            "name": "master",
            "protected": true,
            "developers_can_push": false,
            "developers_can_merge": false,
            "commit": {
              "author_email": "john@example.com",
              "author_name": "John Smith",
              "authored_date": "2012-06-27T05:51:39-07:00",
              "committed_date": "2012-06-28T03:44:20-07:00",
              "committer_email": "john@example.com",
              "committer_name": "John Smith",
              "id": "7b5c3cc8be40ee161ae89a06bba6229da1032a0c",
              "message": "add projects API",
              "parent_ids": [
                "4ad91d3c1144c406e50c7b33bae684bd6837faf8"
              ]
            }
          },
          ...
        ]
        """
        request = self.requests.get(
            "{0}/{1}/repository/branches".format(self.projects_url, project_id), **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getbranch(self, project_id, branch):
        """Get a single project repository branch.
        GET /projects/:id/repository/branches/:branch

        :param project_id: The ID of a project
        :param branch: The name of the branch
        :return:
        {
          "name": "master",
          "protected": true,
          "developers_can_push": false,
          "developers_can_merge": false,
          "commit": {
            "author_email": "john@example.com",
            "author_name": "John Smith",
            "authored_date": "2012-06-27T05:51:39-07:00",
            "committed_date": "2012-06-28T03:44:20-07:00",
            "committer_email": "john@example.com",
            "committer_name": "John Smith",
            "id": "7b5c3cc8be40ee161ae89a06bba6229da1032a0c",
            "message": "add projects API",
            "parent_ids": [
              "4ad91d3c1144c406e50c7b33bae684bd6837faf8"
            ]
          }
        }
        """
        request = self.requests.get(
            "{0}/{1}/repository/branches/{2}".format(self.projects_url, project_id, branch), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createbranch(self, project_id, branch, ref):
        """Create branch from commit SHA or existing branch
        POST /projects/:id/repository/branches

        :param project_id:  The ID of a project
        :param branch: The name of the branch
        :param ref: Create branch from commit SHA or existing branch
        :return: True if success, False if not
        """
        data = {"id": project_id, "branch_name": branch, "ref": ref}

        request = self.requests.post(
            "{0}/{1}/repository/branches".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def deletebranch(self, project_id, branch):
        """Delete branch by name
        DELETE /projects/:id/repository/branches/:branch
        :param project_id:  The ID of a project
        :param branch: The name of the branch
        :return: True if success, False if not
        """

        request = self.requests.delete(
            "{0}/{1}/repository/branches/{2}".format(self.projects_url, project_id, branch), **self.rq_params
        )

        return request.status_code == 200

    def protectbranch(self, project_id, branch, developers_can_push=None, developers_can_merge=None):
        """Protects a single project repository branch. This is an idempotent function, protecting an already protected
        repository branch still returns a 200 OK status code.
        PUT /projects/:id/repository/branches/:branch/protect
        :param project_id: The ID of a project
        :param branch: The name of the branch
        :param developers_can_push: Flag if developers can push to the branch
        :param developers_can_merge: Flag if developers can merge to the branch
        :return: True if success
        """
        params = {}
        if developers_can_push is not None:
            params.update({"developers_can_push": developers_can_push})
        if developers_can_push is not None:
            params.update({"developers_can_merge": developers_can_merge})

        request = self.requests.put(
            "{0}/{1}/repository/branches/{2}/protect".format(self.projects_url, project_id, branch),
            params=params, **self.rq_params
        )
        return request.status_code == 200

    def unprotectbranch(self, project_id, branch):
        """Unprotects a single project repository branch. This is an idempotent function, unprotecting an already
        unprotected repository branch still returns a 200 OK status code.
        PUT /projects/:id/repository/branches/:branch/unprotect
        :param project_id: The ID of a project
        :param branch: The name of the branch
        :return: True if success
        """
        request = self.requests.put(
            "{0}/{1}/repository/branches/{2}/unprotect".format(self.projects_url, project_id, branch), **self.rq_params)
        return request.status_code == 200

    def createforkrelation(self, project_id, from_project_id):
        """Create a fork relation. This DO NOT create a fork but only adds a link as fork the relation between 2 repositories

        :param project_id: project id
        :param from_project_id: from id
        :return: True if success, False if not
        """
        data = {"id": project_id, "forked_from_id": from_project_id}
        request = self.requests.post(
            "{0}/{1}/fork/{2}".format(self.projects_url, project_id, from_project_id), data=data, **self.rq_params
        )
        return request.status_code == 201

    def removeforkrelation(self, project_id):
        """Remove an existing fork relation. this DO NOT remove the fork,only the relation between them

        :param project_id: project id
        :return: true if success
        """
        request = self.requests.delete(
            "{0}/{1}/fork".format(self.projects_url, project_id), **self.rq_params
        )
        return request.status_code == 200

    def createfork(self, project_id):
        """Forks a project into the user namespace of the authenticated user.

        :param project_id: Project ID to fork
        :return: True if succeed
        """

        request = self.requests.post(
            "{0}/fork/{1}".format(self.projects_url, project_id), timeout=self.timeout, verify=self.verify_ssl
        )

        return request.status_code == 200

    def getissues(self, page=1, per_page=20):
        """Return a global list of issues for your user.

        :return: list of issues
        """
        data = {'page': page, 'per_page': per_page}

        request = self.requests.get("{0}/api/v3/issues".format(self.host), params=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getprojectissues(self, project_id, page=1, per_page=20, **kwargs):
        """Return a list of issues for project id.

        :param: project_id: The id for the project.
        :return: list of issues
        """
        kwargs['page'] = page
        kwargs['per_page'] = per_page
        data = kwargs

        request = self.requests.get(
            "{0}/{1}/issues".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getprojectissue(self, project_id, issue_id):
        """Get an specific issue id from a project

        :param project_id: project id
        :param issue_id: issue id
        :return: the issue
        """
        request = self.requests.get(
            "{0}/{1}/issues/{2}".format(self.projects_url, project_id, issue_id), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createissue(self, project_id, title, **kwargs):
        """Create a new issue

        :param project_id: project id
        :param title: title of the issue
        :return: dict with the issue created
        """
        data = {"id": id, "title": title}
        if kwargs:
            data.update(kwargs)
        request = self.requests.post(
            "{0}/{1}/issues".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def editissue(self, project_id, issue_id, **kwargs):
        """Edit an existing issue data

        :param project_id: project id
        :param issue_id: issue id
        :return: true if success
        """
        data = {"id": project_id, "issue_id": issue_id}
        if kwargs:
            data.update(kwargs)
        request = self.requests.put(
            "{0}/{1}/issues/{2}".format(self.projects_url, project_id, issue_id), data=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def deleteissue(self, project_id, issue_id):
        """Delete an existing issue

        :param project_id: project_id
        :param issue_id: issue id
        :return: true if success
        """
        data = {"id": project_id, "issue_id": issue_id}
        request = self.requests.delete(
            "{0}/{1}/issues/{2}".format(self.projects_url, project_id, issue_id), data=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getmilestones(self, project_id, page=1, per_page=20):
        """Get the milestones for a project

        :param project_id: project id
        :return: the milestones
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/milestones".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getmilestone(self, project_id, milestone_id):
        """Get an specific milestone

        :param project_id: project id
        :param milestone_id: milestone id
        :return: dict with the new milestone
        """
        request = self.requests.get(
            "{0}/{1}/milestones/{2}".format(self.projects_url, project_id, milestone_id), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createmilestone(self, project_id, title, **kwargs):
        """Create a new milestone

        :param project_id: project id
        :param title: title
        :param description: description
        :param due_date: due date
        :param sudo: do the request as another user
        :return: dict of the new issue
        """
        data = {"id": project_id, "title": title}

        if kwargs:
            data.update(kwargs)

        request = self.requests.post(
            "{0}/{1}/milestones".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def editmilestone(self, project_id, milestone_id, **kwargs):
        """Edit an existing milestone

        :param project_id: project id
        :param milestone_id: milestone id
        :param title: title
        :param description: description
        :param due_date: due date
        :param state_event: state
        :param sudo: do the request as another user
        :return: dict with the modified milestone
        """
        data = {"id": project_id, "milestone_id": milestone_id}
        if kwargs:
            data.update(kwargs)
        request = self.requests.put(
            "{0}/{1}/milestones/{2}".format(self.projects_url, project_id, milestone_id), data=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getmilestoneissues(self, project_id, milestone_id, page=1, per_page=20):
        """Get the issues associated with a milestone

        :param project_id: project id
        :param milestone_id: milestone id
        :return: list of issues
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/milestones/{2}/issues".format(self.projects_url, project_id, milestone_id), params=data,
            **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getdeploykeys(self, project_id):
        """Get a list of a project's deploy keys.

        :param project_id: project id
        :return: the keys in a dictionary if success, false if not
        """
        request = self.requests.get(
            "{0}/{1}/keys".format(self.projects_url, project_id), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getdeploykey(self, project_id, key_id):
        """Get a single key.

        :param project_id: project id
        :param key_id: key id
        :return: the key in a dict if success, false if not
        """
        request = self.requests.get(
            "{0}/{1}/keys/{2}".format(self.projects_url, project_id, key_id), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def adddeploykey(self, project_id, title, key):
        """Creates a new deploy key for a project.

        :param project_id: project id
        :param title: title of the key
        :param key: the key itself
        :return: true if sucess, false if not
        """
        data = {"id": project_id, "title": title, "key": key}

        request = self.requests.post(
            "{0}/{1}/keys".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def deletedeploykey(self, project_id, key_id):
        """Delete a deploy key from a project

        :param project_id: project id
        :param key_id: key id to delete
        :return: true if success, false if not
        """
        request = self.requests.delete(
            "{0}/{1}/keys/{2}".format(self.projects_url, project_id, key_id),**self.rq_params
        )
        return request.status_code == 200

    def creategroup(self, name, path, **kwargs):
        """Creates a new group

        :param name: The name of the group
        :param path: The path for the group
        :param kwargs: Any param the the Gitlab API supports
        :return: dict of the new group
        """

        data = {'name': name, 'path': path}

        if kwargs:
            data.update(kwargs)

        request = self.requests.post(self.groups_url, data=data, **self.rq_params)
        if request.status_code == 201:
            return request.json()
        else:
            msg = request.json()['message']
            raise exceptions.HttpError(msg)

    def getgroups(self, group_id=None, page=1, per_page=20):
        """Retrieve group information

        :param group_id: Specify a group. Otherwise, all groups are returned
        :return: list of groups
        """
        data = {'page': page, 'per_page': per_page}

        request = self.requests.get(
            "{0}/{1}".format(self.groups_url, group_id if group_id else ""), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def moveproject(self, group_id, project_id):
        """Move a given project into a given group

        :param group_id: ID of the destination group
        :param project_id: ID of the project to be moved
        :return: dict of the updated project
        """
        request = self.requests.post(
            "{0}/{1}/projects/{2}".format(self.groups_url, group_id, project_id), **self.rq_params
        )
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def getmergerequests(self, project_id, page=1, per_page=20, state=None):
        """Get all the merge requests for a project.

        :param project_id: ID of the project to retrieve merge requests for
        :param state: Passes merge request state to filter them by it
        :return: list with all the merge requests
        """
        data = {'page': page, 'per_page': per_page, 'state': state}

        request = self.requests.get(
            '{0}/{1}/merge_requests'.format(self.projects_url, project_id), params=data, **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getmergerequest(self, project_id, mergerequest_id):
        """Get information about a specific merge request.

        :param project_id: ID of the project
        :param mergerequest_id: ID of the merge request
        :return: dict of the merge request
        """
        request = self.requests.get(
            '{0}/{1}/merge_request/{2}'.format(self.projects_url, project_id, mergerequest_id), **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getmergerequestcomments(self, project_id, mergerequest_id, page=1, per_page=20):
        """Get comments of a merge request.

        :param project_id: ID of the project
        :param mergerequest_id: ID of the merge request
        :return: list of the comments
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            '{0}/{1}/merge_request/{2}/comments'.format(self.projects_url, project_id, mergerequest_id),
            params=data, **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getmergerequestchanges(self, project_id, mergerequest_id):
        """Get changes of a merge request.

        :param project_id: ID of the project
        :param mergerequest_id: ID of the merge request
        :return: information about the merge request including files and changes
        """
        request = self.requests.get(
            '{0}/{1}/merge_request/{2}/changes'.format(self.projects_url, project_id, mergerequest_id),
            **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createmergerequest(self, project_id, sourcebranch, targetbranch,
                           title, target_project_id=None, assignee_id=None):
        """Create a new merge request.

        :param project_id: ID of the project originating the merge request
        :param sourcebranch: name of the branch to merge from
        :param targetbranch: name of the branch to merge to
        :param title: Title of the merge request
        :param assignee_id: Assignee user ID
        :return: dict of the new merge request
        """
        data = {'source_branch': sourcebranch,
                'target_branch': targetbranch,
                'title': title,
                'assignee_id': assignee_id,
                'target_project_id': target_project_id}

        request = self.requests.post(
            '{0}/{1}/merge_requests'.format(self.projects_url, project_id), data=data, **self.rq_params
        )
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def updatemergerequest(self, project_id, mergerequest_id, **kwargs):
        """Update an existing merge request.

        :param project_id: ID of the project originating the merge request
        :param mergerequest_id: ID of the merge request to update
        :param sourcebranch: name of the branch to merge from
        :param targetbranch: name of the branch to merge to
        :param title: Title of the merge request
        :param assignee_id: Assignee user ID
        :param closed: MR status.  True = closed
        :return: dict of the modified merge request
        """
        data = {}

        if kwargs:
            data.update(kwargs)

        request = self.requests.put(
            '{0}/{1}/merge_request/{2}'.format(self.projects_url, project_id, mergerequest_id),
            data=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def acceptmergerequest(self, project_id, mergerequest_id, merge_commit_message=None):
        """Update an existing merge request.

        :param project_id: ID of the project originating the merge request
        :param mergerequest_id: ID of the merge request to accept
        :param merge_commit_message: Custom merge commit message
        :return: dict of the modified merge request
        """

        data = {'merge_commit_message': merge_commit_message}

        request = self.requests.put(
            '{0}/{1}/merge_request/{2}/merge'.format(self.projects_url, project_id, mergerequest_id),
            data=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def addcommenttomergerequest(self, project_id, mergerequest_id, note):
        """Add a comment to a merge request.

        :param project_id: ID of the project originating the merge request
        :param mergerequest_id: ID of the merge request to comment on
        :param note: Text of comment
        :return: True if success
        """
        request = self.requests.post(
            '{0}/{1}/merge_request/{2}/comments'.format(self.projects_url, project_id, mergerequest_id),
            data={'note': note}, **self.rq_params
        )
        return request.status_code == 201

    def getsnippets(self, project_id, page=1, per_page=20):
        """Get all the snippets of the project identified by project_id

        :param project_id: project id to get the snippets from
        :return: list of dictionaries
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/snippets".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getsnippet(self, project_id, snippet_id):
        """Get one snippet from a project

        :param project_id: project id to get the snippet from
        :param snippet_id: snippet id
        :return: dictionary
        """
        request = self.requests.get(
            "{0}/{1}/snippets/{2}".format(self.projects_url, project_id, snippet_id), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createsnippet(self, project_id, title, file_name, code, visibility_level=0):
        """Creates an snippet

        :param project_id: project id to create the snippet under
        :param title: title of the snippet
        :param file_name: filename for the snippet
        :param code: content of the snippet
        :param visibility_level: snippets can be either private (0), internal(10) or public(20)
        :return: True if correct, false if failed
        """
        data = {"id": project_id, "title": title, "file_name": file_name, "code": code}
        if visibility_level in [0, 10, 20]:
            data["visibility_level"] = visibility_level
        request = self.requests.post(
            "{0}/{1}/snippets".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def getsnippetcontent(self, project_id, snippet_id):
        """Get raw content of a given snippet

        :param project_id: project_id for the snippet
        :param snippet_id: snippet id
        :return: the content of the snippet
        """
        request = self.requests.get(
            "{0}/{1}/snippets/{2}/raw".format(self.projects_url, project_id, snippet_id), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def deletesnippet(self, project_id, snippet_id):
        """Deletes a given snippet

        :param project_id: project_id
        :param snippet_id: snippet id
        :return: True if success
        """
        request = self.requests.delete(
            "{0}/{1}/snippets/{2}".format(self.projects_url, project_id, snippet_id), **self.rq_params
        )
        return request.status_code == 200

    def getrepositories(self, project_id, page=1, per_page=20):
        """Gets all repositories for a project id

        :param project_id: project id
        :return: list of repos
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/repository/branches".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getrepositorybranch(self, project_id, branch):
        """Get a single project repository branch.

        :param project_id: project id
        :param branch: branch
        :return: dict of the branch
        """
        request = self.requests.get(
            "{0}/{1}/repository/branches/{2}".format(self.projects_url, project_id, branch), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        elif request.status_code == 404:
            if request.json()['message'] == "404 Branch does not exist Not Found":
                # In the future we should raise an exception here
                return False
        else:
            return False

    def protectrepositorybranch(self, project_id, branch):
        """Protects a single project repository branch. This is an idempotent function,
        protecting an already protected repository branch still returns a 200 OK status code.

        :param project_id: project id
        :param branch: branch to protech
        :return: dict with the branch
        """
        request = self.requests.put(
            "{0}/{1}/repository/branches/{2}/protect".format(self.projects_url, project_id, branch),
            **self.rq_params
           )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def unprotectrepositorybranch(self, project_id, branch):
        """Unprotects a single project repository branch. This is an idempotent function,
        unprotecting an already unprotected repository branch still returns a 200 OK status code.

        :param project_id: project id
        :param branch: branch to unprotect
        :return: dict with the branch
        """
        request = self.requests.put(
            "{0}/{1}/repository/branches/{2}/unprotect".format(self.projects_url, project_id, branch),
            **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return

    def getrepositorytags(self, project_id, page=1, per_page=20):
        """Get a list of repository tags from a project, sorted by name in reverse alphabetical order.

        :param project_id: project id
        :return: list with all the tags
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/repository/tags".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createrepositorytag(self, project_id, tag_name, ref, message=None):
        """Creates new tag in the repository that points to the supplied ref

        :param project_id: project id
        :param tag_name: tag
        :param ref: sha1 of the commit or branch to tag
        :param message: message
        :return: dict
        """

        data = {"id": project_id, "tag_name": tag_name, "ref": ref, "message": message}
        request = self.requests.post(
            "{0}/{1}/repository/tags".format(self.projects_url, project_id), data=data, **self.rq_params
        )

        if request.status_code == 201:
            return request.json()
        else:
            return False

    def deleterepositorytag(self, project_id, tag_name):
        """Deletes tag in the repository 

        :param project_id: project id
        :param tag_name: tag
        :return: dict
        """

        data = {"tag_name": tag_name}
        request = self.requests.delete(
            "{0}/{1}/repository/tags/{2}".format(self.projects_url, project_id, tag_name), data=data, **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def addcommenttocommit(self, project_id, author, sha, path, line, note):
        """Adds an inline comment to a specific commit
        :param project_id project id
        :param author The author info as returned by createmergerequest
        :param sha The name of a repository branch or tag or if not given the default branch
        :param path The file path
        :param line The line number
        :param note Text of comment
        """

        data = {
            "author": author,
            "note": note,
            "path": path,
            "line": line,
            "line_type": "new"
        }

        request = self.requests.post(
            "{0}/{1}/repository/commits/{2}/comments".format(self.projects_url, project_id, sha), data=data,
            **self.rq_params
        )
        return request.status_code == 201

    def getrepositorycommits(self, project_id, ref_name=None, page=1, per_page=20):
        """Get a list of repository commits in a project.

        :param project_id: The ID of a project
        :param ref_name: The name of a repository branch or tag or if not given the default branch
        :return: list of commits
        """
        data = {'page': page, 'per_page': per_page}
        if ref_name is not None:
            data.update({"ref_name": ref_name})
        request = self.requests.get(
            "{0}/{1}/repository/commits".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getrepositorycommit(self, project_id, sha1):
        """Get a specific commit identified by the commit hash or name of a branch or tag.

        :param project_id: The ID of a project
        :param sha1: The commit hash or name of a repository branch or tag
        :return: dic tof commit
        """
        request = self.requests.get(
            "{0}/{1}/repository/commits/{2}".format(self.projects_url, project_id, sha1), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getrepositorycommitdiff(self, project_id, sha1):
        """Get the diff of a commit in a project

        :param project_id: The ID of a project
        :param sha1: The name of a repository branch or tag or if not given the default branch
        :return: dict with the diff
        """
        request = self.requests.get(
            "{0}/{1}/repository/commits/{2}/diff".format(self.projects_url, project_id, sha1), **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getrepositorytree(self, project_id, **kwargs):
        """Get a list of repository files and directories in a project.

        :param project_id: The ID of a project
        :param path: The path inside repository. Used to get contend of subdirectories
        :param ref_name: The name of a repository branch or tag or if not given the default branch
        :return: dcit with the tree
        """
        data = {}
        if kwargs:
            data.update(kwargs)

        request = self.requests.get(
            "{0}/{1}/repository/tree".format(self.projects_url, project_id), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getrawfile(self, project_id, sha1, filepath):
        """Get the raw file contents for a file by commit SHA and path.

        :param project_id: The ID of a project
        :param sha1: The commit or branch name
        :param filepath: The path the file
        :return: raw file contents
        """
        data = {"filepath": filepath}
        request = self.requests.get(
            "{0}/{1}/repository/blobs/{2}".format(self.projects_url, project_id, sha1), params=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.content
        else:
            return False

    def getrawblob(self, project_id, sha1):
        """Get the raw file contents for a blob by blob SHA.

        :param project_id: The ID of a project
        :param sha1: the commit sha
        :return: raw blob
        """
        request = self.requests.get(
            "{0}/{1}/repository/raw_blobs/{2}".format(self.projects_url, project_id, sha1), **self.rq_params
        )
        if request.status_code == 200:
            return request.content
        else:
            return False

    def getcontributors(self, project_id, page=1, per_page=20):
        """Get repository contributors list

        :param: project_id: The ID of a project
        :return: list of contributors
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/repository/contributors".format(self.projects_url, project_id), params=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def compare_branches_tags_commits(self, project_id, from_id, to_id):
        """Compare branches, tags or commits

        :param project_id: The ID of a project
        :param from_id: the commit sha or branch name
        :param to_id: the commit sha or branch name
        :return: commit list and diff between two branches tags or commits provided by name
        """
        data = {"from": from_id, "to": to_id}
        request = self.requests.get(
            "{0}/{1}/repository/compare".format(self.projects_url, project_id), params=data, **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def searchproject(self, search, page=1, per_page=20):
        """Search for projects by name which are accessible to the authenticated user

        :param search: query to search for
        :return: list of results
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}".format(self.search_url, search), params=data,
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getfilearchive(self, project_id, filepath=""):
        """Get an archive of the repository

        :param project_id: project id
        :param filepath: path to save the file to
        :return: True if the file was saved to the filepath
        """
        request = self.requests.get(
            "{0}/{1}/repository/archive".format(self.projects_url, project_id), **self.rq_params
        )
        if request.status_code == 200:
            if filepath == "":
                filepath = request.headers['content-disposition'].split(";")[1].split("=")[1].strip('"')
            with open(filepath, "wb") as filesave:
                filesave.write(request.content)
                # TODO: Catch oserror exceptions as no permissions and such
                # TODO: change the filepath to a path and keep always the filename?
            return True
        else:
            msg = request.json()['message']
            raise exceptions.HttpError(msg)

    def deletegroup(self, group_id):
        """Deletes an group by ID

        :param group_id: id of the group to delete
        :return: True if it deleted, False if it couldn't. False could happen for several reasons, but there isn't a good way of differentiating them
        """
        request = self.requests.delete("{0}/{1}".format(self.groups_url, group_id), **self.rq_params)
        return request.status_code == 200

    def getgroupmembers(self, group_id, page=1, per_page=20):
        """Lists the members of a given group id

        :param group_id: the group id
        :param page: which page to return (default is 1)
        :param per_page: number of items to return per page (default is 20)
        :return: the group's members
        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get("{0}/{1}/members".format(self.groups_url, group_id), params=data, **self.rq_params)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def addgroupmember(self, group_id, user_id, access_level):
        """Adds a project member to a project

        :param user_id: user id
        :param access_level: "owner", "master", "developer", "reporter", "guest"
        :return: True if success
        """
        access_level = self.get_access_level_code(access_level=access_level)
        data = {"id": group_id, "user_id": user_id, "access_level": access_level}

        request = self.requests.post("{0}/{1}/members".format(self.groups_url, group_id), data=data, **self.rq_params)
        return request.status_code == 201

    def editgroupmember(self, group_id, user_id, access_level):
        """Edit user access level in a group

        :param group_id: group id
        :param user_id: user id
        :param access_level: "owner", "master", "developer", "reporter", "guest"
        :return: True if success
        """
        access_level = self.get_access_level_code(access_level=access_level)
        data = {"id": group_id, "user_id": user_id, "access_level": access_level}

        request = self.requests.put(
            "{0}/{1}/members/{2}".format(self.groups_url, group_id, user_id), data=data, **self.rq_params)
        return request.status_code == 200

    def deletegroupmember(self, group_id, user_id):
        """Delete a group member

        :param group_id: group id to remove the member from
        :param user_id: user id
        :return: always true
        """
        request = self.requests.delete(
            "{0}/{1}/members/{2}".format(self.groups_url, group_id, user_id), **self.rq_params
        )
        return request.status_code == 200

    def addldapgrouplink(self, group_id, cn, group_access, provider):
        """Add LDAP group link

        :param id: The ID of a group
        :param cn: The CN of a LDAP group
        :param group_access: Minimum access level for members of the LDAP group
        :param provider: LDAP provider for the LDAP group (when using several providers)
        :return: True if success
        """
        data = {"id": group_id, "cn": cn, "group_access": group_access, "provider": provider}
        request = self.requests.post(
            "{0}/{1}/ldap_group_links".format(self.groups_url, group_id), data=data, **self.rq_params
        )
        return request.status_code == 201

    def deleteldapgrouplink(self, group_id, cn, provider=None):
        """Deletes a LDAP group link (for a specific LDAP provider if given)

        :param id: The ID of a group
        :param cn: The CN of a LDAP group
        :param provider: Name of a LDAP provider
        :return True if success
        """
        url = ""
        if provider:
            url = "{base}/{gid}/ldap_group_links/{provider}{cn}".format(
                base=self.groups_url, gid=group_id, cn=cn, provider=("{0}/".format(provider)))
        request = self.requests.delete(url, **self.rq_params)
        return request.status_code == 200

    def getissuewallnotes(self, project_id, issue_id, page=1, per_page=20):
        """Get the notes from the wall of a issue

        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/issues/{2}/notes".format(self.projects_url, project_id, issue_id), params=data, **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getissuewallnote(self, project_id, issue_id, note_id):
        """Get one note from the wall of the issue

        """
        request = self.requests.get(
            "{0}/{1}/issues/{2}/notes/{3}".format(self.projects_url, project_id, issue_id, note_id), **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createissuewallnote(self, project_id, issue_id, content):
        """Create a new note

        """
        data = {"body": content}
        request = self.requests.post(
            "{0}/{1}/issues/{2}/notes".format(self.projects_url, project_id, issue_id), data=data, **self.rq_params
        )

        if request.status_code == 201:
            return request.json()
        else:
            return False

    def getsnippetwallnotes(self, project_id, snippet_id, page=1, per_page=20):
        """Get the notes from the wall of a snippet

        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/snippets/{2}/notes".format(self.projects_url, project_id, snippet_id),
            params=data, **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getsnippetwallnote(self, project_id, snippet_id, note_id):
        """Get one note from the wall of the snippet

        """
        request = self.requests.get(
            "{0}/{1}/snippets/{2}/notes/{3}".format(self.projects_url, project_id, snippet_id, note_id),
            **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createsnippetewallnote(self, project_id, snippet_id, content):
        """Create a new note

        """
        data = {"body": content}
        request = self.requests.post(
            "{0}/{1}/snippets/{2}/notes".format(self.projects_url, project_id, snippet_id), data=data, **self.rq_params
        )

        if request.status_code == 201:
            return request.json()
        else:
            return False

    def getmergerequestwallnotes(self, project_id, merge_request_id, page=1, per_page=20):
        """Get the notes from the wall of a merge request

        """
        data = {'page': page, 'per_page': per_page}
        request = self.requests.get(
            "{0}/{1}/merge_requests/{2}/notes".format(self.projects_url, project_id, merge_request_id),
            params=data, **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getmergerequestwallnote(self, project_id, merge_request_id, note_id):
        """Get one note from the wall of the merge request

        """
        request = self.requests.get(
            "{0}/{1}/merge_requests/{2}/notes/{3}".format(self.projects_url, project_id, merge_request_id, note_id),
            **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createmergerequestewallnote(self, project_id, merge_request_id, content):
        """Create a new note

        """
        data = {"body": content}
        request = self.requests.post(
            "{0}/{1}/merge_requests/{2}/notes".format(self.projects_url, project_id, merge_request_id),
            data=data, **self.rq_params
        )

        if request.status_code == 201:
            return request.json()
        else:
            return False

    def createfile(self, project_id, file_path, branch_name, encoding, content, commit_message):
        """Creates a new file in the repository

        :param project_id: project id
        :param file_path: Full path to new file. Ex. lib/class.rb
        :param branch_name: The name of branch
        :param content: File content
        :param commit_message: Commit message
        :return: true if success, false if not
        """
        data = {"file_path": file_path, "branch_name": branch_name, "encoding": encoding,
                "content": content, "commit_message": commit_message}
        request = self.requests.post(
            "{0}/{1}/repository/files".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        return request.status_code == 201

    def updatefile(self, project_id, file_path, branch_name, content, commit_message):
        """Updates an existing file in the repository

        :param project_id: project id
        :param file_path: Full path to new file. Ex. lib/class.rb
        :param branch_name: The name of branch
        :param content: File content
        :param commit_message: Commit message
        :return: true if success, false if not
        """
        data = {"file_path": file_path, "branch_name": branch_name,
                "content": content, "commit_message": commit_message}
        request = self.requests.put(
            "{0}/{1}/repository/files".format(self.projects_url, project_id), data=data, **self.rq_params
        )

        return request.status_code == 200

    def getfile(self, project_id, file_path, ref):
        """Allows you to receive information about file in repository like name, size, content.
        Note that file content is Base64 encoded.

        :param project_id: project_id
        :param file_path: Full path to file. Ex. lib/class.rb
        :param ref: The name of branch, tag or commit
        :return:
        """
        data = {"file_path": file_path, "ref": ref}
        request = self.requests.get(
            "{0}/{1}/repository/files".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        if request.status_code == 200:
            return request.json()
        else:
            return False

    def deletefile(self, project_id, file_path, branch_name, commit_message):
        """Deletes existing file in the repository

        :param project_id: project id
        :param file_path: Full path to new file. Ex. lib/class.rb
        :param branch_name: The name of branch
        :param commit_message: Commit message
        :return: true if success, false if not
        """
        data = {"file_path": file_path, "branch_name": branch_name,
                "commit_message": commit_message}
        request = self.requests.delete(
            "{0}/{1}/repository/files".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        return request.status_code == 200

    def setgitlabciservice(self, project_id, token, project_url):
        """Set GitLab CI service for project

        :param project_id: project id
        :param token: CI project token
        :param project_url: CI project url
        :return: true if success, false if not
        """
        data = {"token": token, "project_url": project_url}
        request = self.requests.put(
            "{0}/{1}/services/gitlab-ci".format(self.projects_url, project_id), data=data, **self.rq_params)

        return request.status_code == 200

    def deletegitlabciservice(self, project_id, token, project_url):
        """Delete GitLab CI service settings

        :return: true if success, false if not
        """
        request = self.requests.delete(
            "{0}/{1}/services/gitlab-ci".format(self.projects_url, project_id), **self.rq_params
        )

        return request.status_code == 200

    def getlabels(self, project_id):
        """Get all labels for given project.

        :param project_id: The ID of a project
        :return: list of the labels
        """
        request = self.requests.get(
            "{0}/{1}/labels".format(self.projects_url, project_id), **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def createlabel(self, project_id, name, color):
        """Creates a new label for given repository with given name and color.

        :param project_id: The ID of a project
        :param name: The name of the label
        :param color: Color of the label given in 6-digit hex notation with leading '#' sign (e.g. #FFAABB)
        :return:
        """

        data = {"name": name, "color": color}
        request = self.requests.post(
            "{0}/{1}/labels".format(self.projects_url, project_id), data=data, **self.rq_params
        )
        if request.status_code == 201:
            return request.json()
        else:
            return False

    def deletelabel(self, project_id, name):
        """Deletes a label given by its name.

        :param project_id: The ID of a project
        :param name: The name of the label
        :return: True if succeed
        """
        data = {"name": name}

        request = self.requests.delete(
            "{0}/{1}/labels".format(self.projects_url, project_id), data=data, **self.rq_params
        )

        return request.status_code == 200

    def editlabel(self, project_id, name, new_name=None, color=None):
        """Updates an existing label with new name or now color. At least one parameter is required, to update the label.

        :param project_id: The ID of a project
        :param name: The name of the label
        :return: True if succeed
        """
        data = {"name": name, "new_name": new_name, "color": color}

        request = self.requests.put(
            "{0}/{1}/labels".format(self.projects_url, project_id), data=data, **self.rq_params
        )

        if request.status_code == 200:
            return request.json()
        else:
            return False

    def getnamespaces(self, search=None, page=1, per_page=20):
        """Return a namespace list

        :param search: Optional search query
        :param page: Which page to return (default is 1)
        :param per_page: Number of items to return per page (default is 20)
        :return: returs a list of namespaces, false if there is an error
        """
        data = {'page': page, 'per_page': per_page}
        if search:
            data['search'] = search
        request = self.requests.get(self.namespaces_url, params=data, headers=self.headers, verify=self.verify_ssl)
        if request.status_code == 200:
            return request.json()
        else:
            return False

    @staticmethod
    def getall(fn, *args, **kwargs):
        """Auto-iterate over the paginated results of various methods of the API.
        Pass the GitLabAPI method as the first argument, followed by the
        other parameters as normal. Include `page` to determine first page to poll.
        Remaining kwargs are passed on to the called method, including `per_page`.

        :param fn: Actual method to call
        :param *args: Positional arguments to actual method
        :param page: Optional, page number to start at, defaults to 1
        :param **kwargs: Keyword arguments to actual method
        :return: Yields each item in the result until exhausted, and then
        implicit StopIteration; or no elements if error
        """
        page = kwargs.pop('page', 1)
        while True:
            results = fn(*args, page=page, **kwargs)
            if not results:
                break
            for x in results:
                yield x
            page += 1

    @staticmethod
    def get_access_level_code(access_level):
        """Returns code of access level
        @:param access_level: "owner", "master", "developer", "reporter", "guest"
        :return int: access level code
        """
        access_level = {
            "owner": 50,
            "master": 40,
            "developer": 30,
            "reporter": 20,
            "guest": 10
        }.get(access_level)
        if not access_level:
            raise AttributeError
        return access_level