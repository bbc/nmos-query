# Copyright 2017 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def convert(obj, rtype, target_ver, downgrade_ver=None):
    # Ensure an API version is set on the object
    if "@_apiversion" not in obj:
        obj["@_apiversion"] = "v1.0"

    # Fix max supported API version
    if _api_ver_compare(target_ver, "v1.3") > 0:
        return None

    # Convert high versioned resources for low versioned output
    if _api_ver_compare(target_ver, "v1.3") < 0 and obj["@_apiversion"] == "v1.3":
        obj = _v1_3_to_v1_2(obj, rtype)
        obj["@_apiversion"] = "v1.2"
    if _api_ver_compare(target_ver, "v1.2") < 0 and obj["@_apiversion"] == "v1.2":
        obj = _v1_2_to_v1_1(obj, rtype)
        obj["@_apiversion"] = "v1.1"
    if _api_ver_compare(target_ver, "v1.1") < 0 and obj["@_apiversion"] == "v1.1":
        obj = _v1_1_to_v1_0(obj, rtype)
        obj["@_apiversion"] = "v1.0"

    # Check if the object's API version is permitted in the output
    if target_ver == obj["@_apiversion"]:
        return obj
    elif downgrade_ver and _api_ver_compare(obj["@_apiversion"], downgrade_ver) >= 0:
        return obj

    # Fallback
    return None


def _remove_if_present(obj, delete_key):
    if isinstance(obj, list):
        for element in obj:
            _remove_if_present(element, delete_key)
    if isinstance(obj, dict):
        for key, val in obj.copy().items():
            if isinstance(val, dict):
                val = _remove_if_present(val, delete_key)
            if isinstance(val, list):
                for element in val:
                    val = _remove_if_present(element, delete_key)
            if key == delete_key:
                del obj[delete_key]
    return obj


def _remove_keys_from_resource(obj, rtype, downgrade_mapping):
    if rtype in downgrade_mapping:
        for key in downgrade_mapping[rtype]:
            _remove_if_present(obj, key)
    return obj


def _api_ver_compare(first, second):
    ver_first = first[1:].split(".")
    ver_second = second[1:].split(".")
    if ver_first[0] < ver_second[0]:
        return -1
    elif ver_first[0] > ver_second[0]:
        return 1
    elif ver_first[1] < ver_second[1]:
        return -1
    elif ver_first[1] > ver_second[1]:
        return 1
    else:
        return 0


def _v1_1_to_v1_0(obj, rtype):

    downgrade_mapping = {
        'nodes': [
            "api", "description", "tags", "clocks"
        ],
        "flows": [
            "device_id", "media_type", "colorspace", "components", "frame_height", "frame_width",
            "interlace_mode", "bit_depth", "sample_rate", "DID_SDID", "grain_rate", "transfer_characteristic"
        ],
        "devices": [
            "controls", "description", "tags"
        ],
        "receivers": [
            "caps"
        ],
        "sources": [
            "clock_name", "channels", "grain_rate"
        ]
    }

    return _remove_keys_from_resource(obj, rtype, downgrade_mapping)


def _v1_2_to_v1_1(obj, rtype):

    downgrade_mapping = {
        'nodes': [
            "interfaces"
        ],
        "receivers": [
            "interface_bindings"
        ],
        "senders": [
            "interface_bindings", "caps", "subscription"
        ]
    }

    return _remove_keys_from_resource(obj, rtype, downgrade_mapping)


def _v1_3_to_v1_2(obj, rtype):

    downgrade_mapping = {
        'nodes': [
            "attached_network_device", "authorization"
        ],
        "devices": [
            "authorization"
        ],
        "sources": [
            "event_type"
        ],
        "flows": [
            "event_type"
        ]
    }

    return _remove_keys_from_resource(obj, rtype, downgrade_mapping)
