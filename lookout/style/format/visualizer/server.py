"""Visualize features of the format analyzer."""
from collections.abc import Mapping as Mapping_abc
from logging import basicConfig
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from bblfsh import BblfshClient
from flask import abort, Flask, jsonify, request, Response
from flask_cors import CORS
import numpy

from lookout.core.api.service_data_pb2 import File
from lookout.style.format.descriptions import CLASS_PRINTABLES, CLASS_REPRESENTATIONS
from lookout.style.format.feature_extractor import FeatureExtractor
from lookout.style.format.feature_utils import VirtualNode
from lookout.style.format.model import FormatModel


basicConfig(level="INFO")
app = Flask(__name__)
CORS(app)


def _convert_to_jsonable(mapping: MutableMapping[Any, Any]) -> MutableMapping[Any, Any]:
    for key, value in mapping.items():
        if isinstance(value, numpy.ndarray):
            mapping[key] = value.tolist()
        elif isinstance(value, Mapping_abc):
            mapping[key] = _convert_to_jsonable(value)
    return mapping


def _vnode_to_dict(vnode: VirtualNode) -> Mapping[str, Any]:
    return {
        "start": {"offset": int(vnode.start.offset),
                  "col": int(vnode.start.col),
                  "line": int(vnode.start.line)},
        "end": {"offset": int(vnode.end.offset),
                "col": int(vnode.end.col),
                "line": int(vnode.end.line)},
        "value": vnode.value,
        "path": vnode.path,
        "roles": [role for role in vnode.node.roles] if vnode.node else [],
        "y": vnode.y,
        "internal_type": vnode.node.internal_type if vnode.node else None,
    }


@app.route("/", methods=["POST"])
def return_features() -> Response:
    """Featurize the given code."""
    body = request.get_json()
    code = body["code"]
    babelfish_address = body["babelfish_address"]
    language = body["language"]
    client = BblfshClient(babelfish_address)
    res = client.parse(filename="", contents=code.encode(), language=language)
    if res.status != 0:
        abort(500)
    model = FormatModel().load(str(Path(__file__).parent / "models" / "model.asdf"))
    rules = model[language]
    file = File(content=code.encode(), uast=res.uast, language="javascript")
    config = rules.origin_config["feature_extractor"]
    config["return_sibling_indices"] = True
    fe = FeatureExtractor(language=language, **config)
    res = fe.extract_features([file])
    if res is None:
        abort(500)
    X, y, vnodes_y, vnodes, sibling_indices = res
    y_pred, winners = rules.predict(X, True)
    app.logger.info("returning features of shape %d, %d" % X.shape)
    return jsonify({"code": code,
                    "features": X.tolist(),
                    "predictions": y_pred.tolist(),
                    "sibling_indices": sibling_indices,
                    "feature_names": fe.feature_names,
                    "class_representations": CLASS_REPRESENTATIONS,
                    "class_printables": CLASS_PRINTABLES,
                    "vnodes": list(map(_vnode_to_dict, vnodes)),
                    "config": _convert_to_jsonable(rules.origin_config)})
