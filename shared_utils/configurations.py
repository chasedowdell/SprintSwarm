import yaml


class Configurations:

    def __init__(self, config_file='/Users/charlesdowdell/PycharmProjects/sprintswarm/config.yml'):
        self._config = self._load_config(config_file)

    def _load_config(self, config_file):
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def get(self, *keys, default=None):
        config = self._config
        for key in keys:
            if key in config:
                config = config[key]
            else:
                return default
        return config


# Initialize a global configurations object
configurations = Configurations()
