import time
import aiohttp
import requests
import urllib3
import glv
from db.methods import get_marzban_profile_db

# Отключаем предупреждения InsecureRequestWarning для requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROTOCOLS = {
    "vmess": [
        {},
        ["VMess TCP"]
    ],
    "vless": [
        {
            "flow": "xtls-rprx-vision"
        },
        ["VLESS TCP REALITY"]
    ],
    "trojan": [
        {},
        ["Trojan Websocket TLS"]
    ],
    "shadowsocks": [
        {
            "method": "chacha20-ietf-poly1305"
        },
        ["Shadowsocks TCP"]
    ]
}

class Marzban:
    def __init__(self, ip: str, login: str, passwd: str) -> None:
        self.ip = ip.rstrip('/')
        self.login = login
        self.passwd = passwd
        self.token = None

    async def _send_request(self, method: str, path: str, headers=None, data=None) -> dict | list:
        url = f"{self.ip}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=data, ssl=False) as resp:
                if 200 <= resp.status < 300:
                    return await resp.json()
                else:
                    text = await resp.text()
                    raise Exception(f"Error {resp.status} from {url}; Body: {text}; Data: {data}")

    def _fetch_token(self) -> str:
        data = {"username": self.login, "password": self.passwd}
        # до 5 попыток с паузой
        for attempt in range(1, 6):
            try:
                resp = requests.post(
                    f"{self.ip}/api/admin/token",
                    data=data,
                    verify=False,
                    timeout=10
                ).json()
                token = resp.get('access_token')
                if not token:
                    raise ValueError("no access_token in response")
                return token
            except Exception as e:
                print(f"⚠️ Marzban get_token attempt {attempt} failed: {e}")
                time.sleep(2)
        raise ConnectionError("Could not fetch Marzban token after 5 attempts")

    def get_token(self, force: bool = False) -> str:
        if self.token is None or force:
            self.token = self._fetch_token()
        return self.token

    async def get_user(self, username: str) -> dict:
        token = self.get_token()
        headers = {'Authorization': f"Bearer {token}"}
        return await self._send_request("GET", f"/api/user/{username}", headers=headers)

    async def get_users(self) -> dict:
        token = self.get_token()
        headers = {'Authorization': f"Bearer {token}"}
        return await self._send_request("GET", "/api/users", headers=headers)

    async def add_user(self, data: dict) -> dict:
        token = self.get_token()
        headers = {'Authorization': f"Bearer {token}"}
        return await self._send_request("POST", "/api/user", headers=headers, data=data)

    async def modify_user(self, username: str, data: dict) -> dict:
        token = self.get_token()
        headers = {'Authorization': f"Bearer {token}"}
        return await self._send_request("PUT", f"/api/user/{username}", headers=headers, data=data)


def get_protocols() -> dict:
    proxies = {}
    inbounds = {}
    for proto in glv.config['PROTOCOLS']:
        l = proto.lower()
        if l not in PROTOCOLS:
            continue
        proxies[l] = PROTOCOLS[l][0]
        inbounds[l] = PROTOCOLS[l][1]
    return {"proxies": proxies, "inbounds": inbounds}


panel = Marzban(
    glv.config['PANEL_HOST'],
    glv.config['PANEL_USER'],
    glv.config['PANEL_PASS']
)

ps = get_protocols()


async def check_if_user_exists(name: str) -> bool:
    try:
        await panel.get_user(name)
        return True
    except Exception:
        return False


async def get_marzban_profile(tg_id: int):
    marzban_username = str(tg_id) # В Marzban теперь username = tg_id
    exists = await check_if_user_exists(marzban_username)
    if not exists:
        # Для обратной совместимости: если пользователь не найден по tg_id в Marzban,
        # попробуем найти по vpn_id (MD5) из нашей локальной БД,
        # так как он мог быть создан в Marzban старым способом.
        db_profile = await get_marzban_profile_db(tg_id)
        if db_profile and db_profile.vpn_id and db_profile.vpn_id != marzban_username:
            old_marzban_username_md5 = db_profile.vpn_id
            # Печать для отладки, чтобы видеть какой идентификатор используется
            print(f"DEBUG: User tg_id={tg_id} not found in Marzban by tg_id ('{marzban_username}'). Trying old vpn_id: '{old_marzban_username_md5}'")
            exists_by_old_md5 = await check_if_user_exists(old_marzban_username_md5)
            if exists_by_old_md5:
                print(f"DEBUG: User tg_id={tg_id} FOUND in Marzban by old vpn_id: '{old_marzban_username_md5}'")
                return await panel.get_user(old_marzban_username_md5)
            else:
                print(f"DEBUG: User tg_id={tg_id} NOT found in Marzban by old vpn_id: '{old_marzban_username_md5}' either.")
        else:
            # Профиль в локальной БД не найден или vpn_id совпадает с tg_id (маловероятно, но для полноты)
            print(f"DEBUG: User tg_id={tg_id} not found in Marzban by tg_id ('{marzban_username}') and no distinct old vpn_id in local DB.")
        return None # Не найден ни по tg_id, ни по старому vpn_id в Marzban
    
    # Нашли в Marzban по tg_id (marzban_username), его и возвращаем
    print(f"DEBUG: User tg_id={tg_id} FOUND in Marzban by tg_id as username: '{marzban_username}'")
    return await panel.get_user(marzban_username)


async def generate_test_subscription(username: str, custom_hours: int = None):
    hours_to_use = custom_hours if custom_hours is not None else glv.config['PERIOD_LIMIT']
    
    # Печать для отладки, какие часы используются
    print(f"DEBUG MarzbanAPI: generate_test_subscription for '{username}' using {hours_to_use} hours.")

    exists = await check_if_user_exists(username)
    now = time.time()
    if exists:
        user = await panel.get_user(username)
        user['status'] = 'active'
        # Убедимся, что user['expire'] это число, иначе сравнение и сложение вызовут ошибку
        current_expire = user.get('expire') if isinstance(user.get('expire'), (int, float)) else 0
        if current_expire < now:
            user['expire'] = get_test_subscription(hours_to_use)
        else:
            user['expire'] = current_expire + get_test_subscription(hours_to_use, additional=True)
        return await panel.modify_user(username, user)
    else:
        new_user = {
            'username': username,
            'proxies': ps["proxies"],
            'inbounds': ps["inbounds"],
            'expire': get_test_subscription(hours_to_use),
            'data_limit': 0,
            'data_limit_reset_strategy': "no_reset",
        }
        return await panel.add_user(new_user)


async def generate_marzban_subscription(username: str, good):
    exists = await check_if_user_exists(username)
    now = time.time()
    if exists:
        user = await panel.get_user(username)
        user['status'] = 'active'
        if user['expire'] < now:
            user['expire'] = get_subscription_end_date(good['months'])
        else:
            user['expire'] += get_subscription_end_date(good['months'], additional=True)
        return await panel.modify_user(username, user)
    else:
        new_user = {
            'username': username,
            'proxies': ps["proxies"],
            'inbounds': ps["inbounds"],
            'expire': get_subscription_end_date(good['months']),
            'data_limit': 0,
            'data_limit_reset_strategy': "no_reset",
        }
        return await panel.add_user(new_user)


def get_test_subscription(hours: int, additional: bool = False) -> int:
    return (0 if additional else int(time.time())) + 60 * 60 * hours


def get_subscription_end_date(months: int, additional: bool = False) -> int:
    return (0 if additional else int(time.time())) + 60 * 60 * 24 * 30 * months
