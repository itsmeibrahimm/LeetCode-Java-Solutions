# Payment Service Client Integration

## Before Starting
Before starting integration, things developers should know first:
- Payment Service API Design Docs available [here](https://docs.google.com/document/d/1cnIx3TTkTZYkuuvCYc0XysdNixOippd5g8uzzKLIcms/edit?ts=5d14f007#heading=h.r76fhvcd081g)
- Payment Service exposes REST interfaces for Payin flows, referred to as Payin APIs.
- Payin APIs are fully-compatible with existing DSJ clients. Please the read client migration guide [here](https://docs.google.com/document/d/1QVl2LdZMIpSz2129WaYSx99b9QhKE38lhbmlMZ4_jhM/edit#heading=h.6k4cn0qqf3m1)


## Environment
- Staging: Payment Service is deployed on Staging along with Stripe Sandbox. Client can test against Staging environment for almost all of features.
- Local staging:
  - Unit Test: clients mock the the Payment Service APIs.
  - Integration Test: (short-term solution) interact with Payment Service on Staging.

## Integration Step by Step
1. Request an IDS API Key against the `payment-service` service by following instructions [here](https://doordash.atlassian.net/wiki/spaces/PE/pages/762970379/Identity+Service#IdentityService-Services,ClientsandTokensTerms). Payment Service enforces IDS authentication. Client needs to acquire a valid API Key and provide in HTTP request header x-api-key for each request.

2. Experience Payment Service through FastAPI docs. This is the fastest way to experience Payin APIs without changing any line of code.

   1. login Staging:
   ```bash
    dd-toolbox kubernetes-auth login --environment staging
   ```
   2. port forwarding:
   ```bash
   kubectl port-forward -n payment-service service/payment-service-web 8080:80
   ```
   3. open browser, and type the following url (note: v0 supports legacy information as input and is expected to be called only by DSJ for backward compatibility):
   ```bash
   http://localhost:8080/payin/api/v0/docs
   ```
   ```bash
   http://localhost:8080/payin/api/v1/docs
   ```
   4. you will see the following view and will be able to issue request to Payin APIs on Staging (with valid API Key)
![payin_fastapi_dmeo_list](./development/payin_fastapi_dmeo_list.png)
![payin_fastapi_dmeo_contract](./development/payin_fastapi_dmeo_contract.png)

3. `Client Library`. We provided an OpenAPI generated client library (python only for now, kotlin planned for the future). Please see [here](https://github.com/doordash/payment-service-python-client/tree/master/payin) for detailed information.


## Golden Examples
(WIP) We will provide separate examples to showcase the major scenarios. Now we refer to our pulse tests as the golden workflows are already covered by pulse tests.
- Payers:
  - [create payer and update default payment method](https://github.com/doordash/payment-service/blob/master/pulse/tests/payin/test_end_to_end.py#L9)
- PaymentMethods:
  - [create/attach/detach payment method](https://github.com/doordash/payment-service/blob/master/pulse/tests/payin/test_end_to_end.py#L9)
- CartPayments:
  - [create cart_payment](https://github.com/doordash/payment-service/blob/master/pulse/tests/payin/test_cart_payment.py#L14)
  - [order cart adjustment with higher amount](https://github.com/doordash/payment-service/blob/master/pulse/tests/payin/test_cart_payment.py#L72)
  - [order cart adjustment with lower amount](https://github.com/doordash/payment-service/blob/master/pulse/tests/payin/test_cart_payment.py#L94)
