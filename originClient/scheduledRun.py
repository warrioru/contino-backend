import requests
from git import Repo, Git
from api.models import Project
from pathlib import Path
import os
import json

HOST = 'http://127.0.0.1:8000/'
PORT = 8000
repo = None
index = None

def update_forecast():
    Proys = Project.objects.all()
    print(Proys)
    for project in Proys:
        try:
            my_path = os.path.abspath(os.path.dirname(__file__))
            my_path = Path(my_path).parent
            path = os.path.join(my_path, 'gitOrigins/' + project.project_name)
            root = Repo(path) #thsi should be the originRepo.
            pull = root.git.remote('update')
            branches = list(root.remote().refs)
            for branch in branches:
                root.git.checkout(branch.reference.remote_head)
                updated = root.git.status('-uno')
                if ("Your branch is behind" in updated) or ("have diverged" in updated):
                    root.git.pull()#TODO:check if this works
                    is_correct_response(root)
        except BaseException:
            print(BaseException)


def is_correct_response(repo):
    remote_url = repo.remotes.origin.url
    pivot_commit = checkDelta(remote_url, repo)

    #mandar solo el delta
    delta = []
    commitsToSend = commitListtoArray(list(repo.iter_commits(pivot_commit + '..HEAD')))
    commitsToSend.reverse()
    for commit in commitsToSend:
        #patch = repo.git.show()
        patch = repo.git.format_patch('-1', '--stdout', commit) #TODO: revisar si esto es correcto, hay que usar diff para el merge info.
        parent_commit_id = repo.commit(commit).parents[0].hexsha
        current_branch = repo.active_branch.name
        parent_branch = repo.git.branch(['--contains', parent_commit_id]).replace("* ", "")#TODO: usar objeto git y no consola P.D: esto funciona?
        email = 'origin@client'#TODO:check if this is ok.
        username = repo.commit(commit).author.name
        commit_id = repo.commit(commit).hexsha
        message = repo.commit(commit).message
        offset = repo.commit(commit).author_tz_offset
        time = repo.commit(commit).authored_date
        tempCommit = json.dumps({
            'patch':str(patch),
            'remote_url': str(remote_url),
            'parent_commit_id': str(parent_commit_id),
            'commit_id': str(commit_id),
            'current_branch': str(current_branch),
            'parent_branch': str(parent_branch),
            'email': str(email),
            'username': str(username),
            'message': str(message),
            'time': str(time),
            'offset': str(offset)
        })
        delta.append(tempCommit)

    print('mando el commmit o diff al server')
    headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
    req = requests.post(HOST, data=json.dumps(delta), headers = headers)


def checkDelta(remote_url, repo):

    completeList= list(repo.iter_commits(repo.active_branch))
    idList = commitListtoArray(completeList)
    jsonList = json.dumps({'commits' : idList, 'url' : remote_url})
    req = requests.post(HOST + 'commitCheck/', data=jsonList)
    print(req.content)
    return json.loads(req.text)['pivot_commit']

def commitListtoArray(list):
    idList = []
    for commit in list:
        idList.append(commit.hexsha)
    return idList
