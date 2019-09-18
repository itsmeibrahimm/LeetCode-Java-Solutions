# Payment pressure tests
## Set up local environment
While doordash-pressure still utilize `pip` + `requirements.txt` combination for development, we want to simplify local env setup in a similar way as we do in payment-service main repo with `pipenv`.

### Local environment setup

#### Install dependencies
```bash
cd <payment repo>/pressure
./update-local-env.sh # create virtual environment if necessary
pipenv shell # login to virtual environment
```
#### Setup pycharm
- **DO NOT** use same Pycharm environment setup for payment-service
- Create a new pycharm project directly from `.../<payment-service-repo>/pressure/`
- Set content root via `cmd+,` -> `Project: pressure` -> `Project structure` -> `+ Add Content Root` to **ONLY**  `.../<payment-service-repo>/pressure/tests` to allow pycharm do absolute imports with correct path.

### Run locally

Assuming you started your local service at port 8000


```bash
cd <payment repo>/pressure
pipenv shell
pressure --data-file=$(pipenv --venv)/infra/local/data.yaml --data-file=infra/local/data.yaml --locust-args="--host http://localhost:8000 -f tests/locustfile.py --csv=report --no-web -c 1000 -r 100 --run-time 5m"
```
#### Troubleshooting
- Maximum number of open files (`[Errno 24] Too many open files`)

Every HTTP connection on a machine opens a new file (technically a file descriptor). Operating systems may set a low limit for the maximum number of files that can be open. If the limit is less than the number of simulated users in a test, failures will occur.

To increase this limit, Mac users do:
```bash
ulimit -S -n 2048 # increase as needed
```

### One-off load test against staging
https://github.com/doordash/doordash-pressure#one-off-deployment

### More configurations and how to run in staging prod
Refers to main doordash-pressure [readme](https://github.com/doordash/doordash-pressure/blob/master/README.md)

### How to write load test with locust
https://docs.locust.io/en/stable/

### Pressure wavefron dashboard
https://metrics.wavefront.com/dashboard/payment-service-pressure
