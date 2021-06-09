
import git
repo = git.Repo("/vagrant/release/tools")
commit = repo.head.commit
print(commit.message)