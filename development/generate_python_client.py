#!/usr/bin/env python

import os
import subprocess
import time
from urllib.request import urlopen
import argparse
import shutil
import json


def run_shell_command(command):
    print("Running command: ", command)
    try:
        subprocess.check_output(command, shell=True)
    except Exception as e:
        print("Error: {}".format(str(e)))
        exit(3)


def mkdir_path(path):
    if not os.access(path, os.F_OK):
        os.mkdir(path)


supported_apps = ["payout_v0", "payout_v1", "payin_v0", "payin_v1", "ledger"]

parser = argparse.ArgumentParser(
    description="Generate Python Client for Payment Service"
)
parser.add_argument(
    "-a",
    "--app",
    help="payment service app name, should be payin_v0, payin_v1, payout_v0, payout_v1, or ledger",
    required=True,
)

args = vars(parser.parse_args())

app = args["app"].lower()

if app not in supported_apps:
    print("The app your entered is not supported.")
    exit(1)

if app in ["payout_v0", "payout_v1", "payin_v0", "payin_v1"]:
    app_specs = app.split("_")
    app_name = app_specs[0]
    app_version = app_specs[1]
    service_spec_url = "http://localhost:8001/{name}/api/{version}/openapi.json".format(
        name=app_name, version=app_version
    )
else:
    service_spec_url = "http://localhost:8001/{}/openapi.json".format(app)

# create tmp folder for build
mkdir_path("tmp")

client_root_dir = os.getcwd() + "/tmp/payment-service-python-client"
app_dir = client_root_dir + "/" + app

# clone payment-service-python-client and rm all files in app_dir
if os.path.isdir(client_root_dir):
    shutil.rmtree(client_root_dir)
run_shell_command(
    "git clone --depth 1 git@github.com:doordash/payment-service-python-client.git {}".format(
        client_root_dir
    )
)

# get or create version
version_file = "{}/.version".format(app_dir)
if os.path.isfile(version_file):
    version = open(version_file.format(app_dir), "r").read()
    print(
        "Basing {} service client new version on existing version {}".format(
            app, version
        )
    )
else:
    version = "0.0.0"
    print("Basing {} service client new version on no existing version".format(app))

version_pieces = [int(i) for i in version.split(".")]
version_pieces[2] += 1
new_version = ".".join(str(i) for i in version_pieces)

# Replace config file with new version number
run_shell_command(
    'sed -i \'\' \'s/"packageVersion":.*/"packageVersion": "{}"/g\' development/python-client-configs/{}.json'.format(
        new_version, app
    )
)

# Remove all files including hidden files
run_shell_command("rm -fr " + app_dir + "/{,.[!.],..?}*")

# Write new version
with open(version_file, "w+") as f:
    f.write(new_version)
print("Current version is {}; upgrading to version: {}".format(version, new_version))

# Generate release.json.py
data = {
    "tag": "{}-{}".format(app, new_version),
    "name": "{} client {}".format(app.capitalize(), new_version),
    "app": app,
    "body": "",
    "prerelease": True,
}
with open(app_dir + "/release.json", "w+") as f:
    f.write(json.dumps(data, indent=4))


# Bring up payment service
run_shell_command(
    "WEB_PORT=8001 docker-compose -f docker-compose.yml -f docker-compose.nodeploy.yml down"
)
run_shell_command(
    "WEB_PORT=8001 docker-compose -f docker-compose.yml -f docker-compose.nodeploy.yml up --build -d web"
)

# Wait until it's ready
max_wait = 5 * 60  # 5min
sleep = 2
current_iteration = 0

while current_iteration * sleep < max_wait:
    try:
        response = urlopen(service_spec_url)
    except IOError:
        print(
            "{} Service swagger API not ready yet. Trying again in 2s".format(
                app.capitalize()
            )
        )
        time.sleep(sleep)
        current_iteration += 1
        continue
    else:
        break
else:
    print("Timeout: could not reach {} service".format(app))
    exit(2)

print("Generating client for {} service".format(app))

run_shell_command(
    """
docker run --rm \
    --network host \
    -v $(pwd)/development/python-client-configs/{}.json:/python-config.json \
    -v {}:/tmp/out \
    openapitools/openapi-generator-cli generate \
    -i {} \
    -g python \
    -c /python-config.json \
    -o /tmp/out
""".format(
        app, app_dir, service_spec_url
    )
)

# Save api schema
run_shell_command(
    "curl {} -o {}/schema.json 2> /dev/null".format(service_spec_url, app_dir)
)

# Shut down payment service
run_shell_command(
    "WEB_PORT=8001 docker-compose -f docker-compose.yml -f docker-compose.nodeploy.yml down"
)

# Commit new client version and push to remote branch
os.chdir(client_root_dir)
branch_name = "{}-client-{}".format(app, new_version)
run_shell_command("git add .")
run_shell_command(
    'git commit -am "Update {} service client to version {}"'.format(app, new_version)
)
run_shell_command("git checkout -b {}".format(branch_name))
run_shell_command("git push --set-upstream -f origin {}".format(branch_name))

print(
    "Please create a PR for your branch: {}, the new version will be bumped when PR is merged.".format(
        branch_name
    )
)
