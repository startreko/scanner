import configparser
import os

class ConfigManager:
    DEFAULT_CONFIG = {
        'CONFIG': {
            'xml_path': '\\your-server-name\\YourApp\\Default_XML_Path',
            'server_ip': 'localhost',
            'server_port': '3000',
            'db_path': '\\your-server-ip\\DefaultDB',
            'cutter': 'DefaultCutter'
        }
    }

    def __init__(self, filename):
        self.filename = filename
        self.config = configparser.ConfigParser()

    def load_config(self):
        if not os.path.exists(self.filename):
            self.config.read_dict(self.DEFAULT_CONFIG)
            self.save_config()
        self.config.read(self.filename)

    def save_config(self):
        with open(self.filename, 'w') as configfile:
            self.config.write(configfile)

    def get_config(self, section, key, default=None):
        try:
            return self.config[section][key]
        except KeyError:
            return default