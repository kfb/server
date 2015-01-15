import sys
from agithub import Github

hook_id = "3856601"
reponame = "ctrl-repo"
username = sys.argv[1]
password = sys.argv[2]

github = Github(username, password)
status, response = github.repos[username][reponame].hooks[hook_id].pings.post()

print (status, response)