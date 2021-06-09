from enum import Enum


class GithubPipelineTriggerType(Enum):
    push = 1
    schedule = 2
    workflow_dispatch = 3

print([e.name for e in GithubPipelineTriggerType])


supported_distros = {
    "el/7": 140,
    "el/8": 205,
    "ol/7": 146,
    "debian/buster": 150,
    "debian/stretch": 149,
    "ubuntu/focal": 210,
    "ubuntu/bionic": 190,
    "ubuntu/xenial": 165
}

print([e for e in supported_distros])