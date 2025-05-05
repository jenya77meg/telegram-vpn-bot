from tgbot.handlers.start import router as start_router
from tgbot.handlers.vpn import router as vpn_router
from tgbot.handlers.profile import router as profile_router
from tgbot.handlers.cancel import router as cancel_router
from tgbot.handlers.guide import router as guide_router

routers_list = [
    cancel_router,
    start_router,
    vpn_router,
    profile_router,
    guide_router,
]
