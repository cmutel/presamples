from .array import IrregularPresamplesArray
from .utils import validate_presamples_dirpath, check_name_conflicts
from collections.abc import Mapping
from pathlib import Path
import json
import numpy as np
import os


class PresamplesPackage:
    """Interface for individual presample packages.

    Packages are directories, stored either locally or on a network resource (via `PyFilesystem <https://www.pyfilesystem.org/>`__.

    Presampled arrays are provided as a list of directory paths. Each directory contains a metadata file, and one or more data files:

    * ``datapackage.json``: A JSON file following the `datapackage standard <http://frictionlessdata.io/guides/data-package/>`__ that indicates the provenance of the data. The specific content of the datapackage will depend on what the presamples contains.
    All datapackage.json files should minimally have the following information:

    .. code-block:: json

        {
          "name": human readable name,
          "id": uuid,
          "profile": "data-package",
          "resources": [{
                "type": string,
                "samples": {
                    "filepath": "{id}.{data package index}.samples.npy",
                    "md5": md5 hash,
                    "shape": [rows, columns],
                    "dtype": dtype
                },
                "indices": {
                    "filepath": "{id}.{data package index}.indices.npy",
                    "md5": md5 hash
                },
                "matrix": string,
                "row from label": string,
                "row to label": string,
                "row dict": string,
                "col from label": string,
                "col to label": string,
                "col dict": string,
                "profile": "data-resource",
                "format": "npy",
                "mediatype": "application/octet-stream"
            }]
        }

    The ``resources`` list should have at least one resource. Multiple resources of different types can be present in a single datapackage. The field ``{data package index}`` doesn't have to be consecutive integers, but should be unique for each resource. If there is only one set of samples, it can be omitted entirely.

    """
    def __init__(self, path):
        self.path = Path(path)
        validate_presamples_dirpath(path)

    @property
    def metadata(self):
        return json.load(open(self.path / "datapackage.json"))

    @property
    def name(self):
        return self.metadata['name']

    @property
    def seed(self):
        return self.metadata['seed']

    def change_seed(self, new):
        """Change seed to ``new``"""
        current = json.load(open())
        current['seed'] = new
        with open(self.path / "datapackage.json", "w", encoding='utf-8') as f:
            json.dump(current, f, indent=2, ensure_ascii=False)

    @property
    def id(self):
        return self.metadata['id']

    @property
    def resources(self):
        return self.metadata['resources']

    def __len__(self):
        return len(self.resources)

    @property
    def parameters(self):
        if not hasattr(self, "_parameters"):
            self._parameters = ParametersMapping(self.path, self.resources, self.name)
        return self._parameters


class ParametersMapping(Mapping):
    def __init__(self, path, resources, package_name, sample_index=None):
        name_lists = [
            json.load(open(path / obj['names']['filepath'])) for obj in resources
        ]
        check_name_conflicts(name_lists)
        self.mapping = {
            name: index
            for lst in name_lists
            for index, name in enumerate(lst)
        }
        self.ipa = IrregularPresamplesArray(*[
            path / obj['samples']['filepath'] for obj in resources
        ])
        self.ids = [(path, package_name, name) for name in self.mapping]
        self.index = sample_index or 0

    def values(self):
        return self.ipa.sample(self.index)

    def __getitem__(self, key):
        return float(self.ipa.sample(self.index)[self.mapping[key]])

    def __len__(self):
        return len(self.mapping)

    def __contains__(self, key):
        return key in self.mapping

    def __iter__(self):
        return iter(self.mapping)