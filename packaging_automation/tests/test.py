from github import Github

g = Github("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")
repo = g.get_repo("citusdata/citus")
# contents = repo.get_clones_traffic()
contents = repo.get_clones_traffic(per="day")
print(contents)
print(contents["clones"][0].uniques)
