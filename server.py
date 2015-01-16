import SocketServer
import re
import json
import getpass
import sys

from agithub import Github
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class GithubEventHandler:
    def __init__(self, username, password, repo):
        # The basic pattern splits the input into a "verb + data" group;
        # individual handling operations might split the data further.
        self.pattern = re.compile("^(\w+) (.*)$")

        self.username = username
        self.password = password
        self.repo = repo

        self.github = Github(username, password)

        # A partial to be used in requests
        self.git_data = self.github.repos[self.username][self.repo].git

class IssueEventHandler(GithubEventHandler):
    def handle(self, event):
        # Parse the incoming event
        event = json.loads(event)

        # We're interested in tickets being opened
        if event["action"] == "opened":
            title = event["issue"]["title"]
            match = self.pattern.match(title)

            operations = {
                "add": self.add_file,
                "update": self.update_file,
            }

            if match and match.group(1) in operations:
                operations[match.group(1)](match.group(2))
            else:
                print "Couldn't understand title: '%'" % title

    def add_file(self, data, content="New file created by IssueEventHandler"):
        print "Adding file (data = '%s', content = '%s')" % (data, content)
        
        # Obtain the current HEAD
        head_sha = self._get_head_commit()

        # Create a new blob
        blob_sha = self._create_blob(content)

        # Create a new tree
        tree_sha = self._create_tree(head_sha, data, blob_sha)

        # Create a commit
        commit_sha = self._create_commit(data, tree_sha, [head_sha], "Add %s" % data)

        # Update refs/heads/master
        if self._update_refs_heads_master(commit_sha):
            print "Successfully created %s in %s" % (data, self.repo)

    def update_file(self, data):
        print "Updating file (data = '%s')" % data

        # Split the data into a filename and content pair
        name = data.split()[0]
        content = ' '.join(data.split()[1:])

        # Obtain the current HEAD
        head_sha = self._get_head_commit()

        # Create a new blob
        blob_sha = self._create_blob(content)

        # Create a new tree
        tree_sha = self._create_tree(head_sha, data, blob_sha)

        # Create a commit
        commit_sha = self._create_commit(data, tree_sha, [head_sha], "Updated content of %s" % name)

        # Update refs/heads/master
        if self._update_refs_heads_master(commit_sha):
            print "Successfully updated %s in %s" % (data, self.repo)

    def _update_refs_heads_master(self, sha):
        response = self._patch_request(self.git_data.refs.heads.master,
            {
                "sha": sha
            })

        return response

    def _create_commit(self, path, tree, parents, message):
        response = self._post_request(self.git_data.commits,
            {
                "message": message,
                "tree": tree,
                "parents": parents
            })

        return response["sha"]

    def _create_tree(self, base_tree, path, sha):
        response = self._post_request(self.git_data.trees,
            {
                "base_tree": base_tree, 
                "tree": [{
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": sha
                }]
            })

        return response["sha"]

    def _create_blob(self, content):
        response = self._post_request(self.git_data.blobs,
            {
                "content": content,
                "encoding": "utf-8"
            })

        return response["sha"]

    def _get_head_commit(self):
        response = self._get_request(self.git_data.refs.heads.master)

        return response["object"]["sha"]

    def _get_request(self, endpoint):
        status, response = endpoint.get()

        # Reset the partial
        self.git_data = self.github.repos[self.username][self.repo].git

        if 200 <= status < 300:
            return response
        else:
            print "_get_request: failed (%d)" % status
            print "_get_request: response = \n%s", response

            return None

    def _post_request(self, endpoint, payload):
        status, response = endpoint.post(body=payload)

        # Reset the partial
        self.git_data = self.github.repos[self.username][self.repo].git

        if 200 <= status < 300:
            return response
        else:
            print "_post_request: call to endpoint '%s' failed (%d)" % (endpoint, status)
            print "_post_request: response = \n%s" % response

            return None

    def _patch_request(self, endpoint, payload):
        status, response = endpoint.patch(body=payload)

        # Reset the partial
        self.git_data = self.github.repos[self.username][self.repo].git

        if 200 <= status < 300:
            return response
        else:
            print "_post_request: failed (%d)" % status
            print "_post_request: response = \n%s" % response

            return None
 
class Handler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
    def do_POST(self):
        self._set_headers()

        if self.headers["X-GitHub-Event"] == "issues":
            self.server.issues_handler.handle(self.rfile.read(int(self.headers["Content-Length"])))

class Server(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, username, password, repo):
        HTTPServer.__init__(self, server_address, RequestHandlerClass)

        # Only issues for now, but this can be extended in the future
        self.issues_handler = IssueEventHandler(username, password, repo)

if __name__ == "__main__":
    try:
        password = getpass.getpass()

        httpd = Server(('', 8080), Handler, sys.argv[1], password, sys.argv[2])
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.socket.close()
