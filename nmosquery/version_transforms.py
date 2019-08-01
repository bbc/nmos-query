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

from nmoscommon.utils import downgrade_api_version


def convert(obj, rtype, target_ver, downgrade_ver=None):

    downgrade_map = {
        "v1.1": {
            "node": ["description", "tags", "api", "clocks"],
            "device": ["description", "tags", "controls"],
            "source": ["clock_name", "grain_rate", "channels"],
            "flow": [
                "device_id", "grain_rate", "media_type", "sample_rate", "bit_depth", "DID_SDID", "frame_width",
                "frame_height", "interlace_mode", "colorspace", "components", "transfer_characteristic"
            ],
        },
        "v1.2": {
            "node": ["interfaces"],
            "sender": ["interface_bindings", "caps", "subscription"],
            "receiver": ["interface_bindings"]
        },
        "v1.3": {
            "node": ["attached_network_device", "authorization"],
            "device": ["authorization"],
            "source": ["event_type"],
            "flow": ["event_type"],
        }
    }

    return downgrade_api_version(obj, rtype, target_ver, downgrade_map, downgrade_ver)
