# marzban/init_client.py
import httpx                           # + импорт

async def get_token(self):
    try:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=False               # → SSL нам не нужен во внутренней сети
        ) as client:
            resp = await client.post(
                "/api/admin/token",
                data={                 # !!! form-urlencoded, НЕ json
                    "username": self._config.marzban.username,
                    "password": self._config.marzban.password,
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]
    except Exception as e:
        self._logger.error(f"Error getting token: {e}")
        raise

