# Cauldron apps

Django apps used in Cauldron. Mainly models and implementations for poolsched. We include all the applications and models in a single package to be used from different parts of cauldron: webserver and workers.

## cauldron

Include all the models related with the project, repositories, users, etc. This is mainly used by the user interface.

## poolsched

Include all the instances of Intentions, ArchIntentions, and implementation for running them. There are many submodules for git, github, gitlab and meetup.
