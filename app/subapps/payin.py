from fastapi import FastAPI

app = FastAPI(openapi_prefix="/payin")


@app.get("/charges")
async def getCharges():
    return {"app": "Pay-In: Charges, Refunds, etc"}


@app.get("/refunds")
async def getRefunds():
    return {"app": "Pay-In: Charges, Refunds, etc"}
