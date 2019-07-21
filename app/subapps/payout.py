from fastapi import FastAPI

app = FastAPI(openapi_prefix="/payout")


@app.get("/accounts")
async def getAccounts():
    return {"app": "Pay-Out: ACH, FastPay, etc"}


@app.get("/payouts")
async def getPayouts():
    return {"app": "Pay-Out: ACH, FastPay, etc"}
