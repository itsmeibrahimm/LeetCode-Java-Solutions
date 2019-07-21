from fastapi import FastAPI

from .subapps import payin, payout

app = FastAPI()


@app.get("/health")
async def getHealth():
    return "OK"


app.mount(payin.app.openapi_prefix, payin.app)
app.mount(payout.app.openapi_prefix, payout.app)
