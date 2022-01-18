"""
All Plugins must contain a main function that takes a `context` argument as a 
dictionary to use for populating a jinja template (or any other supported 
templating engine) and a `config` argument which will be the current config
dictionary (e.g., contents of config.yml as a dict).

This function must return a context dictionary which will be passed to the 
template rendering engine to produce the report.

"""
