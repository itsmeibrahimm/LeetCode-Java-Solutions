# Payment pulse tests
## Set up local environment
While doordash-pulse still utilize `pip` + `requirements.txt` combination for development, we want to simplify local env setup in a similar way as we do in payment-service main repo with `pipenv`.

### Local environment setup

#### Install dependencies
```bash
cd <payment repo>/pulse
deactivate > /dev/null 2>&1 # deactivate any existing pipenv shell in case parent pipenv shell exists
./update-local-env.sh # create virtual environment if necessary
pipenv shell # login to virtual environment
```
#### Setup pycharm
- **DO NOT** use same Pycharm environment setup for payment-service
- Create a new pycharm project directly from `.../<payment-service-repo>/pulse/`

### Run locally

Assuming you started your local service at port 8082 by `make local-server WEB_PORT=8082`

```bash
cd <payment repo>/pulse
deactivate > /dev/null 2>&1 # deactivate any existing pipenv shell in case parent pipenv shell exists
pipenv shell
pulse --data-file=$(pipenv --venv)/infra/local/data.yaml --data-file=infra/local/data.yaml
```
