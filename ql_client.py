import httpx


class QLClient:
    def __init__(self, base_url, client_id=None, client_secret=None, host_header=None):
        self.base_url = base_url.rstrip("/")
        self._headers = {"Host": host_header} if host_header else {}
        self._client = httpx.Client(base_url=self.base_url, timeout=30, headers=self._headers)

        if client_id and client_secret:
            self._bearer = self._fetch_oauth_token(client_id, client_secret)
            if self._bearer:
                self._client.headers.update({"Authorization": f"Bearer {self._bearer}"})

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _fetch_oauth_token(self, client_id, client_secret):
        try:
            resp = httpx.get(
                f"{self.base_url}/open/auth/token",
                params={"client_id": client_id, "client_secret": client_secret},
                headers=self._headers,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", {}).get("token", "")
            return ""
        except Exception:
            return ""

    def _get(self, path, params=None):
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, data=None):
        resp = self._client.post(path, json=data)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path, data=None):
        resp = self._client.put(path, json=data)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path, data=None):
        resp = self._client.request("DELETE", path, json=data)
        resp.raise_for_status()
        return resp.json()

    # ==================================================================
    # 定时任务  /crons
    # ==================================================================

    def list_crons(self, search=None):
        params = {"searchValue": search} if search else {}
        data = self._get("/open/crons", params=params)
        if data.get("code") == 200:
            result = data.get("data", {})
            if isinstance(result, dict):
                return result.get("data", [])
            if isinstance(result, list):
                return result
        return []

    def get_cron(self, cron_id):
        data = self._get(f"/open/crons/{cron_id}")
        if data.get("code") == 200:
            return data.get("data")
        return None

    def get_cron_by_name(self, name):
        crons = self.list_crons(search=name)
        for c in crons:
            if c.get("name") == name:
                return c
        return None

    def create_cron(self, cron_data):
        """cron_data: {command, schedule, name?, labels?, ...}"""
        return self._post("/open/crons", data=cron_data)

    def update_cron(self, cron_data):
        """cron_data: {id, command, schedule, name?, labels?, ...}"""
        return self._put("/open/crons", data=cron_data)

    def delete_crons(self, ids):
        """ids: [id1, id2, ...]"""
        return self._delete("/open/crons", data=ids)

    def run_cron(self, cron_id):
        return self._put("/open/crons/run", data=[cron_id])

    def run_cron_by_name(self, name):
        cron = self.get_cron_by_name(name)
        if not cron:
            return {"code": -1, "msg": f"未找到任务: {name}"}
        return self.run_cron(cron["id"])

    def stop_cron(self, cron_id):
        return self._put("/open/crons/stop", data=[cron_id])

    def stop_cron_by_name(self, name):
        cron = self.get_cron_by_name(name)
        if not cron:
            return {"code": -1, "msg": f"未找到任务: {name}"}
        return self.stop_cron(cron["id"])

    def disable_cron(self, cron_id):
        return self._put("/open/crons/disable", data=[cron_id])

    def disable_cron_by_name(self, name):
        cron = self.get_cron_by_name(name)
        if not cron:
            return {"code": -1, "msg": f"未找到任务: {name}"}
        return self.disable_cron(cron["id"])

    def enable_cron(self, cron_id):
        return self._put("/open/crons/enable", data=[cron_id])

    def enable_cron_by_name(self, name):
        cron = self.get_cron_by_name(name)
        if not cron:
            return {"code": -1, "msg": f"未找到任务: {name}"}
        return self.enable_cron(cron["id"])

    def pin_cron(self, cron_id):
        return self._put("/open/crons/pin", data=[cron_id])

    def unpin_cron(self, cron_id):
        return self._put("/open/crons/unpin", data=[cron_id])

    def get_cron_logs(self, cron_id, limit=20):
        data = self._get(f"/open/crons/{cron_id}/logs")
        if data.get("code") == 200:
            logs = data.get("data", [])
            return logs[:limit]
        return []

    def get_cron_log_content(self, cron_id):
        data = self._get(f"/open/crons/{cron_id}/log")
        if data.get("code") == 200:
            return data.get("data", "")
        return ""

    def get_cron_detail(self, cron_id=None):
        """GET /crons/detail"""
        data = self._get("/open/crons/detail")
        if data.get("code") == 200:
            result = data.get("data", {})
            if isinstance(result, dict):
                items = result.get("data", [])
            elif isinstance(result, list):
                items = result
            else:
                items = []
            if cron_id is not None:
                for item in items:
                    if item.get("id") == cron_id:
                        return item
                return None
            return items
        return None if cron_id is not None else []

    def add_cron_labels(self, ids, labels):
        """POST /crons/labels  ids:[], labels:[]"""
        return self._post("/open/crons/labels", data={"ids": ids, "labels": labels})

    def delete_cron_labels(self, ids, labels):
        """DELETE /crons/labels  ids:[], labels:[]"""
        return self._delete("/open/crons/labels", data={"ids": ids, "labels": labels})

    def import_crons(self):
        """GET /crons/import"""
        data = self._get("/open/crons/import")
        return data.get("data", []) if data.get("code") == 200 else []

    # ---- 任务视图 ----
    def list_cron_views(self):
        data = self._get("/open/crons/views")
        return data.get("data", []) if data.get("code") == 200 else []

    def create_cron_view(self, view_data):
        """view_data: {name, sorts?, filters?, filterRelation?}"""
        return self._post("/open/crons/views", data=view_data)

    def update_cron_view(self, view_data):
        """view_data: {id, name, sorts?, filters?, filterRelation?}"""
        return self._put("/open/crons/views", data=view_data)

    def delete_cron_views(self, ids):
        return self._delete("/open/crons/views", data=ids)

    def move_cron_view(self, from_index, to_index, view_id):
        return self._put("/open/crons/views/move", data={
            "fromIndex": from_index, "toIndex": to_index, "id": view_id,
        })

    def disable_cron_views(self, ids):
        return self._put("/open/crons/views/disable", data=ids)

    def enable_cron_views(self, ids):
        return self._put("/open/crons/views/enable", data=ids)

    # ==================================================================
    # 环境变量  /envs
    # ==================================================================

    def get_envs(self, search_value=None):
        params = {}
        if search_value:
            params["searchValue"] = search_value
        data = self._get("/open/envs", params=params)
        return data.get("data", []) if data.get("code") == 200 else []

    def get_env_by_id(self, env_id):
        data = self._get(f"/open/envs/{env_id}")
        return data.get("data") if data.get("code") == 200 else None

    def create_env(self, envs):
        """envs: [{name, value, remarks?}]"""
        data = self._post("/open/envs", data=envs)
        return data.get("data", []) if data.get("code") == 200 else []

    def update_env(self, env_item):
        """env_item: {id, name, value, remarks?}"""
        return self._put("/open/envs", data=env_item)

    def delete_envs(self, ids):
        return self._delete("/open/envs", data=ids)

    def disable_envs(self, ids):
        return self._put("/open/envs/disable", data=ids)

    def enable_envs(self, ids):
        return self._put("/open/envs/enable", data=ids)

    def update_env_names(self, ids, name):
        return self._put("/open/envs/name", data={"ids": ids, "name": name})

    def move_env(self, env_id, from_index, to_index):
        return self._put(f"/open/envs/{env_id}/move", data={
            "fromIndex": from_index,
            "toIndex": to_index,
        })

    def upload_envs(self, file_path):
        """POST /envs/upload multipart/form-data 上传 JSON 文件"""
        with open(file_path, "rb") as f:
            resp = self._client.post("/open/envs/upload", files={"env": f})
            resp.raise_for_status()
            return resp.json()

    # ==================================================================
    # 订阅管理  /subscriptions
    # ==================================================================

    def list_subscriptions(self, search=None):
        params = {}
        if search:
            params["searchValue"] = search
        data = self._get("/open/subscriptions", params=params)
        return data.get("data", []) if data.get("code") == 200 else []

    def get_subscription_by_name(self, name):
        subs = self.list_subscriptions(search=name)
        for s in subs:
            if s.get("alias") == name or s.get("name") == name:
                return s
        return None

    def run_subscription(self, sub_id):
        return self._put("/open/subscriptions/run", data=[sub_id])

    def run_subscription_by_name(self, name):
        sub = self.get_subscription_by_name(name)
        if not sub:
            return {"code": -1, "msg": f"未找到订阅: {name}"}
        return self.run_subscription(sub["id"])

    def stop_subscription_by_name(self, name):
        sub = self.get_subscription_by_name(name)
        if not sub:
            return {"code": -1, "msg": f"未找到订阅: {name}"}
        return self.stop_subscription(sub["id"])

    def disable_subscription_by_name(self, name):
        sub = self.get_subscription_by_name(name)
        if not sub:
            return {"code": -1, "msg": f"未找到订阅: {name}"}
        return self.disable_subscription(sub["id"])

    def enable_subscription_by_name(self, name):
        sub = self.get_subscription_by_name(name)
        if not sub:
            return {"code": -1, "msg": f"未找到订阅: {name}"}
        return self.enable_subscription(sub["id"])

    def stop_subscription(self, sub_id):
        return self._put("/open/subscriptions/stop", data=[sub_id])

    def disable_subscription(self, sub_id):
        return self._put("/open/subscriptions/disable", data=[sub_id])

    def enable_subscription(self, sub_id):
        return self._put("/open/subscriptions/enable", data=[sub_id])

    def get_subscription_log(self, sub_id):
        data = self._get(f"/open/subscriptions/{sub_id}/log")
        return data.get("data", "") if data.get("code") == 200 else ""

    def get_subscription_logs(self, sub_id, limit=20):
        data = self._get(f"/open/subscriptions/{sub_id}/logs")
        if data.get("code") == 200:
            logs = data.get("data", [])
            return logs[:limit]
        return []

    def create_subscription(self, sub_data):
        """sub_data: {type, url, schedule_type, alias, ...}"""
        return self._post("/open/subscriptions", data=sub_data)

    def update_subscription_status(self, ids, status, pid=None, log_path=None):
        body = {"ids": ids, "status": status}
        if pid:
            body["pid"] = pid
        if log_path:
            body["log_path"] = log_path
        return self._put("/open/subscriptions/status", data=body)

    # ==================================================================
    # 脚本管理  /scripts
    # ==================================================================

    def list_scripts(self, path=None):
        params = {}
        if path:
            params["path"] = path
        data = self._get("/open/scripts", params=params)
        if data.get("code") != 200:
            return []
        result = data.get("data", [])
        # 青龙不同版本返回格式：
        #   v1: {"data": [script_dict, ...]}
        #   v2: {"data": {"data": [...], "dirs": [...], "files": [...], "total": N}}
        if isinstance(result, dict):
            # 优先取 files，其次 data
            result = result.get("files", result.get("data", []))
        if not isinstance(result, list):
            return []
        # 过滤掉非 dict 的元素（如 int），只保留脚本对象
        return [s for s in result if isinstance(s, dict)]

    def get_script_detail(self, file, path=None):
        params = {"file": file}
        if path:
            params["path"] = path
        data = self._get("/open/scripts/detail", params=params)
        return data.get("data") if data.get("code") == 200 else None

    def run_script(self, filename, path=None, content=None):
        body = {"filename": filename}
        if path:
            body["path"] = path
        if content:
            body["content"] = content
        return self._put("/open/scripts/run", data=body)

    def stop_script(self, filename, path=None, pid=None):
        body = {"filename": filename}
        if path:
            body["path"] = path
        if pid:
            body["pid"] = pid
        return self._put("/open/scripts/stop", data=body)

    def delete_script(self, filename, path=None):
        body = {"filename": filename}
        if path:
            body["path"] = path
        return self._delete("/open/scripts", data=body)

    def create_script(self, filename, path=None, content=None):
        """通过 JSON 创建脚本"""
        body = {"filename": filename}
        if path:
            body["path"] = path
        if content:
            body["content"] = content
        return self._post("/open/scripts", data=body)

    def update_script(self, filename, content, path=None):
        """PUT /scripts 更新脚本内容"""
        body = {"filename": filename, "content": content}
        if path:
            body["path"] = path
        return self._put("/open/scripts", data=body)

    def download_script(self, filename, path=None):
        """POST /scripts/download"""
        body = {"filename": filename}
        if path:
            body["path"] = path
        return self._post("/open/scripts/download", data=body)

    def rename_script(self, filename, new_filename, path=None):
        """PUT /scripts/rename"""
        body = {"filename": filename, "newFilename": new_filename}
        if path:
            body["path"] = path
        return self._put("/open/scripts/rename", data=body)

    # ==================================================================
    # 依赖管理  /dependencies
    # ==================================================================

    def list_dependencies(self):
        data = self._get("/open/dependencies")
        return data.get("data", []) if data.get("code") == 200 else []

    def reinstall_dependency(self, dep_id):
        return self._put("/open/dependencies/reinstall", data=[dep_id])

    def create_dependency(self, deps):
        """deps: [{name, type, remark?}]"""
        return self._post("/open/dependencies", data=deps)

    def update_dependency(self, dep_item):
        """dep_item: {id, name, type, remark?}"""
        return self._put("/open/dependencies", data=dep_item)

    def delete_dependencies(self, ids):
        return self._delete("/open/dependencies", data=ids)

    def force_delete_dependencies(self, ids):
        return self._delete("/open/dependencies/force", data=ids)

    def get_dependency(self, dep_id):
        data = self._get(f"/open/dependencies/{dep_id}")
        return data.get("data") if data.get("code") == 200 else None

    def cancel_dependency(self, ids):
        return self._put("/open/dependencies/cancel", data=ids)

    # ==================================================================
    # 系统管理  /system
    # ==================================================================

    def get_system_info(self):
        data = self._get("/open/system")
        return data.get("data") if data.get("code") == 200 else {}

    def get_system_log(self, start_time=None, end_time=None):
        params = {}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        data = self._get("/open/system/log", params=params)
        return data.get("data") if data.get("code") == 200 else None

    def run_command(self, command):
        return self._put("/open/system/command-run", data={"command": command})

    def stop_command(self, command=None, pid=None):
        body = {}
        if command:
            body["command"] = command
        if pid:
            body["pid"] = pid
        return self._put("/open/system/command-stop", data=body)

    def send_notify(self, title, content):
        return self._put("/open/system/notify", data={
            "title": title,
            "content": content,
        })

    # ---- 系统配置 ----
    def get_system_config(self):
        data = self._get("/open/system/config")
        return data.get("data") if data.get("code") == 200 else {}

    def update_log_remove_frequency(self, frequency):
        return self._put("/open/system/config/log-remove-frequency",
                         data={"logRemoveFrequency": frequency})

    def update_cron_concurrency(self, concurrency):
        return self._put("/open/system/config/cron-concurrency",
                         data={"cronConcurrency": concurrency})

    def update_dependence_proxy(self, proxy):
        return self._put("/open/system/config/dependence-proxy",
                         data={"dependenceProxy": proxy})

    def update_node_mirror(self, mirror):
        return self._put("/open/system/config/node-mirror",
                         data={"nodeMirror": mirror})

    def update_python_mirror(self, mirror):
        return self._put("/open/system/config/python-mirror",
                         data={"pythonMirror": mirror})

    def update_linux_mirror(self, mirror):
        return self._put("/open/system/config/linux-mirror",
                         data={"linuxMirror": mirror})

    # ---- 系统操作 ----
    def check_update(self):
        return self._put("/open/system/update-check")

    def update_system(self):
        return self._put("/open/system/update")

    def reload_system(self, reload_type=None):
        body = {"type": reload_type} if reload_type else {}
        return self._put("/open/system/reload", data=body)

    def export_data(self):
        return self._put("/open/system/data/export")

    def import_data(self, file_path):
        with open(file_path, "rb") as f:
            resp = self._client.put("/open/system/data/import", files={"data": f})
            resp.raise_for_status()
            return resp.json()

    def delete_system_log(self):
        return self._delete("/open/system/log")

    # ==================================================================
    # 配置文件  /configs
    # ==================================================================

    def list_configs(self):
        data = self._get("/open/configs/files")
        return data.get("data", []) if data.get("code") == 200 else []

    def get_config_detail(self, path):
        data = self._get("/open/configs/detail", params={"path": path})
        return data.get("data") if data.get("code") == 200 else None

    def get_config_samples(self):
        """GET /configs/sample"""
        data = self._get("/open/configs/sample")
        return data.get("data", []) if data.get("code") == 200 else []

    def get_config_file(self, filename):
        """GET /configs/:file"""
        data = self._get(f"/open/configs/{filename}")
        return data.get("data") if data.get("code") == 200 else None

    def save_config(self, name, content):
        """POST /configs/save"""
        return self._post("/open/configs/save", data={"name": name, "content": content})

    # ==================================================================
    # 日志管理  /logs
    # ==================================================================

    def list_logs(self):
        data = self._get("/open/logs")
        return data.get("data", []) if data.get("code") == 200 else []

    def get_log_detail(self, path=None, file=None):
        params = {}
        if path:
            params["path"] = path
        if file:
            params["file"] = file
        data = self._get("/open/logs/detail", params=params)
        return data.get("data") if data.get("code") == 200 else None

    def get_log_file(self, filename, path=None):
        """GET /logs/:file"""
        params = {}
        if path:
            params["path"] = path
        data = self._get(f"/open/logs/{filename}", params=params)
        return data.get("data") if data.get("code") == 200 else None

    def delete_logs(self, filename, path=None, log_type=None):
        """DELETE /logs/"""
        body = {"filename": filename}
        if path:
            body["path"] = path
        if log_type:
            body["type"] = log_type
        return self._delete("/open/logs", data=body)