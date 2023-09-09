import configparser
import os

class ConfigManager:
    def __init__(self, filename):
        self.filename = filename
        self.config = configparser.ConfigParser()

    def load_config(self):
        if not os.path.exists(self.filename):
            self.config['CONFIG'] = {
                'xml_path': 'PLACEHOLDER_PATH',
                'server_ip': 'PLACEHOLDER_IP',
                'server_port': 'PLACEHOLDER_PORT',
                'db_path': 'PLACEHOLDER_PATH',
                'cutter_name': 'PLACEHOLDER_CUTTER_NAME',
                'clean_mode': 'n'
            }
            self.save_config()
        self.config.read(self.filename)

    def save_config(self):
        with open(self.filename, 'w') as configfile:
            self.config.write(configfile)

    def get_config(self, section, key):
        return self.config[section][key]
