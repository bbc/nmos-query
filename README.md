# NMOS Registry Query API Service

Provides a service implementing the NMOS Query API, specified in [AMWA IS-04](https://github.com/AMWA-TV/nmos-discovery-registration). This API allows querying of an IS-04 registry. This API can be used in conjunction with the [BBC's implementation of the Registration API](https://github.com/bbc/nmos-registration/). The BBC has also produced an open source implementation of the [IS-04 Node API](https://github.com/bbc/nmos-node).

For those wishing to experiment or familiarise themselves with the APIs the BBC has provided a joint reference implementation of IS-04 and IS-05 [here](https://github.com/bbc/nmos-joint-ri), which is readily installed using Vagrant and provides some basic user interfaces for interacting with the APIs.

This implementation was written by the BBC as part of our work on the IS-04 specification, and is research software. It has been open sourced to provide an example of the API, but has not been designed for use in production.

## Bugs and Contributions
Please file any bugs in the github issue tracker for this repository. We welcome contributions in the form of pull requests to this repository, but we would ask that you please take note of our contribution policy in [CONTRIBUTING.md](CONTRIBUTING.md).

## Installing with Python

Before installing this library please make sure you have installed the [NMOS Common Library](https://github.com/bbc/nmos-common), on which this API depends. The query API also requires [etcd](https://github.com/coreos/etcd) to be installed. For debain distributions this can be installed using apt:

```
sudo apt-get install etcd

```
``

The modern Couchbase datastore [requires some further steps](https://docs.couchbase.com/python-sdk/2.5/start-using-sdk.html). The Python package depends on the C `libcouchbase` SDK, installed on debian distributions as follows:

```
# Only needed during first-time setup:
wget http://packages.couchbase.com/releases/couchbase-release/couchbase-release-1.0-6-amd64.deb
sudo dpkg -i couchbase-release-1.0-6-amd64.deb
# Will install or upgrade packages
sudo apt-get update
sudo apt-get install libcouchbase-dev libcouchbase2-bin build-essential
```

In addition `libsystemd-dev` is required to  be installed for `cysystemd`:

```
sudo apt install libsystemd-dev
```

Once all dependencies are satisfied run the following commands to install the API:

```
pip install setuptools
sudo python setup.py install
```

## Configuration

The Query API makes use of two configuration files. The first is native to the Query API and is described below. The second forms part of the [NMOS Common Library](https://github.com/bbc/nmos-common) and is described in that repository. Note that you will likely have to configure items in both files.

The native Query API configuration should consist of a JSON object in the file `/etc/ips-regquery/config.json`. The following attributes may be set within the object:

*   **priority:** \[integer\] Sets a priority value for this Query API instance between 0 and 255. A value of 100+ indicates a development rather than production instance. Default: 100.
*   **https_mode:** \[string\] Switches the API between HTTP and HTTPS operation. "disabled" indicates HTTP mode is in use, "enabled" indicates HTTPS mode is in use. Default: "disabled".
*   **enable_mdns:** \[boolean\] Provides a mechanism to disable mDNS announcements in an environment where unicast DNS is preferred. Default: true.
*   **oauth_mode:** \[boolean\] Switches the API between being secured using OAuth2 and not using authorization. Default: false.
* **registry**: \[object\]
  * **type**: \[string\] Defines whether the registry is an instance of etcd or Couchbase. Default: etcd.
  * **hosts**: \[array\] An array of string IPs/URLs specifying a set of Couchbase Server instances (i.e., each node in a cluster).
  * **port**: \[integer\] The host port of the Couchbase cluster nodes
  * **username**: \[string\] The client username for authenticating against the Couchbase cluster.
  * **password**: \[string\]The client password for authenticating against the Couchbase cluster.
  * **buckets**: \[object\]
    * **registry**: \[string\] The name of the primary bucket for storing/accessing resource documents.
    * **meta**: \[string\] The name of the secondary bucket for storing/accessing metadata documents.
* **resource_expiry**: \[integer\] The time after which a document will expire in the absence of any heartbeat. Default: 12.

Example configuration files are shown below:

### etcd

```json
{
  "priority": "30",
  "https_mode": "enabled",
  "enable_mdns": false,
  "oauth_mode": true
}
```

### Couchbase

```json
{
    "priority": 100,
    "https_mode": "disabled",
    "enable_mdns": true,
    "service_port": 8235,
    "registry": {
        "type": "couchbase",
        "hosts": ["192.168.0.1", "192.168.0.2"],
        "port": 8091,
        "username": "nmos-admin",
        "password": "ipstudio",
        "buckets": {
            "registry": "nmos-registry",
            "meta": "nmos-registry-meta"
        }
    },
    "resource_expiry": 12
}
```

## Running the Query API

### Non-blocking

Run the following script to start the Query API in a non-blocking manner, and then stop it again at a later point:

```Python
    from nmosquery.service import QueryService

    service = QueryService()
    service.start()

    # Do something else until ready to stop

    service.stop()
```

### Blocking

It is also possible to run Query API in a blocking manner:

```python
from nmosquery.service import QueryService

service = QueryService()
service.run() # Runs forever
```

### Local Development Datastore

To run a local instance of Couchbase Server, the easiest approach is to run `docker-compose` in the `tests/` directory and run a test container. Some setup is required, either through a web GUI accessible via `http://[host]:8091` or POSTing the http requests specified in `_initialise_cluster()` within `test_couchbase` in `tests/v1_0/`.

For a full development environment, a `Vagrantfile` is provided in the root of the directory that provisions a Virtual Machine with all the required dependencies. This can be run using:

```bash
vagrant up --provision
```

Note this will require both Vagrant and Ansible to be installed in order to provision the VM. Once the machine has been provisioned, running the following script will configure a single node cluster and bring up the API Service:

```bash
vagrant ssh  # ssh into the VM
python3 /vagrant/initialise_couchbase.py  # initialise cluster
```

## Tests

Unit and integration tests are provided.

### Unit Tests
 Currently these have hard-coded dummy/example hostnames, IP addresses and UUIDs.  You will need to edit the Python files under nmos-query/test/ to suit your needs and then "make test". You will need to have [Python virtualenv](https://pypi.python.org/pypi/virtualenv) installed and in your system PATH.

### Integration Tests
 These run against a containerised docker instance of a single-node Couchbase cluster (which is automatically provisioned when running associated test files/calling `make test`).

## Debian Packaging

Debian packaging files are provided for internal BBC R&D use.
These packages depend on packages only available from BBC R&D internal mirrors, and will not build in other environments. For use outside the BBC please use python installation method.
