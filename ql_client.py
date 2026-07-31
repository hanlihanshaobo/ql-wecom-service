import httpx


class QLClient:
    def __init__(self, base_url, token=None, client_id=None, client_secret=None, host_header=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._headers = {"Host": host_header} if host_header else {}
        self._client = httpx.Client(base_url=self.base_url, timeout=30, headers=self._headers)

        if client_id and client_secret:
            self.token = self._fetch_oauth_token(client_id, client_secret)

        if self.token:
            self._client.headers.update({"Authorization": f"Bearer {self.token}"})

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _fetch_oauth_token(self, client_id, client_secret):
        try:
            resp = httpx.get(
                f"{self.base_url}/open/auth/token",
                params={
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
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

    # ---- 任务视图 (可选) ----
    def list_cron_views(self):
        data = self._get("/open/crons/views")
        return data.get("data", []) if data.get("code") == 200 else []

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

    # ==================================================================
    # 脚本管理  /scripts
    # ==================================================================

    def list_scripts(self, path=None):
        params = {}
        if path:
            params["path"] = path
        data = self._get("/open/scripts", params=params)
        return data.get("data", []) if data.get("code") == 200 else []

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

    # ==================================================================
    # 依赖管理  /dependencies
    # ==================================================================

    def list_dependencies(self):
        data = self._get("/open/dependencies")
        return data.get("data", []) if data.get("code") == 200 else []

    def reinstall_dependency(self, dep_id):
        return self._put("/open/dependencies/reinstall", data=[dep_id])

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

    # ==================================================================
    # 配置文件  /configs
    # ==================================================================

    def list_configs(self):
        data = self._get("/open/configs/files")
        return data.get("data", []) if data.get("code") == 200 else []

    def get_config_detail(self, path):
        data = self._get("/open/configs/detail", params={"path": path})
        return data.get("data") if data.get("code") == 200 else None

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