#!/usr/bin/python
import re
import json
import requests
import warnings
import math
from uuid import UUID

MAP_NAME = "HOME_AREA"

## TODO: Try to use function to reconstruct path for decorator's argument 'path'

class Request(object):
    def __init__(self, method, path):
        self.method = method.upper()
        self.path = path
        self.h = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept-Language": "en-US",
            "Authorization": "Basic ZGlzdHJpYnV0b3I6NjJmMmYwZjFlZmYxMGQzMTUyYzk1ZjZmMDU5NjU3NmU0ODJiYjhlNDQ4MDY0MzNmNGNmOTI5NzkyODM0YjAxNA=="
        }

    def __call__(self, f):
        def wrapper(obj, *args, **kwargs):
            payload = f(obj, *args, **kwargs)
            URL = "{}{}".format(obj.host, self.path)

            if payload is not None:
                if payload.has_key("PATH"):
                    URL = "{}{}".format(URL, payload.get("PATH"))

                if payload.has_key("BODY"):
                    payload = payload.get("BODY")

                try:
                    res = requests.request(self.method,
                                           url=URL,
                                           headers=self.h,
                                           data=json.dumps(payload),
                                           timeout=3)
                except requests.RequestException as e:
                    print(e)
                    return
            else:
                try:
                    res = requests.request(self.method,
                                           url=URL,
                                           headers=self.h,
                                           timeout=3)
                except requests.RequestException as e:
                    print(e)
                    return
            return res
        return wrapper


class MIR(object):
    def __init__(self, host):
        if not "http" in host:
            warnings.warn("WARRING: Maybe the host name is error.")

        self.host = host

    def check_response_status_code(self, res):
        if str(res.status_code).startswith("20"):
            print("[Response OK]")
        else:
            raise Exception("Response ERROR")

    def is_valid_guid(self, guid_to_test, version=1):
        try:
            guid_obj = UUID(guid_to_test, version=version)
        except ValueError:
            return False

        return str(guid_obj) == guid_to_test

    @Request(method="get", path="/status")
    def get_status(self):
        pass

    @Request(method="put", path="/status")
    def set_status(self, set_state):
        STATE = {"Ready": 3, "Pause": 4}

        # Check whether input 'set_state' is correct
        if isinstance(set_state, (str, int)):
            if isinstance(set_state, str):
                s = STATE.get(set_state, 4)
        else:
            print("ERROR type of set_state")
            return

        body = {
            "state_id": s
        }
        return body

    @Request(method="get", path="/system/info")
    def get_system_info(self):
        pass

    @Request(method="get", path="/missions")
    def get_missions(self):
        pass

    def get_mission_guid(self, mission, auto_create=True):
        r = self.get_missions()
        rjson = json.loads(r.text)
        for l in rjson:
            if l.get("name") == mission:
                return l.get("guid")
        warnings.warn("No this mission")
        return None

    @Request(method="get", path="/mission_queue")
    def get_mission_queue(self):
        pass

    @Request(method="post", path="/mission_queue")
    def post_mission_queue(self, mission):
        body = {
            "mission_id": mission
        }
        return body

    def add_mission_to_queue(self, mission):
        if not self.is_valid_guid(mission):
            mission_id = self.get_mission_guid(mission)
        r = self.post_mission_queue(mission_id)
        self.check_response_status_code(r)

    @property
    def mission_queue_is_empty(self):
        r = self.get_mission_queue()
        rjson = json.loads(r.text)
        for l in rjson:
            if l.get("state").upper() == "PENDING" or \
               l.get("state").upper() == "EXECUTING":
               return False
        return True

    @Request(method="delete", path="/mission_queue")
    def clear_mission_queue(self):
        pass

    @Request(method="get", path="/mission_groups")
    def get_groups(self):
        pass

    def get_group_guid(self, group):
        r = self.get_groups()
        rjson = json.loads(r.text)
        for l in rjson:
            if l.get("name") == group:
                return l.get("guid")
        print("No this group")
        #print(r.text)
        return None

    @Request(method="get", path="/sessions")
    def get_sessions(self):
        pass

    def get_session_guid(self, session):
        r = self.get_sessions()
        rjson = json.loads(r.text)
        for l in rjson:
            if l.get("name") == session:
                return l.get("guid")
        print("No this session")
        #print(r.text)
        return None

    @Request(method="post", path="/missions")
    def create_new_mission(self, name, group_id="TKU_IARC", session_id="TKU_IARC"):
        print("Creating new mission name: {}, group_id: {}, session_id: {}" \
                .format(name, group_id, session_id))
        if not self.is_valid_guid(group_id):
            group_id = self.get_group_guid(group_id)
        if not self.is_valid_guid(session_id):
            session_id = self.get_session_guid(session_id)

        body = {
            "group_id": group_id,
            "session_id": session_id,
            "name": name
        }
        return body

    @Request(method="delete", path="/missions")
    def delete_mission(self, mission):
        if not self.is_valid_guid(mission):
            mission_id = self.get_mission_guid(mission)
            if mission_id is None:
                warnings.warn("No this mission to DELETE")
                return
        return {"PATH": "/" + mission_id}

    @Request(method="post", path="/missions")
    def add_action_to_mission(self, mission, action_type, parameters, priority):
        mission_guid = self.get_mission_guid(mission)
        if mission_guid is None:
            print("[WARNING] No this mission. Creating mission {}".format(mission))
            r = self.create_new_mission(mission)
            rjson = json.loads(r.text)
            mission_guid = rjson.get("guid")

        path = "/" + mission_guid + "/actions"
        body = {
            "action_type": action_type,
            "mission_id": mission_guid,
            "parameters": parameters,
            "priority": priority
        }
        return {"PATH": path, "BODY": body}

    def add_relative_move_action(self, dx=0.0, dy=0.0, dyaw=0.0, \
                                 max_speed_v=0.5, max_speed_w=0.5, \
                                 collision_detection=True):
        param = [
            { "id": "x", "value": dx},
            { "id": "y", "value": dy},
            { "id": "orientation", "value": dyaw},
            { "id": "max_linear_speed", "value": max_speed_v},
            { "id": "max_angular_speed", "value": max_speed_w},
            { "id": "collision_detection", "value": collision_detection}
        ]
        self.add_action_to_mission("TKU_TMP", "relative_move", param, 1)

    def relative_move(self, dx=0.0, dy=0.0, dyaw=0.0, \
                      max_speed_v=0.5, max_speed_w=0.5, collision_detection=True):
        self.clear_mission_queue()
        self.delete_mission("TKU_TMP")
        self.add_relative_move_action(dx, dy, dyaw, max_speed_v, max_speed_w, collision_detection)
        self.add_mission_to_queue("TKU_TMP")

    @Request(method="get", path="/positions")
    def get_positions(self):
        pass

    @Request(method="get", path="/positions")
    def get_position_by_id(self, guid):
        return {"PATH": "/" + guid}

    def get_position_guid(self, position_name):
        r = self.get_positions()
        self.check_response_status_code(r)
        rjson = json.loads(r.text)
        for l in rjson:
            if l.get("name") == position_name:
                return l.get("guid")
        print("No this position")
        return None

    @Request(method="post", path="/positions")
    def add_position(self, name, x, y, yaw, position_type=0):
        map_guid = self.get_map_guid(MAP_NAME)
        body = {
            "map_id": map_guid,
            "name": name,
            "orientation": yaw,
            "pos_x": x,
            "pos_y": y,
            "type_id": position_type
        }
        return body

    @Request(method="get", path="/maps")
    def get_maps(self):
        pass

    def get_map_guid(self, map_name):
        r = self.get_maps()
        rjson = json.loads(r.text)
        for l in rjson:
            if l.get("name") == map_name:
                return l.get("guid")
        print("No this position")
        return None

    @property
    def status(self):
        r = self.get_status()
        self.check_response_status_code(r)
        rjson = json.loads(r.text)
        d = {
            "mir_state": rjson.get("state_text").encode('utf-8'),
            "mir_position": {
                "x": rjson.get("position").get("x"),
                "y": rjson.get("position").get("y"),
                "yaw": rjson.get("position").get("orientation")
            }
        }
        return d

    ## Maybe this function is useless
    def arrived_position(self, position_name):
        id = self.get_position_guid(position_name)
        r = self.get_position_by_id(id)
        self.check_response_status_code(r)
        rjson = json.loads(r.text)

        if rjson.get("name") == position_name:
            rs = self.get_status()
            rsjson = json.loads(rs.text)
            dx = rjson.get("pos_x") - rsjson.get("position").get("x")
            dy = rjson.get("pos_y") - rsjson.get("position").get("y")
            dyaw = rjson.get("orientation") - rsjson.get("position").get("orientation")

            if math.hypot(dx, dy) < 0.1 and abs(dyaw) < 10:
                print("Distanse is short enough. {}, {}, {}".format(dx, dy, dyaw))
                return True
            else:
                return False

    ## TODO: Add action with try-catch
    ## TODO: map
