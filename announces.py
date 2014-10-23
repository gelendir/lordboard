import yaml
import os

sort = lambda a: a['timestamp']


class Announces(object):

    def __init__(self, filepath):
        self.filepath = filepath

    def _load(self):
        if not os.path.exists(self.filepath):
            return []

        with open(self.filepath) as f:
            return yaml.load(f)

    def all(self):
        return self._load()

    def add(self, announce):
        announces = self._load()
        found = [a for a in announces
                 if a['timestamp'] == announce['timestamp']
                 and a['category'] == announce['category']]
        if len(found) == 0:
            announces.append(announce)
            announces = sorted(announces, key=sort, reverse=True)
            self._save(announces)

    def _save(self, announces):
        with open(self.filepath, 'w') as f:
            yaml.dump(announces, f, default_flow_style=False)
